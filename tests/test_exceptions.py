"""Unit tests for domain-specific exception hierarchy and error handling."""

import pytest
from pathlib import Path

from tg_sticker.exceptions import (
    TelegramStickerError,
    DependencyError,
    FFmpegNotFoundError,
    FFprobeNotFoundError,
    MediaError,
    MediaNotFoundError,
    DirectoryNotFoundError,
    ProcessingError,
    FFmpegExecutionError,
    EncodingError,
    ProbeError,
    ValidationError,
    SizeConstraintExceededError,
)
from tg_sticker.converter import TelegramConverter, ConversionConfig
from tg_sticker.validator import probe_media, validate_telegram_webm
from tg_sticker.batch import find_video_files


def test_exception_inheritance_hierarchy():
    """Verify that all domain exceptions properly inherit from TelegramStickerError."""
    assert issubclass(DependencyError, TelegramStickerError)
    assert issubclass(FFmpegNotFoundError, DependencyError)
    assert issubclass(FFprobeNotFoundError, DependencyError)

    assert issubclass(MediaError, TelegramStickerError)
    assert issubclass(MediaNotFoundError, (MediaError, FileNotFoundError))
    assert issubclass(DirectoryNotFoundError, (MediaError, NotADirectoryError))

    assert issubclass(ProcessingError, TelegramStickerError)
    assert issubclass(FFmpegExecutionError, ProcessingError)
    assert issubclass(EncodingError, FFmpegExecutionError)
    assert issubclass(ProbeError, ProcessingError)

    assert issubclass(ValidationError, TelegramStickerError)
    assert issubclass(SizeConstraintExceededError, ValidationError)


def test_media_not_found_error(tmp_path):
    """probe_media and converter.convert should raise MediaNotFoundError for missing files."""
    missing_path = tmp_path / "nonexistent_video_12345.mp4"

    with pytest.raises(MediaNotFoundError) as exc_info:
        probe_media(missing_path)
    assert "Media file not found" in str(exc_info.value)
    assert isinstance(exc_info.value, FileNotFoundError)

    converter = TelegramConverter()
    with pytest.raises(MediaNotFoundError):
        converter.convert(missing_path, tmp_path / "out.webm")


def test_directory_not_found_error(tmp_path):
    """find_video_files should raise DirectoryNotFoundError for missing directory."""
    missing_dir = tmp_path / "nonexistent_directory_999"
    with pytest.raises(DirectoryNotFoundError) as exc_info:
        find_video_files(missing_dir)
    assert isinstance(exc_info.value, NotADirectoryError)


def test_probe_corrupted_file(tmp_path):
    """probe_media should raise ProbeError on unreadable/corrupted files."""
    corrupt_file = tmp_path / "corrupt.mp4"
    corrupt_file.write_bytes(b"NOT A REAL VIDEO CONTENT JUNK DATA")

    with pytest.raises(ProbeError) as exc_info:
        probe_media(corrupt_file)
    assert "ffprobe failed to inspect" in str(exc_info.value)


def test_validation_invalid_mode(tmp_path):
    """validate_telegram_webm should raise ValidationError for unrecognized mode."""
    dummy_file = tmp_path / "dummy.webm"
    dummy_file.write_text("fake")

    with pytest.raises(ValidationError) as exc_info:
        validate_telegram_webm(dummy_file, mode="invalid_mode")
    assert "Invalid mode 'invalid_mode'" in str(exc_info.value)


def test_ffmpeg_execution_error_attributes():
    """FFmpegExecutionError should preserve command, returncode, and stderr."""
    err = FFmpegExecutionError(
        message="Encoding failed",
        cmd=["ffmpeg", "-i", "in.mp4", "out.webm"],
        returncode=1,
        stderr="Unknown encoder libvpx-unknown\nConversion failed!\n",
    )
    assert err.returncode == 1
    assert "Conversion failed!" in str(err)
    assert err.cmd == ["ffmpeg", "-i", "in.mp4", "out.webm"]
