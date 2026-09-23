"""Core conversion pipeline for Telegram animated stickers and emoji."""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .exceptions import (
    EncodingError,
    MediaNotFoundError,
    ValidationError,
)
from .optimizer import (
    MAX_TELEGRAM_STICKER_BYTES,
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
    start_time: float | None = None  # Start timestamp in seconds
    duration: float | None = None  # Desired clip duration in seconds (<= 3.0)
    speed_to_fit: bool = False  # Speed up video so entire clip fits in <= 3.0s
    loop_mode: str = "normal"  # "normal" or "pingpong" (boomerang)
    fit_mode: str | None = (
        None  # "contain", "crop", "pad", or "stretch" (default: "contain" for sticker, "crop" for emoji)
    )
    fps: int = 30  # Max 30 FPS
    crf: int = 30  # Base VP9 CRF quality (0-63)
    remove_bg: str | None = (
        None  # Color to key out, e.g. "green", "white", "black", "#hex"
    )
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
        config: ConversionConfig | None = None,
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

        effective_fit = cfg.fit_mode or ("crop" if cfg.mode == "emoji" else "contain")
        needs_alpha = (
            (cfg.preserve_alpha and info.has_alpha)
            or (cfg.remove_bg is not None)
            or (effective_fit == "pad")
        )
        pix_fmt = "yuva420p" if needs_alpha else "yuv420p"

        input_args = self._build_input_args(in_p, info.duration, timing.start_time)
        initial_params = EncodingParams(
            crf=cfg.crf, bitrate_kbps=0, two_pass=False, fps=min(cfg.fps, 30)
        )

        vfilters = self._build_video_filters(cfg, timing, initial_params.fps)
        self._run_encode(
            in_p,
            out_p,
            vfilters,
            initial_params,
            pix_fmt,
            timing.clip_duration,
            input_args,
        )

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
            self._run_encode(
                in_p,
                out_p,
                curr_filters,
                reencode_params,
                pix_fmt,
                timing.clip_duration,
                input_args,
            )
            file_size = out_p.stat().st_size
            attempt += 1

        return validate_telegram_webm(out_p, mode=cfg.mode)

    def _plan_timing(self, info: MediaInfo, cfg: ConversionConfig) -> TimingPlan:
        start_t = cfg.start_time or 0.0
        if start_t < 0:
            raise ValidationError(
                f"Start time cannot be negative (got: {start_t:.2f}s)"
            )

        if info.duration > 0:
            if start_t >= info.duration:
                raise ValidationError(
                    f"Start time ({start_t:.2f}s) cannot be greater than or equal to video duration ({info.duration:.2f}s)."
                )
            if info.duration - start_t < 0.05:
                raise ValidationError(
                    f"Remaining video duration from offset {start_t:.2f}s is too short (< 0.05s) to convert."
                )

        available_dur = (
            max(info.duration - start_t, 0.1) if info.duration > 0 else cfg.max_duration
        )

        if cfg.speed_to_fit and available_dur > cfg.max_duration:
            clip_dur = cfg.max_duration
            pts_speed_factor = cfg.max_duration / available_dur
        else:
            pts_speed_factor = 1.0
            requested_dur = cfg.duration or available_dur
            clip_dur = min(requested_dur, available_dur, cfg.max_duration)

        half_dur = (clip_dur / 2.0) if cfg.loop_mode == "pingpong" else clip_dur
        return TimingPlan(
            start_time=start_t,
            clip_duration=clip_dur,
            half_duration=half_dur,
            pts_speed_factor=pts_speed_factor,
        )

    def _build_input_args(
        self, in_p: Path, duration: float, start_t: float
    ) -> list[str]:
        args = []
        if in_p.suffix.lower() in STATIC_IMAGE_EXTENSIONS and duration <= 0.1:
            args.extend(["-loop", "1"])
        if start_t > 0:
            args.extend(["-ss", f"{start_t:.4f}"])
        return args

    def _build_video_filters(
        self, cfg: ConversionConfig, timing: TimingPlan, target_fps: int
    ) -> str:
        filters: list[str] = []

        if cfg.speed_to_fit and timing.pts_speed_factor < 1.0:
            filters.append(f"setpts={timing.pts_speed_factor:.6f}*PTS")

        if cfg.remove_bg:
            color = cfg.remove_bg.lower()
            key_map = {
                "green": "colorkey=0x00FF00:0.3:0.15",
                "black": "colorkey=0x000000:0.1:0.1",
                "white": "colorkey=0xFFFFFF:0.1:0.1",
            }
            filters.append(
                key_map.get(color, f"colorkey={color.replace('#', '0x')}:0.25:0.15")
            )

        effective_fit = cfg.fit_mode or ("crop" if cfg.mode == "emoji" else "contain")

        if cfg.mode == "emoji":
            if effective_fit in ("pad", "contain"):
                filters.append(
                    "scale='if(gte(iw,ih),100,-2)':'if(gte(iw,ih),-2,100)',"
                    "pad=100:100:(100-iw)/2:(100-ih)/2:color=0x00000000"
                )
            elif effective_fit == "stretch":
                filters.append("scale=100:100")
            else:  # crop
                filters.append("crop=min(iw\\,ih):min(iw\\,ih),scale=100:100")
        else:
            # Sticker mode
            if effective_fit == "crop":
                filters.append("crop=min(iw\\,ih):min(iw\\,ih),scale=512:512")
            elif effective_fit == "pad":
                filters.append(
                    "scale='if(gte(iw,ih),512,-2)':'if(gte(iw,ih),-2,512)',"
                    "pad=512:512:(512-iw)/2:(512-ih)/2:color=0x00000000"
                )
            elif effective_fit == "stretch":
                filters.append("scale=512:512")
            else:  # contain (default)
                # exactly 512px on longer side, <= 512px on other, even dimensions
                filters.append("scale='if(gte(iw,ih),512,-2)':'if(gte(iw,ih),-2,512)'")

        filters.append(f"fps={min(target_fps, 30)}")
        base_chain = ",".join(filters)

        if cfg.loop_mode == "pingpong":
            return (
                f"[0:v]{base_chain},trim=0:{timing.half_duration:.4f},setpts=PTS-STARTPTS,split[fwd][rev_in];"
                f"[rev_in]reverse[rev];"
                f"[fwd][rev]concat=n=2:v=1:a=0"
            )
        return (
            f"[0:v]{base_chain},trim=0:{timing.clip_duration:.4f},setpts=PTS-STARTPTS"
        )

    def _execute(
        self, cmd: list[str], file_name: str, stage_name: str
    ) -> subprocess.CompletedProcess[str]:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if res.returncode != 0:
            raise EncodingError(
                f"{stage_name} failed for {file_name}",
                cmd=cmd,
                returncode=res.returncode,
                stderr=res.stderr,
            )
        if stage_name != "FFmpeg 2-pass (pass 1)" and (
            "Output file is empty, nothing was encoded" in res.stderr
        ):
            raise EncodingError(
                f"{stage_name} produced an empty video (0 frames) for {file_name}. "
                "Check that the start time offset and duration fall within the video's range.",
                cmd=cmd,
                returncode=res.returncode,
                stderr=res.stderr,
            )
        return res

    def _run_encode(
        self,
        in_p: Path,
        out_p: Path,
        vfilters: str,
        params: EncodingParams,
        pix_fmt: str,
        clip_dur: float,
        input_args: list[str] | None = None,
    ) -> None:
        """Executes FFmpeg encoding command (single-pass or two-pass)."""
        is_complex = ";" in vfilters or vfilters.startswith("[")
        filter_args = ["-filter_complex", vfilters] if is_complex else ["-vf", vfilters]
        base_cmd = [
            self.ffmpeg_bin,
            "-y",
            "-autorotate",
            *(input_args or []),
            "-i",
            str(in_p),
            *filter_args,
            "-c:v",
            "libvpx-vp9",
            "-pix_fmt",
            pix_fmt,
        ]

        if not params.two_pass:
            cmd = base_cmd + [
                "-crf",
                str(params.crf),
                "-b:v",
                "0",
                "-an",
                "-t",
                f"{clip_dur:.4f}",
                str(out_p),
            ]
            self._execute(cmd, in_p.name, "FFmpeg encoding")
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                passlogfile = os.path.join(tmpdir, "ffmpeg2pass")
                rate_args = [
                    "-b:v",
                    f"{params.bitrate_kbps}k",
                    "-minrate",
                    f"{int(params.bitrate_kbps * 0.5)}k",
                    "-maxrate",
                    f"{params.maxrate_kbps}k",
                    "-bufsize",
                    f"{params.bufsize_kbps}k",
                    "-crf",
                    str(params.crf),
                ]

                # Pass 1
                cmd_pass1 = (
                    base_cmd
                    + rate_args
                    + [
                        "-pass",
                        "1",
                        "-passlogfile",
                        passlogfile,
                        "-an",
                        "-t",
                        f"{clip_dur:.4f}",
                        "-f",
                        "null",
                        os.devnull,
                    ]
                )
                self._execute(cmd_pass1, in_p.name, "FFmpeg 2-pass (pass 1)")

                # Pass 2
                cmd_pass2 = (
                    base_cmd
                    + rate_args
                    + [
                        "-pass",
                        "2",
                        "-passlogfile",
                        passlogfile,
                        "-an",
                        "-t",
                        f"{clip_dur:.4f}",
                        str(out_p),
                    ]
                )
                self._execute(cmd_pass2, in_p.name, "FFmpeg 2-pass (pass 2)")

        if out_p.exists():
            out_size = out_p.stat().st_size
            if out_size < 1024:
                out_p.unlink(missing_ok=True)
                raise EncodingError(
                    f"FFmpeg encoding produced an empty or incomplete video ({out_size} bytes) for {in_p.name}. "
                    "Please ensure the start time and duration are within the video duration.",
                    cmd=cmd if not params.two_pass else cmd_pass2,
                )
