"""Custom domain-specific exception hierarchy for telegram-sticker-converter."""

from __future__ import annotations

from typing import List, Optional


class TelegramStickerError(Exception):
    """Base exception for all errors in the telegram-sticker-converter package."""
    pass


# --- System & Dependency Exceptions ---

class DependencyError(TelegramStickerError):
    """Raised when a system dependency (e.g. ffmpeg or ffprobe) is missing or incompatible."""
    pass


class FFmpegNotFoundError(DependencyError):
    """Raised when the ffmpeg executable cannot be found in PATH."""
    pass


class FFprobeNotFoundError(DependencyError):
    """Raised when the ffprobe executable cannot be found in PATH."""
    pass


# --- Media File & Format Exceptions ---

class MediaError(TelegramStickerError):
    """Base class for media file input and decoding errors."""
    pass


class MediaNotFoundError(MediaError, FileNotFoundError):
    """Raised when an input media file cannot be found."""
    pass


class DirectoryNotFoundError(MediaError, NotADirectoryError):
    """Raised when an input or output directory cannot be found."""
    pass


class UnsupportedFormatError(MediaError):
    """Raised when an input format is unrecognized or unsupported."""
    pass


class CorruptMediaError(MediaError):
    """Raised when media data is corrupted, empty, or cannot be parsed."""
    pass


# --- Processing & Encoding Exceptions ---

class ProcessingError(TelegramStickerError):
    """Base class for video processing, filtering, and encoding errors."""
    pass


class FFmpegExecutionError(ProcessingError):
    """Raised when an FFmpeg subprocess fails execution."""

    def __init__(
        self,
        message: str,
        cmd: Optional[List[str]] = None,
        returncode: Optional[int] = None,
        stderr: Optional[str] = None,
    ):
        super().__init__(message)
        self.cmd = cmd or []
        self.returncode = returncode
        self.stderr = stderr or ""

    def __str__(self) -> str:
        base = super().__str__()
        if self.stderr:
            # Extract last line or concise summary from stderr
            err_lines = [line.strip() for line in self.stderr.splitlines() if line.strip()]
            tail = err_lines[-1] if err_lines else ""
            return f"{base} (Exit code: {self.returncode}): {tail}"
        return base


class EncodingError(FFmpegExecutionError):
    """Raised when VP9 encoding or multi-pass encoding fails."""
    pass


class ProbeError(FFmpegExecutionError):
    """Raised when ffprobe fails to parse media streams or metadata."""
    pass


# --- Telegram Specification / Constraint Exceptions ---

class ValidationError(TelegramStickerError):
    """Raised when a video fails Telegram sticker or emoji technical specifications."""

    def __init__(self, message: str, issues: Optional[List[str]] = None):
        super().__init__(message)
        self.issues = issues or []


class SizeConstraintExceededError(ValidationError):
    """Raised when a sticker cannot be compressed below Telegram's 256 KB limit."""

    def __init__(self, current_size_bytes: int, max_bytes: int = 256 * 1024):
        msg = f"File size {current_size_bytes / 1024:.1f} KB exceeds Telegram 256 KB limit ({max_bytes} bytes)."
        super().__init__(msg, issues=[msg])
        self.current_size_bytes = current_size_bytes
        self.max_bytes = max_bytes


class DimensionConstraintError(ValidationError):
    """Raised when output dimensions violate Telegram sticker (512px) or emoji (100x100) rules."""
    pass


class DurationConstraintError(ValidationError):
    """Raised when video duration exceeds Telegram's 3.0s limit."""
    pass
