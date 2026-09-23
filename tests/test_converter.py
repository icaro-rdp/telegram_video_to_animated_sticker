"""Integration tests for TelegramConverter."""

import subprocess

import pytest

from tg_sticker.converter import (
    ConversionConfig,
    TelegramConverter,
    parse_crop_box,
)
from tg_sticker.exceptions import ValidationError


@pytest.fixture(scope="session")
def sample_landscape_mp4(tmp_path_factory):
    """Creates a 1920x1080 30fps MP4 file with audio."""
    tmp_dir = tmp_path_factory.mktemp("media")
    out_file = tmp_dir / "landscape.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=4.0:size=1920x1080:rate=30",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=1000:duration=4.0",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        str(out_file),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_file


@pytest.fixture(scope="session")
def sample_portrait_mp4(tmp_path_factory):
    """Creates a 1080x1920 portrait video."""
    tmp_dir = tmp_path_factory.mktemp("media")
    out_file = tmp_dir / "portrait.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=2.0:size=1080x1920:rate=30",
        "-c:v",
        "libx264",
        "-an",
        str(out_file),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_file


def test_convert_landscape_to_sticker(sample_landscape_mp4, tmp_path):
    converter = TelegramConverter()
    out_webm = tmp_path / "sticker_landscape.webm"

    cfg = ConversionConfig(mode="sticker", duration=2.5)
    res = converter.convert(sample_landscape_mp4, out_webm, config=cfg)

    assert res.valid is True, res.issues
    assert res.info.width == 512
    assert res.info.height == 288
    assert res.info.has_audio is False
    assert res.info.size_bytes <= 256 * 1024
    assert res.info.duration <= 3.05


def test_convert_portrait_to_sticker(sample_portrait_mp4, tmp_path):
    converter = TelegramConverter()
    out_webm = tmp_path / "sticker_portrait.webm"

    cfg = ConversionConfig(mode="sticker")
    res = converter.convert(sample_portrait_mp4, out_webm, config=cfg)

    assert res.valid is True, res.issues
    assert res.info.height == 512
    assert res.info.width == 288
    assert res.info.has_audio is False
    assert res.info.size_bytes <= 256 * 1024


def test_convert_to_emoji(sample_landscape_mp4, tmp_path):
    converter = TelegramConverter()
    out_webm = tmp_path / "emoji.webm"

    cfg = ConversionConfig(mode="emoji", fit_mode="crop")
    res = converter.convert(sample_landscape_mp4, out_webm, config=cfg)

    assert res.valid is True, res.issues
    assert res.info.width == 100
    assert res.info.height == 100
    assert res.info.has_audio is False
    assert res.info.size_bytes <= 256 * 1024


def test_convert_pingpong(sample_landscape_mp4, tmp_path):
    converter = TelegramConverter()
    out_webm = tmp_path / "pingpong.webm"

    cfg = ConversionConfig(mode="sticker", loop_mode="pingpong", duration=2.0)
    res = converter.convert(sample_landscape_mp4, out_webm, config=cfg)

    assert res.valid is True, res.issues
    assert res.info.duration <= 3.05
    assert res.info.width == 512


def test_speed_to_fit(sample_landscape_mp4, tmp_path):
    converter = TelegramConverter()
    out_webm = tmp_path / "speed_fit.webm"

    cfg = ConversionConfig(mode="sticker", speed_to_fit=True)
    res = converter.convert(sample_landscape_mp4, out_webm, config=cfg)

    assert res.valid is True, res.issues
    assert res.info.duration <= 3.05


def test_remove_bg_colorkey(tmp_path):
    """Test background removal (chromakey) produces alpha stream."""
    converter = TelegramConverter()
    green_video = tmp_path / "green_screen.mp4"
    out_webm = tmp_path / "transparent_sticker.webm"

    # Generate synthetic green screen video
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=green:s=512x512:d=1.0:r=30",
        str(green_video),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    cfg = ConversionConfig(mode="sticker", remove_bg="green")
    res = converter.convert(green_video, out_webm, config=cfg)

    assert res.valid is True, res.issues
    assert res.info.has_alpha is True


