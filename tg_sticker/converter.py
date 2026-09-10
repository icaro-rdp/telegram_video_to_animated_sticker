"""Core conversion pipeline for Telegram animated stickers and emoji."""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .exceptions import (
    EncodingError,
    MediaNotFoundError,
    ValidationError,
)
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

STATIC_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}


@dataclass
class ConversionConfig:
    mode: str = "sticker"  # "sticker" (512px edge) or "emoji" (100x100)
    start_time: Optional[float] = None  # Start timestamp in seconds
    duration: Optional[float] = None  # Desired clip duration in seconds (<= 3.0)
    speed_to_fit: bool = False  # Speed up video so entire clip fits in <= 3.0s
    loop_mode: str = "normal"  # "normal" or "pingpong" (boomerang)
    fit_mode: str = "crop"  # "crop", "pad", or "stretch" (for emoji or custom AR)
    fps: int = 30  # Max 30 FPS
    crf: int = 30  # Base VP9 CRF quality (0-63)
    remove_bg: Optional[str] = None  # Color to key out, e.g. "green", "white", "black", "#hex"
    max_duration: float = 3.0  # Telegram hard max limit is 3.0s
    preserve_alpha: bool = True  # Preserve transparent alpha channels if present


@dataclass
class TimingPlan:
    start_time: float
    clip_duration: float
    half_duration: float
    pts_speed_factor: float


