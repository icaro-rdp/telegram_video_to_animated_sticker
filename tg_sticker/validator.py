"""Media probing and Telegram compliance validation."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .exceptions import (
    CorruptMediaError,
    FFmpegNotFoundError,
    FFprobeNotFoundError,
    MediaNotFoundError,
    ProbeError,
    ValidationError,
)

MAX_STICKER_BYTES = 256 * 1024
MAX_STICKER_DURATION = 3.05
MAX_STICKER_FPS = 30.05


@dataclass
class MediaInfo:
    file_path: str
    format_name: str
    duration: float
    size_bytes: int
    video_codec: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    has_audio: bool = False
    has_alpha: bool = False
    pix_fmt: Optional[str] = None
    raw_probe: Dict[str, Any] = field(default_factory=dict)

    @property
    def size_kb(self) -> float:
        return self.size_bytes / 1024.0


@dataclass
class ValidationResult:
    valid: bool
    mode: str
    issues: List[str]
    info: Optional[MediaInfo] = None

    def summary(self) -> str:
        if self.valid:
            return f"VALID Telegram {self.mode.capitalize()} ({self.info.size_kb:.1f} KB, {self.info.width}x{self.info.height}, {self.info.duration:.2f}s, {self.info.fps:.1f} FPS)"
        return f"INVALID Telegram {self.mode.capitalize()}: " + "; ".join(self.issues)


def _resolve_tool(tool_name: str, error_cls: type[Exception]) -> str:
    path = shutil.which(tool_name)
    if not path:
        raise error_cls(
            f"{tool_name} is not found in PATH. Please install FFmpeg (e.g. brew install ffmpeg / apt install ffmpeg)."
        )
    return path


def ensure_ffprobe_available() -> str:
    return _resolve_tool("ffprobe", FFprobeNotFoundError)


def ensure_ffmpeg_available() -> str:
    return _resolve_tool("ffmpeg", FFmpegNotFoundError)


def _parse_fps(rate_str: Optional[str]) -> Optional[float]:
    if not rate_str or rate_str == "0/0":
        return None
    if "/" in rate_str:
        num, den = rate_str.split("/")
        den_f = float(den)
        return float(num) / den_f if den_f > 0 else 0.0
    return float(rate_str)


def _extract_stream_duration(st: Dict[str, Any], fallback: float) -> float:
    if fallback > 0:
        return fallback
    if "duration" in st:
        return float(st["duration"])
    if "TAG:DURATION" in st:
        parts = st["TAG:DURATION"].split(":")
        if len(parts) == 3:
            try:
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            except (ValueError, IndexError):
                pass
    return 0.0


def probe_media(file_path: str | Path) -> MediaInfo:
    """Probes media file using ffprobe and extracts technical attributes."""
    ffprobe_bin = ensure_ffprobe_available()
    file_path_str = str(Path(file_path).resolve())

    if not os.path.isfile(file_path_str):
        raise MediaNotFoundError(f"Media file not found: {file_path_str}")

    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path_str,
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise ProbeError(f"ffprobe failed to inspect {file_path_str}: {e.stderr.strip()}", stderr=e.stderr)

    try:
        probe_data = json.loads(res.stdout)
    except json.JSONDecodeError as e:
        raise CorruptMediaError(f"Could not parse probe metadata for {file_path_str}: {e}")

    format_data = probe_data.get("format", {})
    streams = probe_data.get("streams", [])

    size_bytes = int(format_data.get("size") or os.path.getsize(file_path_str))
    duration = float(format_data.get("duration") or 0.0)

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)

    video_codec = None
    width = None
    height = None
    fps = None
    has_alpha = False
    pix_fmt = None

    if video_stream:
        video_codec = video_stream.get("codec_name")
        width = int(video_stream.get("width") or 0)
        height = int(video_stream.get("height") or 0)
        pix_fmt = video_stream.get("pix_fmt")
        duration = _extract_stream_duration(video_stream, duration)
        fps = _parse_fps(video_stream.get("r_frame_rate"))

        tags = video_stream.get("tags", {})
        has_alpha = tags.get("alpha_mode") == "1" or bool(pix_fmt and "a" in pix_fmt)

    return MediaInfo(
        file_path=file_path_str,
        format_name=format_data.get("format_name", ""),
        duration=duration,
        size_bytes=size_bytes,
        video_codec=video_codec,
        width=width,
        height=height,
        fps=fps,
        has_audio=has_audio,
        has_alpha=has_alpha,
        pix_fmt=pix_fmt,
        raw_probe=probe_data,
    )


def validate_telegram_webm(file_path: str | Path, mode: str = "sticker") -> ValidationResult:
    """Validates a file against Telegram Video Sticker / Emoji technical guidelines."""
    mode = mode.lower()
    if mode not in ("sticker", "emoji"):
        raise ValidationError(f"Invalid mode '{mode}': must be 'sticker' or 'emoji'")

    info = probe_media(file_path)
    issues: List[str] = []

    if not any(f in info.format_name for f in ("webm", "matroska")):
        issues.append(f"Format is not WebM (got: {info.format_name})")

    if info.video_codec != "vp9":
        issues.append(f"Video codec must be VP9 (got: {info.video_codec})")

    if info.has_audio:
        issues.append("Video must not contain an audio stream")

    if info.duration > MAX_STICKER_DURATION:
        issues.append(f"Duration must not exceed 3.0s (got: {info.duration:.2f}s)")

    if info.fps and info.fps > MAX_STICKER_FPS:
        issues.append(f"FPS must not exceed 30 (got: {info.fps:.2f})")

    if info.size_bytes > MAX_STICKER_BYTES:
        excess = info.size_bytes - MAX_STICKER_BYTES
        issues.append(f"File size exceeds 256 KB limit: {info.size_kb:.2f} KB ({excess} bytes over limit)")

    if not info.width or not info.height:
        issues.append("Unable to determine video dimensions")
    elif mode == "sticker":
        max_dim, min_dim = max(info.width, info.height), min(info.width, info.height)
        if max_dim != 512:
            issues.append(f"For stickers, one side must be exactly 512px (got: {info.width}x{info.height})")
        if min_dim > 512:
            issues.append(f"For stickers, the other side must be <= 512px (got: {info.width}x{info.height})")
    elif mode == "emoji":
        if info.width != 100 or info.height != 100:
            issues.append(f"For emoji, dimensions must be exactly 100x100px (got: {info.width}x{info.height})")

    return ValidationResult(valid=(len(issues) == 0), mode=mode, issues=issues, info=info)
