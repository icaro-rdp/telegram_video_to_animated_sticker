"""Media probing and Telegram compliance validation."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


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


def ensure_ffprobe_available() -> str:
    path = shutil.which("ffprobe")
    if not path:
        raise RuntimeError(
            "ffprobe is not found in PATH. Please install FFmpeg (e.g. brew install ffmpeg / apt install ffmpeg)."
        )
    return path


def ensure_ffmpeg_available() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError(
            "ffmpeg is not found in PATH. Please install FFmpeg (e.g. brew install ffmpeg / apt install ffmpeg)."
        )
    return path


def probe_media(file_path: str | Path) -> MediaInfo:
    """Probes media file using ffprobe and extracts key technical attributes."""
    ffprobe_bin = ensure_ffprobe_available()
    file_path_str = str(Path(file_path).resolve())

    if not os.path.isfile(file_path_str):
        raise FileNotFoundError(f"File not found: {file_path_str}")

    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path_str,
    ]

    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    probe_data = json.loads(res.stdout)

    format_data = probe_data.get("format", {})
    streams = probe_data.get("streams", [])

    size_bytes = int(format_data.get("size") or os.path.getsize(file_path_str))
    duration = float(format_data.get("duration") or 0.0)

    video_stream = None
    has_audio = False

    for st in streams:
        c_type = st.get("codec_type")
        if c_type == "video" and video_stream is None:
            video_stream = st
        elif c_type == "audio":
            has_audio = True

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

        # Duration fallback from video stream tags
        if duration <= 0:
            if "duration" in video_stream:
                duration = float(video_stream["duration"])
            elif "TAG:DURATION" in video_stream:
                # e.g. 00:00:02.000000000
                tag_dur = video_stream["TAG:DURATION"]
                try:
                    parts = tag_dur.split(":")
                    if len(parts) == 3:
                        duration = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                except Exception:
                    pass

        # Calculate FPS
        r_rate = video_stream.get("r_frame_rate", "0/1")
        if "/" in r_rate:
            num, den = r_rate.split("/")
            if float(den) > 0:
                fps = float(num) / float(den)
        else:
            fps = float(r_rate or 0.0)

        # Alpha detection
        tags = video_stream.get("tags", {})
        if tags.get("alpha_mode") == "1" or (pix_fmt and "a" in pix_fmt):
            has_alpha = True

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
    """
    Validates a file against Telegram Video Sticker / Emoji guidelines:
    - Format: .WEBM
    - Codec: VP9
    - Audio: No audio stream
    - Duration: <= 3.0s (allow minor muxing float variance up to 3.05s)
    - FPS: <= 30.05 FPS
    - Size: <= 256 KB (262,144 bytes)
    - Sticker dimensions: One side exactly 512, other side <= 512
    - Emoji dimensions: Exactly 100x100
    """
    mode = mode.lower()
    if mode not in ("sticker", "emoji"):
        raise ValueError("mode must be 'sticker' or 'emoji'")

    info = probe_media(file_path)
    issues: List[str] = []

    # 1. Format check
    if not any(f in info.format_name for f in ("webm", "matroska")):
        issues.append(f"Format is not WebM (got: {info.format_name})")

    # 2. Codec check
    if info.video_codec != "vp9":
        issues.append(f"Video codec must be VP9 (got: {info.video_codec})")

    # 3. Audio check
    if info.has_audio:
        issues.append("Video must not contain an audio stream")

    # 4. Duration check (Telegram limit: max 3.0s)
    if info.duration > 3.05:
        issues.append(f"Duration must not exceed 3.0s (got: {info.duration:.2f}s)")

    # 5. FPS check (Telegram limit: up to 30 FPS)
    if info.fps and info.fps > 30.05:
        issues.append(f"FPS must not exceed 30 (got: {info.fps:.2f})")

    # 6. File size check (Telegram limit: max 256 KB = 262,144 bytes)
    MAX_BYTES = 256 * 1024
    if info.size_bytes > MAX_BYTES:
        excess = info.size_bytes - MAX_BYTES
        issues.append(
            f"File size exceeds 256 KB limit: {info.size_kb:.2f} KB ({excess} bytes over limit)"
        )

    # 7. Dimension checks
    if info.width is None or info.height is None or info.width <= 0 or info.height <= 0:
        issues.append("Unable to determine video dimensions")
    elif mode == "sticker":
        max_dim = max(info.width, info.height)
        min_dim = min(info.width, info.height)
        if max_dim != 512:
            issues.append(f"For stickers, one side must be exactly 512px (got: {info.width}x{info.height})")
        if min_dim > 512:
            issues.append(f"For stickers, the other side must be <= 512px (got: {info.width}x{info.height})")
    elif mode == "emoji":
        if info.width != 100 or info.height != 100:
            issues.append(f"For emoji, dimensions must be exactly 100x100px (got: {info.width}x{info.height})")

    return ValidationResult(
        valid=(len(issues) == 0),
        mode=mode,
        issues=issues,
        info=info,
    )
