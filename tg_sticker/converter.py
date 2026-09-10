"""Core conversion pipeline for Telegram animated stickers and emoji."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .optimizer import (
    MAX_TELEGRAM_STICKER_BYTES,
    SAFE_TARGET_BYTES,
    EncodingParams,
    plan_reencode_strategy,
)
from .validator import (
    MediaInfo,
    ValidationResult,
    ensure_ffmpeg_available,
    probe_media,
    validate_telegram_webm,
)


@dataclass
class ConversionConfig:
    mode: str = "sticker"  # "sticker" (512px edge) or "emoji" (100x100)
    start_time: Optional[float] = None  # Start timestamp in seconds
    duration: Optional[float] = None  # Desired clip duration in seconds (<= 3.0)
    speed_to_fit: bool = False  # Speed up video so entire clip fits in <= 3.0s
    loop_mode: str = "normal"  # "normal" or "pingpong" (boomerang)
    fit_mode: str = "crop"  # "crop", "pad", or "stretch" (for emoji or custom AR)
    fps: int = 30  # Max 30 FPS
    crf: int = 30  # Base VP9 CRF quality (lower = higher quality, 30 is balanced)
    remove_bg: Optional[str] = None  # Color to key out, e.g. "green", "#00FF00", "white", "black"
    max_duration: float = 3.0  # Telegram hard max limit is 3.0s
    preserve_alpha: bool = True  # Preserve transparent alpha channels if present


class TelegramConverter:
    """Orchestrates conversion of video/GIF files to Telegram-compliant WebM VP9 stickers."""

    def __init__(self):
        self.ffmpeg_bin = ensure_ffmpeg_available()

    def convert(
        self,
        input_path: str | Path,
        output_path: str | Path,
        config: Optional[ConversionConfig] = None,
    ) -> ValidationResult:
        """Converts an input video/GIF into a compliant Telegram animated sticker/emoji."""
        cfg = config or ConversionConfig()
        in_p = Path(input_path).resolve()
        out_p = Path(output_path).resolve()

        if not in_p.exists():
            raise FileNotFoundError(f"Input file not found: {in_p}")

        # Probe source media
        info = probe_media(in_p)

        # 1. Determine timing & effective duration
        start_t = cfg.start_time or 0.0
        available_dur = max(info.duration - start_t, 0.1) if info.duration > 0 else cfg.max_duration

        if cfg.speed_to_fit and available_dur > cfg.max_duration:
            clip_dur = cfg.max_duration
            pts_speed_factor = cfg.max_duration / available_dur
        else:
            pts_speed_factor = 1.0
            if cfg.duration:
                clip_dur = min(cfg.duration, cfg.max_duration)
            else:
                clip_dur = min(available_dur, cfg.max_duration)

        # In ping-pong mode, forward playback takes half duration, backward takes half
        if cfg.loop_mode == "pingpong":
            half_dur = clip_dur / 2.0
        else:
            half_dur = clip_dur

        # Ensure parent directory for output exists
        out_p.parent.mkdir(parents=True, exist_ok=True)

        # Build video filter chain
        vfilters = self._build_video_filters(
            cfg=cfg,
            info=info,
            start_t=start_t,
            clip_dur=clip_dur,
            half_dur=half_dur,
            pts_speed_factor=pts_speed_factor,
        )

        # Determine pixel format (preserve alpha if source has it or background removal requested)
        needs_alpha = (cfg.preserve_alpha and info.has_alpha) or (cfg.remove_bg is not None)
        pix_fmt = "yuva420p" if needs_alpha else "yuv420p"

        # Build input seeking args and support static image inputs
        input_args = []
        is_static_image = in_p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".tiff"} and info.duration <= 0.1
        if is_static_image:
            input_args.extend(["-loop", "1"])
        if start_t > 0:
            input_args.extend(["-ss", f"{start_t:.4f}"])

        # Pass 0: Initial high-quality CRF encode
        initial_params = EncodingParams(
            crf=cfg.crf,
            bitrate_kbps=0,
            two_pass=False,
            fps=min(cfg.fps, 30),
        )

        self._run_encode(
            in_p=in_p,
            out_p=out_p,
            vfilters=vfilters,
            params=initial_params,
            pix_fmt=pix_fmt,
            clip_dur=clip_dur,
            input_args=input_args,
        )

        # Check output file size
        file_size = out_p.stat().st_size
        attempt = 1

        # Size enforcement loop: If > 256 KB, optimize iteratively
        while file_size > MAX_TELEGRAM_STICKER_BYTES and attempt <= 4:
            reencode_params = plan_reencode_strategy(
                current_size_bytes=file_size,
                duration_sec=clip_dur,
                attempt=attempt,
                current_fps=initial_params.fps,
            )

            # Rebuild filters if FPS changed
            curr_filters = self._build_video_filters(
                cfg=cfg,
                info=info,
                start_t=start_t,
                clip_dur=clip_dur,
                half_dur=half_dur,
                pts_speed_factor=pts_speed_factor,
                override_fps=reencode_params.fps,
            )

            self._run_encode(
                in_p=in_p,
                out_p=out_p,
                vfilters=curr_filters,
                params=reencode_params,
                pix_fmt=pix_fmt,
                clip_dur=clip_dur,
                input_args=input_args,
            )

            file_size = out_p.stat().st_size
            attempt += 1

        # Validate final output against Telegram rules
        validation = validate_telegram_webm(out_p, mode=cfg.mode)
        return validation

    def _build_video_filters(
        self,
        cfg: ConversionConfig,
        info: MediaInfo,
        start_t: float,
        clip_dur: float,
        half_dur: float,
        pts_speed_factor: float,
        override_fps: Optional[int] = None,
    ) -> str:
        """Constructs FFmpeg filter chain according to scaling, trimming, loop, and color options."""
        filters = []

        # 1. Trimming & Speed adjustment
        target_fps = override_fps or min(cfg.fps, 30)

        # Speed-to-fit
        if cfg.speed_to_fit and pts_speed_factor < 1.0:
            filters.append(f"setpts={pts_speed_factor:.6f}*PTS")

        # Background color removal if requested
        if cfg.remove_bg:
            color = cfg.remove_bg.lower()
            if color == "green":
                filters.append("colorkey=0x00FF00:0.3:0.15")
            elif color == "black":
                filters.append("colorkey=0x000000:0.1:0.1")
            elif color == "white":
                filters.append("colorkey=0xFFFFFF:0.1:0.1")
            else:
                # Custom hex color (e.g. #123456 or 0x123456)
                hex_val = color.replace("#", "0x")
                filters.append(f"colorkey={hex_val}:0.25:0.15")

        # Dimensions scaling
        if cfg.mode == "emoji":
            # Exact 100x100
            if cfg.fit_mode == "crop":
                filters.append("crop=min(iw\\,ih):min(iw\\,ih),scale=100:100")
            elif cfg.fit_mode == "pad":
                filters.append(
                    "scale='if(gte(iw,ih),100,-2)':'if(gte(iw,ih),-2,100)',"
                    "pad=100:100:(100-iw)/2:(100-ih)/2:color=0x00000000"
                )
            else:  # stretch
                filters.append("scale=100:100")
        else:
            # Sticker mode: One side must be 512, other <= 512, even dimensions
            filters.append("scale='if(gte(iw,ih),512,-2)':'if(gte(iw,ih),-2,512)'")

        # Frame rate
        filters.append(f"fps={target_fps}")

        base_chain = ",".join(filters)

        # Looping: pingpong (boomerang) vs normal
        if cfg.loop_mode == "pingpong":
            # Trim to half_dur, then forward + reverse
            complex_filter = (
                f"[0:v]{base_chain},trim=0:{half_dur:.4f},setpts=PTS-STARTPTS,split[fwd][rev_in];"
                f"[rev_in]reverse[rev];"
                f"[fwd][rev]concat=n=2:v=1:a=0"
            )
            return complex_filter
        else:
            # Trim to max clip_dur
            return f"{base_chain},trim=0:{clip_dur:.4f},setpts=PTS-STARTPTS"

    def _run_encode(
        self,
        in_p: Path,
        out_p: Path,
        vfilters: str,
        params: EncodingParams,
        pix_fmt: str,
        clip_dur: float,
        input_args: Optional[list] = None,
    ) -> None:
        """Executes FFmpeg encoding command (single-pass or two-pass)."""
        is_complex = ";" in vfilters
        in_args = input_args or []

        filter_args = ["-filter_complex", vfilters] if is_complex else ["-vf", vfilters]

        if not params.two_pass:
            # Single-pass CRF
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-autorotate",
                *in_args,
                "-i", str(in_p),
                *filter_args,
                "-c:v", "libvpx-vp9",
                "-pix_fmt", pix_fmt,
                "-crf", str(params.crf),
                "-b:v", "0",
                "-an",
                "-t", f"{clip_dur:.4f}",
                str(out_p),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"FFmpeg encoding failed: {res.stderr}")
        else:
            # Two-pass constrained bitrate
            with tempfile.TemporaryDirectory() as tmpdir:
                passlogfile = os.path.join(tmpdir, "ffmpeg2pass")

                # Pass 1
                cmd_pass1 = [
                    self.ffmpeg_bin,
                    "-y",
                    "-autorotate",
                    *in_args,
                    "-i", str(in_p),
                    *filter_args,
                    "-c:v", "libvpx-vp9",
                    "-pix_fmt", pix_fmt,
                    "-b:v", f"{params.bitrate_kbps}k",
                    "-minrate", f"{int(params.bitrate_kbps * 0.5)}k",
                    "-maxrate", f"{params.maxrate_kbps}k",
                    "-bufsize", f"{params.bufsize_kbps}k",
                    "-crf", str(params.crf),
                    "-pass", "1",
                    "-passlogfile", passlogfile,
                    "-an",
                    "-t", f"{clip_dur:.4f}",
                    "-f", "null",
                    os.devnull,
                ]
                res1 = subprocess.run(cmd_pass1, capture_output=True, text=True)
                if res1.returncode != 0:
                    raise RuntimeError(f"FFmpeg 2-pass (pass 1) failed: {res1.stderr}")

                # Pass 2
                cmd_pass2 = [
                    self.ffmpeg_bin,
                    "-y",
                    "-autorotate",
                    *in_args,
                    "-i", str(in_p),
                    *filter_args,
                    "-c:v", "libvpx-vp9",
                    "-pix_fmt", pix_fmt,
                    "-b:v", f"{params.bitrate_kbps}k",
                    "-minrate", f"{int(params.bitrate_kbps * 0.5)}k",
                    "-maxrate", f"{params.maxrate_kbps}k",
                    "-bufsize", f"{params.bufsize_kbps}k",
                    "-crf", str(params.crf),
                    "-pass", "2",
                    "-passlogfile", passlogfile,
                    "-an",
                    "-t", f"{clip_dur:.4f}",
                    str(out_p),
                ]
                res2 = subprocess.run(cmd_pass2, capture_output=True, text=True)
                if res2.returncode != 0:
                    raise RuntimeError(f"FFmpeg 2-pass (pass 2) failed: {res2.stderr}")