def test_size_limit_enforcement(tmp_path):
    """Test that a high-detail noisy video is forcibly compressed under 256 KB."""
    converter = TelegramConverter()
    noisy_video = tmp_path / "noisy.mp4"
    out_webm = tmp_path / "noisy_sticker.webm"

    # Generate synthetic video with dense visual noise
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "nullsrc=s=1280x720:d=3.0:r=30,geq=random(1)*255:128:128",
        "-c:v",
        "libx264",
        str(noisy_video),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    cfg = ConversionConfig(
        mode="sticker", duration=3.0, crf=10
    )  # crf=10 would normally explode file size
    res = converter.convert(noisy_video, out_webm, config=cfg)

    assert res.valid is True, res.issues
    assert res.info.size_bytes <= 256 * 1024


@pytest.mark.parametrize(
    "fmt,codec,extra_args",
    [
        ("mkv", "libx264", []),
        ("avi", "mpeg4", []),
        ("webm", "libvpx", []),
        ("gif", "gif", []),
        ("png", "png", ["-frames:v", "1"]),
    ],
)
def test_multiple_input_formats(tmp_path, fmt, codec, extra_args):
    """Test converting various video and animation container formats into Telegram WebM VP9."""
    converter = TelegramConverter()
    in_file = tmp_path / f"input.{fmt}"
    out_webm = tmp_path / f"output_{fmt}.webm"

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=1.0:size=640x360:rate=25",
        "-c:v",
        codec,
        *extra_args,
        str(in_file),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    res = converter.convert(in_file, out_webm, config=ConversionConfig(mode="sticker"))
    assert res.valid is True, f"Failed for format {fmt}: {res.issues}"
    assert res.info.width == 512
    assert res.info.video_codec == "vp9"


def test_convert_sticker_fit_crop(sample_landscape_mp4, tmp_path):
    """Test that --fit crop produces a 512x512 square sticker."""
    converter = TelegramConverter()
    out_webm = tmp_path / "sticker_cropped.webm"

    cfg = ConversionConfig(mode="sticker", fit_mode="crop", duration=2.0)
    res = converter.convert(sample_landscape_mp4, out_webm, config=cfg)

    assert res.valid is True, res.issues
    assert res.info.width == 512
    assert res.info.height == 512
    assert res.info.size_bytes <= 256 * 1024


def test_convert_sticker_fit_pad(sample_landscape_mp4, tmp_path):
    """Test that --fit pad produces a 512x512 square sticker with transparency."""
    converter = TelegramConverter()
    out_webm = tmp_path / "sticker_padded.webm"

    cfg = ConversionConfig(mode="sticker", fit_mode="pad", duration=2.0)
    res = converter.convert(sample_landscape_mp4, out_webm, config=cfg)

    assert res.valid is True, res.issues
    assert res.info.width == 512
    assert res.info.height == 512
    assert res.info.has_alpha is True
    assert res.info.size_bytes <= 256 * 1024


def test_convert_sticker_fit_stretch(sample_landscape_mp4, tmp_path):
    """Test that --fit stretch produces a 512x512 square sticker."""
    converter = TelegramConverter()
    out_webm = tmp_path / "sticker_stretched.webm"

    cfg = ConversionConfig(mode="sticker", fit_mode="stretch", duration=2.0)
    res = converter.convert(sample_landscape_mp4, out_webm, config=cfg)

    assert res.valid is True, res.issues
    assert res.info.width == 512
    assert res.info.height == 512
    assert res.info.size_bytes <= 256 * 1024


def test_convert_start_time_exceeds_duration(sample_landscape_mp4, tmp_path):
    """Test that setting start_time >= duration raises ValidationError."""
    converter = TelegramConverter()
    out_webm = tmp_path / "out_bounds.webm"

    cfg = ConversionConfig(mode="sticker", start_time=10.0)
    with pytest.raises(ValidationError) as exc_info:
        converter.convert(sample_landscape_mp4, out_webm, config=cfg)
    assert "cannot be greater than or equal to video duration" in str(exc_info.value)


def test_convert_start_time_near_end(sample_landscape_mp4, tmp_path):
    """Test that setting start_time too close to duration raises ValidationError."""
    converter = TelegramConverter()
    out_webm = tmp_path / "out_near_end.webm"

    # sample_landscape_mp4 is 4.0s; 3.98s leaves < 0.05s
    cfg = ConversionConfig(mode="sticker", start_time=3.98)
    with pytest.raises(ValidationError) as exc_info:
        converter.convert(sample_landscape_mp4, out_webm, config=cfg)
    assert "too short" in str(exc_info.value)


