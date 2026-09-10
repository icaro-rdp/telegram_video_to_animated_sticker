# Telegram Animated Sticker & Emoji Studio ⚡

Transform any video, GIF, or animation into official Telegram-compliant animated `.webm` stickers and custom emoji.

Built in strict compliance with Telegram's official [Encoding .WEBM with VP9 Guide](https://core.telegram.org/stickers/webm-vp9-encoding).

---

## 📋 Telegram Specifications Enforced

| Requirement | Stickers | Custom Emoji |
| :--- | :--- | :--- |
| **Container & Codec** | `.webm` encoded with **VP9** (`libvpx-vp9`) | `.webm` encoded with **VP9** (`libvpx-vp9`) |
| **Dimensions** | Exactly **512px** on the longer edge, **&le; 512px** on the shorter edge | Exactly **100x100px** |
| **Max Duration** | **3.0 seconds** | **3.0 seconds** |
| **Max Framerate** | **30 FPS** | **30 FPS** |
| **Max File Size** | **&le; 256 KB** (262,144 bytes) | **&le; 256 KB** (262,144 bytes) |
| **Audio Stream** | **No audio stream** (`-an`) | **No audio stream** (`-an`) |
| **Looping** | Seamless loop or Boomerang | Seamless loop or Boomerang |
| **Alpha Transparency** | Supported (`yuva420p`) | Supported (`yuva420p`) |

---

## 🎬 Supported Input Formats

The tool accepts virtually any multimedia format, including:

- **Modern & Web Video**: `.mp4`, `.mov`, `.mkv`, `.webm`, `.m4v`
- **Animations**: `.gif` (palette & transparency), `.webp` (animated WebP), `.apng`
- **Static Images / Graphics**: `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff` (automatically converted to 3-second animated loops with alpha)
- **Apple / Smartphone Media**: iPhone ProRes 4444 (with alpha channel), HDR 10-bit HEVC, and auto-rotation metadata (vertical/horizontal orientation)
- **Legacy & PC Formats**: `.avi`, `.wmv`, `.asf`, `.flv`, `.f4v`
- **Mobile & Camcorder**: `.3gp`, `.3g2`, `.ts`, `.mts`, `.m2ts`, `.vob`, `.mpg`, `.mpeg`

---

## 🚀 Installation & Sync (using `uv`)

