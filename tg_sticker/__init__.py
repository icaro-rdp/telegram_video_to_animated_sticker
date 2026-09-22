"""Telegram Video to Animated Sticker / Emoji Converter."""

from .converter import ConversionConfig, TelegramConverter
from .exceptions import (
    CorruptMediaError,
    DependencyError,
    DimensionConstraintError,
    DirectoryNotFoundError,
    DurationConstraintError,
    EncodingError,
    FFmpegExecutionError,
    FFmpegNotFoundError,
    FFprobeNotFoundError,
    MediaError,
    MediaNotFoundError,
    ProbeError,
    ProcessingError,
    SizeConstraintExceededError,
    TelegramStickerError,
    UnsupportedFormatError,
    ValidationError,
)
from .validator import probe_media, validate_telegram_webm

__all__ = [
    "ConversionConfig",
    "CorruptMediaError",
    "DependencyError",
    "DimensionConstraintError",
    "DirectoryNotFoundError",
    "DurationConstraintError",
    "EncodingError",
    "FFmpegExecutionError",
    "FFmpegNotFoundError",
    "FFprobeNotFoundError",
    "MediaError",
    "MediaNotFoundError",
    "ProbeError",
    "ProcessingError",
    "SizeConstraintExceededError",
    "TelegramConverter",
    "TelegramStickerError",
    "UnsupportedFormatError",
    "ValidationError",
    "probe_media",
    "validate_telegram_webm",
]
__version__ = "0.1.0"
