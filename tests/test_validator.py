"""Tests for media probing and Telegram specification validator."""

import subprocess
from pathlib import Path
import pytest

from tg_sticker.validator import probe_media, validate_telegram_webm


@pytest.fixture(scope="session")
def valid_sticker_webm(tmp_path_factory):
    """Creates a synthetic 512x288 30fps VP9 WebM video without audio."""
    tmp_dir = tmp_path_factory.mktemp("media")
    out_file = tmp_dir / "valid_sticker.webm"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2.0:size=512x288:rate=30",
        "-c:v", "libvpx-vp9",
        "-crf", "30",
        "-b:v", "0",
        "-an",
        str(out_file),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_file


@pytest.fixture(scope="session")
def valid_emoji_webm(tmp_path_factory):
    """Creates a synthetic 100x100 30fps VP9 WebM video without audio."""
    tmp_dir = tmp_path_factory.mktemp("media")
    out_file = tmp_dir / "valid_emoji.webm"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1.5:size=100x100:rate=30",
        "-c:v", "libvpx-vp9",
        "-crf", "30",
        "-b:v", "0",
        "-an",
        str(out_file),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_file


@pytest.fixture(scope="session")
def invalid_duration_webm(tmp_path_factory):
    """Creates a 5-second video (violates <= 3.0s rule)."""
    tmp_dir = tmp_path_factory.mktemp("media")
    out_file = tmp_dir / "invalid_duration.webm"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=5.0:size=512x288:rate=30",
        "-c:v", "libvpx-vp9",
        "-crf", "30",
        "-b:v", "0",
        "-an",
        str(out_file),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_file


@pytest.fixture(scope="session")
def audio_webm(tmp_path_factory):
    """Creates a video with an audio track (violates no-audio rule)."""
    tmp_dir = tmp_path_factory.mktemp("media")
    out_file = tmp_dir / "with_audio.webm"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1.0:size=512x288:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1.0",
        "-c:v", "libvpx-vp9",
        "-c:a", "libopus",
        str(out_file),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_file


def test_probe_media(valid_sticker_webm):
    info = probe_media(valid_sticker_webm)
    assert info.width == 512
    assert info.height == 288
    assert info.video_codec == "vp9"
    assert info.has_audio is False
    assert 1.9 <= info.duration <= 2.1
    assert 29.0 <= info.fps <= 31.0


def test_validate_sticker_success(valid_sticker_webm):
    res = validate_telegram_webm(valid_sticker_webm, mode="sticker")
    assert res.valid is True
    assert len(res.issues) == 0


def test_validate_emoji_success(valid_emoji_webm):
    res = validate_telegram_webm(valid_emoji_webm, mode="emoji")
    assert res.valid is True
    assert len(res.issues) == 0


def test_validate_duration_failure(invalid_duration_webm):
    res = validate_telegram_webm(invalid_duration_webm, mode="sticker")
    assert res.valid is False
    assert any("Duration must not exceed 3.0s" in issue for issue in res.issues)


def test_validate_audio_failure(audio_webm):
    res = validate_telegram_webm(audio_webm, mode="sticker")
    assert res.valid is False
    assert any("must not contain an audio stream" in issue for issue in res.issues)


def test_validate_dimension_failure(valid_sticker_webm):
    # Testing sticker file (512x288) against emoji validation (requires 100x100)
    res = validate_telegram_webm(valid_sticker_webm, mode="emoji")
    assert res.valid is False
    assert any("100x100px" in issue for issue in res.issues)
