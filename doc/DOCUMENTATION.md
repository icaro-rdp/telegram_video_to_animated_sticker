# Documentation: Telegram Animated Sticker & Emoji Converter

This document provides a comprehensive technical reference for the Telegram Sticker Converter, including CLI commands, flags, Python API, specifications, and upload instructions.

---

## Table of Contents

- [Telegram Specifications](#telegram-specifications)
- [Supported Input Formats](#supported-input-formats)
- [Cross-Platform Setup (Windows, Linux, macOS)](#cross-platform-setup-windows-linux-macos)
- [CLI Reference](#cli-reference)
  - [convert_video (One-Click)](#convert_video-one-click)
  - [tg-sticker convert](#tg-sticker-convert)
  - [tg-sticker batch](#tg-sticker-batch)
  - [tg-sticker check](#tg-sticker-check)
  - [tg-sticker web](#tg-sticker-web)
- [Python API Reference](#python-api-reference)
  - [TelegramConverter](#telegramconverter)
  - [ConversionConfig](#conversionconfig)
  - [Validation and Probing](#validation-and-probing)
  - [Exception Hierarchy](#exception-hierarchy)
- [Telegram Bot Upload Guide](#telegram-bot-upload-guide)
- [Testing](#testing)

---

## Telegram Specifications

All output files strictly comply with Telegram's official [Encoding .WEBM with VP9 Guide](https://core.telegram.org/stickers/webm-vp9-encoding).

| Requirement | Stickers | Custom Emoji |
| :--- | :--- | :--- |
| **Container & Codec** | `.webm` encoded with VP9 (`libvpx-vp9`) | `.webm` encoded with VP9 (`libvpx-vp9`) |
| **Dimensions** | Exactly 512px on longer edge, <= 512px on shorter edge | Exactly 100x100px |
| **Max Duration** | 3.0 seconds | 3.0 seconds |
| **Max Framerate** | 30 FPS | 30 FPS |
| **Max File Size** | <= 256 KB (262,144 bytes) | <= 256 KB (262,144 bytes) |
| **Audio Stream** | None (`-an`) | None (`-an`) |
| **Chroma / Pixel Format** | `yuv420p` or `yuva420p` (with alpha) | `yuv420p` or `yuva420p` (with alpha) |

---

## Supported Input Formats

The tool handles any multimedia format supported by FFmpeg, including:

- **Video Files**: `.mp4`, `.mov`, `.mkv`, `.webm`, `.m4v`, `.avi`, `.wmv`, `.flv`, `.3gp`, `.ts`, `.mts`, `.vob`, `.mpg`, `.mpeg`.
- **Animated Formats**: `.gif` (palette and transparency handling), `.webp` (animated WebP), `.apng`.
- **Static Images**: `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff` (automatically converted into a 3-second animated WebM loop with alpha support).
- **Smartphone & Professional Formats**:
  - iPhone 10-bit HDR HEVC.
  - Apple ProRes 4444 (with full 8-bit/16-bit alpha channel preservation).
  - Rotation metadata (Display Matrix rotation tags applied automatically via `-autorotate`).

---

## Cross-Platform Setup (Windows, Linux, macOS)

The codebase is engineered to run seamlessly across Windows, Linux, and macOS without code changes.

### FFmpeg Installation

- **Windows**:
  - Using Windows Package Manager: `winget install Gyan.FFmpeg`
  - Using Chocolatey: `choco install ffmpeg`
  - Using Scoop: `scoop install ffmpeg`
  - Or download official builds from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add the `bin` folder to your system `PATH`.
- **macOS**:
  - Using Homebrew: `brew install ffmpeg`
- **Linux**:
  - Ubuntu / Debian: `sudo apt update && sudo apt install -y ffmpeg`
  - Fedora / RHEL: `sudo dnf install ffmpeg`
  - Arch Linux: `sudo pacman -S ffmpeg`

### Virtual Environment Activation

When using `uv`:

```bash
uv sync

# Linux / macOS:
source .venv/bin/activate

# Windows (Command Prompt):
.venv\Scripts\activate

# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
```

When using `pip`:

```bash
pip install -e .
```

---

## CLI Reference

### convert_video (One-Click)

The simplest way to convert videos. Processes all files in `input_videos/` and writes `.webm` files to `output_stickers/`.

Available commands (cross-platform):

```bash
convert
# or
convert_video
# or
python convert_video.py
```

Or pass specific files or directories directly:

```bash
convert path/to/video.mp4
convert path/to/my_folder
```

### tg-sticker convert

Converts a single video, GIF, or image file.

```bash
tg-sticker convert <input_file> [options]
```

#### Options:

- `-o, --output <path>`: Destination path for the `.webm` file. If omitted, saves in the same directory as `<input_stem>_sticker.webm`.
- `--mode {sticker,emoji}`: Target format.
  - `sticker` (default): 512px on the longer dimension, <= 512px on the other.
  - `emoji`: Exactly 100x100px.
- `-ss, --start <seconds>`: Start time offset in seconds.
- `-t, --duration <seconds>`: Duration in seconds (maximum 3.0).
- `--speed-to-fit`: Accelerates the entire video so that it fits within 3.0 seconds.
- `--pingpong`: Applies a boomerang / forward-reverse bounce loop.
- `--fit {crop,pad,stretch}`: Resizing strategy for emoji mode (default: `crop`).
  - `crop`: Centers and crops to a 1:1 square.
  - `pad`: Preserves aspect ratio with transparent borders.
  - `stretch`: Non-uniform scaling to 100x100.
- `--fps <int>`: Target framerate (default: 30, maximum: 30).
- `--crf <int>`: Base VP9 CRF quality level (0 to 63, default: 30).
- `--remove-bg <color>`: Removes solid background color using chroma-keying (`green`, `black`, `white`, or hex value `#RRGGBB`).

#### Examples:

```bash
# Basic conversion to sticker
tg-sticker convert video.mp4 -o sticker.webm

# Convert to 100x100 custom emoji
tg-sticker convert avatar.mp4 -o emoji.webm --mode emoji

# Trim snippet from 1.5s with a 2.0s duration
tg-sticker convert clip.mov -ss 1.5 -t 2.0

# Speed up an 8-second video to fit Telegram's 3.0s limit
tg-sticker convert long_clip.mp4 --speed-to-fit

# Create a pingpong (boomerang) loop
tg-sticker convert dance.mp4 --pingpong

# Remove green screen background
tg-sticker convert overlay.mp4 --remove-bg green
```

---

### tg-sticker batch

Processes multiple videos in a folder.

```bash
tg-sticker batch [options]
```

#### Options:

- `-i, --input-dir <path>`: Source folder containing videos (default: `input_videos`).
- `-o, --output-dir <path>`: Destination folder for stickers (default: `output_stickers`).
- `--mode {sticker,emoji}`: Target format (`sticker` or `emoji`).
- `-t, --duration <seconds>`: Max clip duration (default: 3.0s).
- `--speed-to-fit`: Speed up longer videos to fit within 3.0s.
- `--pingpong`: Enable ping-pong looping for all files.
- `--overwrite`: Overwrite existing output files in the destination directory.
- `-r, --recursive`: Recursively traverse subfolders.
- `-w, --watch`: Run in folder watcher mode. Monitors `input_videos` and converts new files in real time.

#### Examples:

```bash
# Batch convert with default directories
tg-sticker batch

# Batch convert with speed-to-fit and overwrite
tg-sticker batch -i ./raw_videos -o ./stickers --speed-to-fit --overwrite

# Live folder watcher
tg-sticker batch --watch
```

---

### tg-sticker check

Inspects an existing `.webm` file against all Telegram `@Stickers` bot rules.

```bash
tg-sticker check <file.webm> [--mode {sticker,emoji}]
```

#### Validation Output Example:

```text
Checking Telegram Compliance for: sticker.webm (Mode: sticker)
-------------------------------------------------------
[PASS] Container format (.WEBM)                      : matroska,webm
[PASS] Video codec (VP9)                             : vp9
[PASS] No audio stream                               : No audio
[PASS] Duration <= 3.0s                              : 2.50s
[PASS] Frame rate <= 30 FPS                          : 30.0 FPS
[PASS] File size <= 256 KB                           : 114.8 KB
[PASS] Sticker dimensions (one side 512px, other <= 512px) : 512x288
-------------------------------------------------------
RESULT: PASS - Ready to upload to Telegram @Stickers bot!
```

---

### tg-sticker web

Starts a local HTTP server providing a graphical browser interface.

```bash
tg-sticker web [--host 127.0.0.1] [-p 8080]
```

#### Web Features:
- Drag-and-drop file upload.
- Video preview with interactive start time and duration inputs.
- Live sticker loop playback against a transparency checkerboard.
- Automated compliance checklist.
- Direct download button for generated `.webm` files.
- Folder Batch tab for managing `input_videos/` and `output_stickers/`.

#### REST API Endpoints:
- `GET /api/status`: Health check.
- `GET /api/folders`: List input and output directory contents.
- `GET /output/<filename>`: Download converted `.webm` file.
- `POST /api/convert`: Multipart form-data conversion endpoint.
- `POST /api/batch`: JSON endpoint to trigger batch processing.

---

## Python API Reference

The library can be imported directly into Python applications.

### TelegramConverter

Main conversion engine. Handles timing calculations, FFmpeg command generation, and adaptive multi-pass compression to enforce the <= 256 KB limit.

```python
from pathlib import Path
from tg_sticker.converter import TelegramConverter, ConversionConfig

converter = TelegramConverter()
config = ConversionConfig(
    mode="sticker",
    duration=2.5,
    speed_to_fit=False,
    loop_mode="normal",
    crf=30,
)

result = converter.convert(
    input_path=Path("input.mp4"),
    output_path=Path("sticker.webm"),
    config=config,
)

print(f"Valid: {result.valid}")
print(f"Size: {result.info.size_kb} KB")
print(f"Dimensions: {result.info.width}x{result.info.height}")
```

### ConversionConfig

Configuration parameters for conversion:

| Attribute | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `mode` | `str` | `"sticker"` | `"sticker"` (512px edge) or `"emoji"` (100x100) |
| `start_time` | `float | None` | `None` | Start offset in seconds |
| `duration` | `float | None` | `None` | Clip duration (<= 3.0s) |
| `speed_to_fit` | `bool` | `False` | Accelerate video to fit in <= 3.0s |
| `loop_mode` | `str` | `"normal"` | `"normal"` or `"pingpong"` |
| `fit_mode` | `str` | `"crop"` | Emoji fitting: `"crop"`, `"pad"`, `"stretch"` |
| `fps` | `int` | `30` | Target framerate (max 30) |
| `crf` | `int` | `30` | VP9 CRF quality level (0-63) |
| `remove_bg` | `str | None` | `None` | Color to key out (`"green"`, `"black"`, etc.) |
| `max_duration`| `float` | `3.0` | Maximum duration limit |
| `preserve_alpha` | `bool` | `True` | Preserve transparent channels |

### Validation and Probing

```python
from tg_sticker.validator import probe_media, validate_telegram_webm

# Probe any input file
info = probe_media("input.mp4")
print(info.duration, info.width, info.height, info.has_audio)

# Validate output compliance
validation = validate_telegram_webm("output.webm", mode="sticker")
if not validation.valid:
    print("Issues found:", validation.issues)
```

### Exception Hierarchy

All exceptions inherit from `TelegramStickerError`:

```text
TelegramStickerError
├── DependencyError
│   ├── FFmpegNotFoundError
│   └── FFprobeNotFoundError
├── MediaError
│   ├── MediaNotFoundError
│   ├── DirectoryNotFoundError
│   └── CorruptMediaError
├── FFmpegExecutionError
│   ├── EncodingError
│   └── ProbeError
└── ValidationError
    └── SizeConstraintExceededError
```

---

## Telegram Bot Upload Guide

Upload animated stickers to Telegram through the official [@Stickers](https://t.me/Stickers) bot by sending the file as an uncompressed document. The specific command depends on whether your animation is a vector file (`.TGS`) or a video file (`.WEBM`).

### Format Distinction:
- **Vector animated stickers**: Use `.TGS` files with command `/newanimated`.
- **Video animated stickers and emoji**: Use `.WEBM` files with command `/newvideo` (for stickers) or `/newemojivideo` (for custom emoji).

### Step-by-Step Upload Instructions:

1. Open Telegram and search for [@Stickers](https://t.me/Stickers).
2. Start the bot and send `/newvideo` (for stickers) or `/newemojivideo` (for custom emoji).
3. Enter a title for your sticker pack.
4. Send your generated `.webm` file as an **uncompressed Document/File**:
   - On Desktop: Drag and drop the file, ensuring "Send as file" is selected.
   - On Mobile: Tap attachment, choose "File" (do not send from Gallery/Photos, which recompresses media).
5. Send the emoji associated with the sticker.
6. Repeat for all stickers in the pack.
7. Send `/publish`, optionally provide an icon (100x100 WEBM or 512x512 PNG), and choose a unique URL slug for your pack.

### Troubleshooting Rejections:

If the bot returns an error upon uploading:
- Run `tg-sticker check <file>.webm` to verify all parameters.
- Verify the file size is under 256.0 KB.
- Verify duration does not exceed 3.0 seconds.
- Verify one dimension is exactly 512px (for stickers) or 100x100px (for emoji).
- Verify the file was uploaded as a file/document, not as a video message or inline video.

---

## Testing

Run the automated test suite using `uv`:

```bash
uv run pytest -v
```

The test suite validates:
- Video duration, framerate, and dimension enforcement.
- Removal of audio tracks.
- Multi-pass size constraint optimization (<= 256 KB).
- Pingpong looping and speed-to-fit filters.
- Alpha channel preservation and chroma-keying.
- Diverse container support (MP4, MOV, MKV, AVI, WebM, GIF, PNG).
- Custom exception handling.
