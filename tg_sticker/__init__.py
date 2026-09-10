"""Telegram Video to Animated Sticker / Emoji Converter."""

from .converter import TelegramConverter, ConversionConfig
from .validator import validate_telegram_webm, probe_media
from .exceptions import (
    TelegramStickerError,
    DependencyError,
    FFmpegNotFoundError,
    FFprobeNotFoundError,
    MediaError,
    MediaNotFoundError,
    DirectoryNotFoundError,
    UnsupportedFormatError,
    CorruptMediaError,
    ProcessingError,
    FFmpegExecutionError,
    EncodingError,
    ProbeError,
    ValidationError,
    SizeConstraintExceededError,
    DimensionConstraintError,
    DurationConstraintError,
)

__all__ = [
    "TelegramConverter",
    "ConversionConfig",
    "validate_telegram_webm",
    "probe_media",
    "TelegramStickerError",
    "DependencyError",
    "FFmpegNotFoundError",
    "FFprobeNotFoundError",
    "MediaError",
    "MediaNotFoundError",
    "DirectoryNotFoundError",
    "UnsupportedFormatError",
    "CorruptMediaError",
    "ProcessingError",
    "FFmpegExecutionError",
    "EncodingError",
    "ProbeError",
    "ValidationError",
    "SizeConstraintExceededError",
    "DimensionConstraintError",
    "DurationConstraintError",
]
__version__ = "0.1.0"