class TelegramConverter:
    """Orchestrates conversion of video/GIF/image files to Telegram-compliant WebM VP9 stickers."""

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
            raise MediaNotFoundError(f"Input file not found: {in_p}")

        info = probe_media(in_p)
        timing = self._plan_timing(info, cfg)

        out_p.parent.mkdir(parents=True, exist_ok=True)

        needs_alpha = (cfg.preserve_alpha and info.has_alpha) or (cfg.remove_bg is not None)
        pix_fmt = "yuva420p" if needs_alpha else "yuv420p"

        input_args = self._build_input_args(in_p, info.duration, timing.start_time)
        initial_params = EncodingParams(crf=cfg.crf, bitrate_kbps=0, two_pass=False, fps=min(cfg.fps, 30))

        vfilters = self._build_video_filters(cfg, timing, initial_params.fps)
        self._run_encode(in_p, out_p, vfilters, initial_params, pix_fmt, timing.clip_duration, input_args)

        # Optimization loop: re-encode if file exceeds Telegram's 256 KB limit
        file_size = out_p.stat().st_size
        attempt = 1
        while file_size > MAX_TELEGRAM_STICKER_BYTES and attempt <= 4:
            reencode_params = plan_reencode_strategy(
                current_size_bytes=file_size,
                duration_sec=timing.clip_duration,
                attempt=attempt,
                current_fps=initial_params.fps,
            )
            curr_filters = self._build_video_filters(cfg, timing, reencode_params.fps)
            self._run_encode(in_p, out_p, curr_filters, reencode_params, pix_fmt, timing.clip_duration, input_args)
            file_size = out_p.stat().st_size
            attempt += 1

        return validate_telegram_webm(out_p, mode=cfg.mode)

    def _plan_timing(self, info: MediaInfo, cfg: ConversionConfig) -> TimingPlan:
        start_t = cfg.start_time or 0.0
        available_dur = max(info.duration - start_t, 0.1) if info.duration > 0 else cfg.max_duration

        if cfg.speed_to_fit and available_dur > cfg.max_duration:
            clip_dur = cfg.max_duration
            pts_speed_factor = cfg.max_duration / available_dur
        else:
            pts_speed_factor = 1.0
            clip_dur = min(cfg.duration, cfg.max_duration) if cfg.duration else min(available_dur, cfg.max_duration)

        half_dur = (clip_dur / 2.0) if cfg.loop_mode == "pingpong" else clip_dur
        return TimingPlan(
            start_time=start_t,
            clip_duration=clip_dur,
            half_duration=half_dur,
            pts_speed_factor=pts_speed_factor,
        )

    def _build_input_args(self, in_p: Path, duration: float, start_t: float) -> List[str]:
        args = []
        if in_p.suffix.lower() in STATIC_IMAGE_EXTENSIONS and duration <= 0.1:
            args.extend(["-loop", "1"])
        if start_t > 0:
            args.extend(["-ss", f"{start_t:.4f}"])
        return args

    def _build_video_filters(self, cfg: ConversionConfig, timing: TimingPlan, target_fps: int) -> str:
        filters: List[str] = []

        if cfg.speed_to_fit and timing.pts_speed_factor < 1.0:
            filters.append(f"setpts={timing.pts_speed_factor:.6f}*PTS")

        if cfg.remove_bg:
            color = cfg.remove_bg.lower()
            key_map = {
                "green": "colorkey=0x00FF00:0.3:0.15",
                "black": "colorkey=0x000000:0.1:0.1",
                "white": "colorkey=0xFFFFFF:0.1:0.1",
            }
            filters.append(key_map.get(color, f"colorkey={color.replace('#', '0x')}:0.25:0.15"))

        if cfg.mode == "emoji":
            if cfg.fit_mode == "pad":
                filters.append(
                    "scale='if(gte(iw,ih),100,-2)':'if(gte(iw,ih),-2,100)',"
                    "pad=100:100:(100-iw)/2:(100-ih)/2:color=0x00000000"
                )
            elif cfg.fit_mode == "stretch":
                filters.append("scale=100:100")
            else:  # crop
                filters.append("crop=min(iw\\,ih):min(iw\\,ih),scale=100:100")
        else:
            # Sticker mode: exactly 512px on longer side, <= 512px on other, even dimensions
            filters.append("scale='if(gte(iw,ih),512,-2)':'if(gte(iw,ih),-2,512)'")

        filters.append(f"fps={min(target_fps, 30)}")
        base_chain = ",".join(filters)

        if cfg.loop_mode == "pingpong":
            return (
                f"[0:v]{base_chain},trim=0:{timing.half_duration:.4f},setpts=PTS-STARTPTS,split[fwd][rev_in];"
                f"[rev_in]reverse[rev];"
                f"[fwd][rev]concat=n=2:v=1:a=0"
            )
        return f"{base_chain},trim=0:{timing.clip_duration:.4f},setpts=PTS-STARTPTS"

    def _execute(self, cmd: List[str], file_name: str, stage_name: str) -> None:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise EncodingError(
                f"{stage_name} failed for {file_name}",
                cmd=cmd,
                returncode=res.returncode,
                stderr=res.stderr,
            )

    def _run_encode(
        self,
        in_p: Path,
        out_p: Path,
        vfilters: str,
        params: EncodingParams,
        pix_fmt: str,
        clip_dur: float,
        input_args: Optional[List[str]] = None,
    ) -> None:
        """Executes FFmpeg encoding command (single-pass or two-pass)."""
        is_complex = ";" in vfilters
        filter_args = ["-filter_complex", vfilters] if is_complex else ["-vf", vfilters]
        base_cmd = [
            self.ffmpeg_bin,
            "-y",
            "-autorotate",
            *(input_args or []),
            "-i", str(in_p),
            *filter_args,
            "-c:v", "libvpx-vp9",
            "-pix_fmt", pix_fmt,
        ]

        if not params.two_pass:
            cmd = base_cmd + ["-crf", str(params.crf), "-b:v", "0", "-an", "-t", f"{clip_dur:.4f}", str(out_p)]
            self._execute(cmd, in_p.name, "FFmpeg encoding")
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                passlogfile = os.path.join(tmpdir, "ffmpeg2pass")
                rate_args = [
                    "-b:v", f"{params.bitrate_kbps}k",
                    "-minrate", f"{int(params.bitrate_kbps * 0.5)}k",
                    "-maxrate", f"{params.maxrate_kbps}k",
                    "-bufsize", f"{params.bufsize_kbps}k",
                    "-crf", str(params.crf),
                ]

                # Pass 1
                cmd_pass1 = base_cmd + rate_args + [
                    "-pass", "1", "-passlogfile", passlogfile, "-an", "-t", f"{clip_dur:.4f}", "-f", "null", os.devnull
                ]
                self._execute(cmd_pass1, in_p.name, "FFmpeg 2-pass (pass 1)")

                # Pass 2
                cmd_pass2 = base_cmd + rate_args + [
                    "-pass", "2", "-passlogfile", passlogfile, "-an", "-t", f"{clip_dur:.4f}", str(out_p)
                ]
                self._execute(cmd_pass2, in_p.name, "FFmpeg 2-pass (pass 2)")
