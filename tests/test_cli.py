"""Tests for CLI subcommands and JSON output formatting."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def sample_video(tmp_path: Path) -> Path:
    """Generate a brief test video using ffmpeg."""
    video = tmp_path / "cli_test.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=0.5:size=320x240:rate=15",
        "-c:v",
        "libx264",
        str(video),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return video


def test_cli_convert_json(sample_video: Path, tmp_path: Path) -> None:
    """Test tg-sticker convert with --json flag emits valid JSON."""
    out_file = tmp_path / "cli_out.webm"
    cmd = [
        sys.executable,
        "-m",
        "tg_sticker.cli",
        "convert",
        str(sample_video),
        "-o",
        str(out_file),
        "--fps",
        "15",
        "--duration",
        "0.5",
        "--json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(proc.stdout.strip())
    assert data["success"] is True
    assert data["valid"] is True
    assert data["filename"] == "cli_out.webm"
    assert data["info"]["width"] <= 512
    assert data["info"]["height"] <= 512
    assert data["info"]["codec"] == "vp9"


def test_cli_check_json(sample_video: Path, tmp_path: Path) -> None:
    """Test tg-sticker check with --json flag validates a converted file."""
    out_file = tmp_path / "valid_sticker.webm"
    conv_cmd = [
        sys.executable,
        "-m",
        "tg_sticker.cli",
        "convert",
        str(sample_video),
        "-o",
        str(out_file),
        "--fps",
        "15",
        "--duration",
        "0.5",
        "--json",
    ]
    subprocess.run(conv_cmd, check=True, capture_output=True)

    check_cmd = [
        sys.executable,
        "-m",
        "tg_sticker.cli",
        "check",
        str(out_file),
        "--json",
    ]
    proc = subprocess.run(check_cmd, capture_output=True, text=True, check=True)
    data = json.loads(proc.stdout.strip())
    assert data["valid"] is True
    assert "checks" in data
    assert data["checks"]["Container format (.WEBM)"]["passed"] is True
    assert data["checks"]["Video codec (VP9)"]["passed"] is True


def test_cli_convert_missing_file_json(tmp_path: Path) -> None:
    """Test convert with non-existent file produces JSON error."""
    non_existent = tmp_path / "not_there.mp4"
    cmd = [
        sys.executable,
        "-m",
        "tg_sticker.cli",
        "convert",
        str(non_existent),
        "--json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert proc.returncode != 0
    data = json.loads(proc.stdout.strip())
    assert data["success"] is False
    assert data["error_type"] == "MediaNotFoundError"


def test_cli_convert_crop_json(sample_video: Path, tmp_path: Path) -> None:
    """Test convert with custom --crop flag produces valid sticker with proper dimensions."""
    out_file = tmp_path / "cli_crop_out.webm"
    cmd = [
        sys.executable,
        "-m",
        "tg_sticker.cli",
        "convert",
        str(sample_video),
        "-o",
        str(out_file),
        "--crop",
        "20,20,100,100",
        "--fps",
        "15",
        "--duration",
        "0.5",
        "--json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(proc.stdout.strip())
    assert data["success"] is True
    assert data["valid"] is True
    assert data["info"]["width"] == 512
    assert data["info"]["height"] == 512
