"""Tests for batch directory processing."""

import subprocess

import pytest

from tg_sticker.batch import find_video_files, process_batch
from tg_sticker.converter import ConversionConfig


@pytest.fixture
def populated_input_dir(tmp_path):
    """Creates multiple synthetic video clips in an input directory."""
    in_dir = tmp_path / "input_videos"
    in_dir.mkdir()

    for name, dur in [("clip1.mp4", 1.0), ("clip2.mov", 1.5), ("anim.gif", 0.8)]:
        fpath = in_dir / name
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc=duration={dur}:size=320x240:rate=25",
            str(fpath),
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    # Add a non-video dummy file
    (in_dir / "notes.txt").write_text("should be ignored")
    return in_dir


def test_find_video_files(populated_input_dir):
    files = find_video_files(populated_input_dir)
    names = [f.name for f in files]
    assert "clip1.mp4" in names
    assert "clip2.mov" in names
    assert "anim.gif" in names
    assert "notes.txt" not in names


def test_process_batch(populated_input_dir, tmp_path):
    out_dir = tmp_path / "output_stickers"
    summary = process_batch(
        input_dir=populated_input_dir,
        output_dir=out_dir,
        config=ConversionConfig(mode="sticker"),
    )

    assert summary.total == 3
    assert summary.succeeded == 3
    assert summary.failed == 0
    assert summary.skipped == 0

    assert (out_dir / "clip1.webm").exists()
    assert (out_dir / "clip2.webm").exists()
    assert (out_dir / "anim.webm").exists()

    # Verify second run skips existing
    summary2 = process_batch(
        input_dir=populated_input_dir,
        output_dir=out_dir,
        overwrite=False,
    )
    assert summary2.skipped == 3
    assert summary2.succeeded == 0
