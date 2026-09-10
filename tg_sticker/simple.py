"""One-command simple runner for Telegram sticker conversion."""

from __future__ import annotations

import sys
from pathlib import Path

from .batch import convert_batch_file, find_video_files, SUPPORTED_EXTENSIONS
from .converter import ConversionConfig, TelegramConverter


def run(input_dir: str = "input_videos", output_dir: str = "output_stickers") -> int:
    in_p, out_p = Path(input_dir).resolve(), Path(output_dir).resolve()
    in_p.mkdir(parents=True, exist_ok=True)
    out_p.mkdir(parents=True, exist_ok=True)

    cli_args = sys.argv[1:]
    files_to_process = []

    if cli_args:
        for arg in cli_args:
            p = Path(arg).resolve()
            if p.is_file():
                files_to_process.append(p)
            elif p.is_dir():
                files_to_process.extend(find_video_files(p))
    else:
        files_to_process = find_video_files(in_p)

    if not files_to_process:
        print("\n" + "=" * 60)
        print("  Telegram Sticker Converter - One-Click Mode")
        print("=" * 60)
        print(f"No videos found in: {in_p}")
        print("\nHow to use:")
        print(f"1. Drop any video or GIF into the '{in_p.name}' folder.")
        print(f"   Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS)[:8])}, etc.")
        print("2. Run 'convert_video' again.")
        print("=" * 60 + "\n")
        return 0

    print("\n" + "=" * 60)
    print(f"  Converting {len(files_to_process)} video(s) into Telegram stickers...")
    print("=" * 60)

    converter = TelegramConverter()
    config = ConversionConfig(mode="sticker")
    success_count = 0

    for idx, video_path in enumerate(files_to_process, 1):
        dest_file = out_p / f"{video_path.stem}.webm"
        print(f"[{idx}/{len(files_to_process)}] Processing: {video_path.name} ...", end=" ", flush=True)

        res = convert_batch_file(converter, video_path, dest_file, config=config, overwrite=True)
        if res.validation and res.validation.valid:
            success_count += 1
            info = res.validation.info
            print(f"DONE! ({info.size_kb:.1f} KB, {info.width}x{info.height})")
        elif res.validation:
            print(f"WARNING: {'; '.join(res.validation.issues)}")
        else:
            print(f"FAILED: {res.error}")

    print("=" * 60)
    print(f"Finished! {success_count}/{len(files_to_process)} sticker(s) created in: {out_p}")
    print("Ready to upload directly to @Stickers on Telegram!\n")
    return 0


def main():
    sys.exit(run())


if __name__ == "__main__":
    main()
