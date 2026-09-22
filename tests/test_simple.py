"""Tests for the simple runner CLI."""

import subprocess

import pytest

from tg_sticker.simple import run
from tg_sticker.validator import probe_media


@pytest.fixture
def sample_video(tmp_path):
    video = tmp_path / "test.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=1.0:size=640x360:rate=25",
        "-c:v",
        "libx264",
        str(video),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return video


def test_simple_run_fit_crop(sample_video, tmp_path):
    out_dir = tmp_path / "output"
    exit_code = run(
        argv=[str(sample_video), "--fit", "crop", "-o", str(out_dir)],
    )
    assert exit_code == 0
    out_file = out_dir / "test.webm"
    assert out_file.exists()

    info = probe_media(out_file)
    assert info.width == 512
    assert info.height == 512


def test_simple_run_default_fit(sample_video, tmp_path):
    out_dir = tmp_path / "output_default"
    exit_code = run(
        argv=[str(sample_video), "-o", str(out_dir)],
    )
    assert exit_code == 0
    out_file = out_dir / "test.webm"
    assert out_file.exists()

    info = probe_media(out_file)
    assert info.width == 512
    assert info.height == 288