This project uses [`uv`](https://github.com/astral-sh/uv) for lightning-fast dependency management with deterministic reproducibility via `uv.lock`.

### 1. Prerequisites
- **Python 3.9+**
- **FFmpeg** (compiled with `libvpx-vp9`):
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt update && sudo apt install -y ffmpeg`
  - Arch: `sudo pacman -S ffmpeg`

### 2. Environment Setup & Synchronization
Clone the repository, then simply sync the environment with `uv`:

```bash
# Sync dependencies and lockfile into .venv:
uv sync

# Activate virtual environment:
source .venv/bin/activate
```

> **Note**: `uv sync` automatically locks dependencies into `uv.lock` and ensures all packages are identically synchronized.

---

## 📖 Usage Guide

### 1. Batch Folder Processing (Easiest Way) 📂

The project comes with two dedicated directories:
- `input_videos/` - Place any number of input videos/GIFs here.
- `output_stickers/` - Converted `.webm` stickers will be saved here.

```bash
# Convert all files from input_videos/ into output_stickers/:
tg-sticker batch

# Or run with custom folders:
tg-sticker batch -i /path/to/my_videos -o /path/to/my_stickers
```

#### Real-time Folder Watcher 👁️
Start a live watcher that monitors `input_videos/` and automatically converts new videos the moment you drop them in:

```bash
tg-sticker batch --watch
```

---

### 2. Single Video / GIF Conversion 🎥

#### Standard Sticker (512px max side)
```bash
tg-sticker convert input_videos/clip.mp4 -o output_stickers/sticker.webm
```

#### Custom Emoji (100x100)
```bash
tg-sticker convert input_videos/clip.mp4 -o output_stickers/emoji.webm --mode emoji
```

#### Boomerang / Ping-Pong Looping
Creates a forward-and-backward bounce effect so the sticker loops seamlessly without jarring cuts:
```bash
tg-sticker convert input_videos/clip.mp4 --pingpong
```

#### Speed-to-Fit
If your source video is longer than 3 seconds (e.g. 6 seconds), accelerate it smoothly so the entire animation fits in 3.0s:
```bash
tg-sticker convert long_video.mp4 --speed-to-fit
```

#### Precision Trimming
Extract a specific snippet using start offset and duration:
```bash
# Start at 2.5 seconds, clip 2.0 seconds:
tg-sticker convert input.mov -ss 2.5 -t 2.0
```

#### Remove Solid Background (Chroma Key)
Make solid backgrounds transparent:
```bash
# Key out green screen:
tg-sticker convert clip.mp4 --remove-bg green

# Key out black or white:
tg-sticker convert clip.mp4 --remove-bg black
```

---

### 3. Telegram Compliance Inspector 🔍

Verify that an existing `.webm` file satisfies Telegram's `@Stickers` bot rules:

```bash
tg-sticker check output_stickers/sticker.webm --mode sticker
```

Example report:
```text
Checking Telegram Compliance for: sticker.webm (Mode: sticker)
-------------------------------------------------------
[✓] Container format (.WEBM)                      : matroska,webm
[✓] Video codec (VP9)                             : vp9
[✓] No audio stream                               : No audio
[✓] Duration <= 3.0s                              : 2.50s
[✓] Frame rate <= 30 FPS                          : 30.0 FPS
[✓] File size <= 256 KB                           : 114.8 KB
[✓] Sticker dimensions (one side 512px, other <= 512px) : 512x288
-------------------------------------------------------
RESULT: PASS - Ready to upload to Telegram @Stickers bot!
```

---

### 4. Interactive Web Studio 🌐

Launch the built-in browser interface:

```bash
tg-sticker web
```

Then visit **`http://127.0.0.1:8080`** in your browser:
- **Drag & Drop** any video, GIF, or image.
- **Interactive Player** with start/end trim sliders.
- **Live Sticker Loop Stage** with transparency checkerboard background.
- **Side-by-Side Comparison** and compliance checklist.
- **Batch Folder Manager** tab to trigger batch conversions and view folders.
- **One-Click Download**.

---

## ⚙️ Command-Line Reference

```text
usage: tg-sticker [-h] {convert,batch,check,web} ...

Convert videos into Telegram animated stickers and emoji (.webm VP9)

positional arguments:
  convert               Convert a single video or GIF file
    input               Input video/animation path
    -o, --output        Output .webm path
    --mode              Target mode: 'sticker' (512px) or 'emoji' (100x100)
    -ss, --start        Start time offset in seconds
    -t, --duration      Max duration in seconds (max 3.0)
    --speed-to-fit      Accelerate longer video to fit inside 3s
    --pingpong          Boomerang forward/backward loop
    --fit               Fit method for emoji: 'crop', 'pad', or 'stretch'
    --fps               Target FPS (default 30, max 30)
    --crf               Base VP9 CRF quality (0-63, default 30)
    --remove-bg         Key out color (green, white, black, or #hex)

  batch                 Batch convert videos from an input folder
    -i, --input-dir     Input directory (default: input_videos)
    -o, --output-dir    Output directory (default: output_stickers)
    --mode              Target mode ('sticker' or 'emoji')
    --speed-to-fit      Accelerate longer videos
    --pingpong          Boomerang forward/backward loop
    --overwrite         Overwrite existing files
    -w, --watch         Continuously monitor folder for new videos

  check                 Verify if a .webm file satisfies Telegram rules
    file                Path to .webm file to inspect
    --mode              'sticker' or 'emoji'

  web                   Launch local browser-based UI
    --host              Host interface (default: 127.0.0.1)
    -p, --port          Port to listen on (default: 8080)
```

---

## 🤖 Uploading to Telegram

Upload animated stickers to Telegram through the official [@Stickers](https://t.me/Stickers) bot by sending the file as an uncompressed document. The specific command depends on whether your animation is a vector file (`.TGS`) or a video file (`.WEBM`).

> [!NOTE]
> **Format Distinction & Troubleshooting**:
> - **Vector animated stickers**: Use `.TGS` with command `/newanimated`.
> - **Video animated stickers & emoji**: Use `.WEBM` with command `/newvideo` (or `/newemojivideo`).
>
> *Is your animated sticker in `.TGS` or `.WEBM` format, and did the bot return any specific dimension or file-size errors when sending the file?*  
> If the bot rejects a file, run `tg-sticker check <file>.webm` to verify all parameters before uploading.

### Step-by-Step Instructions:
1. Open Telegram and start a chat with [@Stickers](https://t.me/Stickers).
2. Type `/newvideo` (for video stickers) or `/newemojivideo` (for custom emoji).
3. Follow the bot prompts:
   - Provide a title for your pack.
   - Send the generated `.webm` file as an **uncompressed Document / File** (do **not** send as a photo/gallery video, as Telegram will compress it).
   - Send the corresponding emoji (e.g. 😊 or 🔥).
   - Repeat for any additional stickers.
4. Type `/publish`, set a short URL name for your pack, and start sharing!

---

## 🧪 Testing

Run the automated test suite with `uv`:

```bash
uv run pytest -v
```
All 20 test cases verify dimensions, codecs, file size limits (&le; 256 KB), durations, audio stripping, and multi-format compatibility.