def test_convert_negative_start_time(sample_landscape_mp4, tmp_path):
    """Test that negative start_time raises ValidationError."""
    converter = TelegramConverter()
    out_webm = tmp_path / "out_negative.webm"

    cfg = ConversionConfig(mode="sticker", start_time=-1.0)
    with pytest.raises(ValidationError) as exc_info:
        converter.convert(sample_landscape_mp4, out_webm, config=cfg)
    assert "cannot be negative" in str(exc_info.value)


def test_parse_crop_box_pixels():
    """Test parsing pixel crop coordinates as string and tuple."""
    assert parse_crop_box("100,50,400,300", 1920, 1080) == (100, 50, 400, 300)
    assert parse_crop_box("100:50:400:300", 1920, 1080) == (100, 50, 400, 300)
    assert parse_crop_box((100, 50, 400, 300), 1920, 1080) == (100, 50, 400, 300)
    # Ensure odd dimensions are made even
    assert parse_crop_box("101,51,401,301", 1920, 1080) == (100, 50, 400, 300)


def test_parse_crop_box_normalized():
    """Test parsing normalized 0.0-1.0 crop coordinates."""
    # 0.1 * 1000 = 100, 0.5 * 1000 = 500
    res = parse_crop_box("0.1,0.2,0.5,0.4", 1000, 800)
    assert res == (100, 160, 500, 320)


def test_parse_crop_box_errors():
    """Test that invalid crop inputs raise ValidationError."""
    with pytest.raises(ValidationError, match="Expected 4 values"):
        parse_crop_box("100,200", 1920, 1080)

    with pytest.raises(ValidationError, match="all 4 values must be numeric"):
        parse_crop_box("abc,200,300,400", 1920, 1080)

    with pytest.raises(ValidationError, match="cannot be negative"):
        parse_crop_box("-10,50,200,200", 1920, 1080)

    with pytest.raises(ValidationError, match="must be positive"):
        parse_crop_box("0,0,0,200", 1920, 1080)

    with pytest.raises(ValidationError, match="outside the video dimensions"):
        parse_crop_box("2000,50,200,200", 1920, 1080)


def test_convert_custom_crop_sticker(sample_landscape_mp4, tmp_path):
    """Test converting with an off-center square custom crop produces a valid 512x512 sticker."""
    converter = TelegramConverter()
    out_webm = tmp_path / "custom_cropped_sticker.webm"

    # Off-center crop near top-right: x=900, y=100, w=600, h=600
    cfg = ConversionConfig(mode="sticker", crop="900,100,600,600", duration=1.0)
    res = converter.convert(sample_landscape_mp4, out_webm, config=cfg)

    assert res.valid is True, res.issues
    assert res.info.width == 512
    assert res.info.height == 512
    assert res.info.size_bytes <= 256 * 1024


def test_convert_custom_crop_rectangular(sample_landscape_mp4, tmp_path):
    """Test converting with a non-square custom crop (2:1 aspect ratio) scales correctly."""
    converter = TelegramConverter()
    out_webm = tmp_path / "custom_cropped_rect.webm"

    # 2:1 rectangle: w=800, h=400 -> should scale to 512x256
    cfg = ConversionConfig(mode="sticker", crop="100,100,800,400", duration=1.0)
    res = converter.convert(sample_landscape_mp4, out_webm, config=cfg)

    assert res.valid is True, res.issues
    assert res.info.width == 512
    assert res.info.height == 256
    assert res.info.size_bytes <= 256 * 1024


def test_convert_custom_crop_emoji(sample_landscape_mp4, tmp_path):
    """Test custom crop in emoji mode produces exactly 100x100."""
    converter = TelegramConverter()
    out_webm = tmp_path / "custom_cropped_emoji.webm"

    cfg = ConversionConfig(mode="emoji", crop="200,200,400,400", duration=1.0)
    res = converter.convert(sample_landscape_mp4, out_webm, config=cfg)

    assert res.valid is True, res.issues
    assert res.info.width == 100
    assert res.info.height == 100
    assert res.info.size_bytes <= 256 * 1024
