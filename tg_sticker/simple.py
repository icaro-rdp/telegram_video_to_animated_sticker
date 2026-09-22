"""One-command simple runner for Telegram sticker conversion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .batch import SUPPORTED_EXTENSIONS, convert_batch_file, find_video_files
from .converter import ConversionConfig, TelegramConverter


def run(
    argv: list[str] | None = None,
    input_dir: str = "input_videos",
    output_dir: str = "output_stickers",
) -> int:
    parser = argparse.ArgumentParser(
        prog="convert",
        description="One-command simple runner for Telegram sticker conversion.",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Optional input video file(s) or directory. If omitted, uses 'input_videos/'.",
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        default=input_dir,
        help=f"Input folder to search when no inputs specified (default: {input_dir})",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=output_dir,
        help=f"Output folder for converted stickers (default: {output_dir})",
    )
    parser.add_argument(
        "--mode",
        choices=["sticker", "emoji"],
        default="sticker",
        help="Target format: sticker (512px) or emoji (100x100)",
    )
    parser.add_argument(
        "--fit",
        choices=["contain", "crop", "pad", "stretch"],
        default=None,
        help="Fit method: contain (preserve aspect ratio, default for sticker), crop (square 1:1, default for emoji), pad, or stretch",
    )
    parser.add_argument(
        "-ss",
        "--start",
        type=float,
        default=None,
        help="Start time offset in seconds",
    )
    parser.add_argument(
        "-t",
        "--duration",
        type=float,
        default=None,
        help="Max duration per clip in seconds (<= 3.0)",
    )
    parser.add_argument(
        "--speed-to-fit",
        action="store_true",
        help="Speed up longer video to fit into 3.0s",
    )
    parser.add_argument(
        "--pingpong",
        "--boomerang",
        action="store_true",
        help="Loop in ping-pong (boomerang) mode",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Target FPS (default 30, max 30)",
    )
    parser.add_argument(
        "--crf",
        type=int,
        default=30,
        help="Base VP9 CRF quality (0-63, default 30)",
    )
    parser.add_argument(
        "--remove-bg",
        default=None,
        help="Color to key out (e.g. green, white, black, or #hex)",
    )

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    in_p, out_p = Path(args.input_dir).resolve(), Path(args.output_dir).resolve()
    in_p.mkdir(parents=True, exist_ok=True)
    out_p.mkdir(parents=True, exist_ok=True)

    files_to_process = []

    if args.inputs:
        for arg in args.inputs:
            p = Path(arg).resolve()
            if p.is_file():
                files_to_process.append(p)
            elif p.is_dir():
                files_to_process.extend(find_video_files(p))
            else:
                print(f"Warning: File or directory not found: {arg}", file=sys.stderr)
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
        print("2. Run 'convert' again.")
        print("=" * 60 + "\n")
        return 0

    print("\n" + "=" * 60)
    print(f"  Converting {len(files_to_process)} video(s) into Telegram stickers...")
    print("=" * 60)

    converter = TelegramConverter()
    config = ConversionConfig(
        mode=args.mode,
        start_time=args.start,
        duration=args.duration,
        speed_to_fit=args.speed_to_fit,
        loop_mode="pingpong" if args.pingpong else "normal",
        fit_mode=args.fit,
        fps=args.fps,
        crf=args.crf,
        remove_bg=args.remove_bg,
    )
    success_count = 0

    for idx, video_path in enumerate(files_to_process, 1):
        dest_file = out_p / f"{video_path.stem}.webm"
        print(
            f"[{idx}/{len(files_to_process)}] Processing: {video_path.name} ...",
            end=" ",
            flush=True,
        )

        res = convert_batch_file(
            converter, video_path, dest_file, config=config, overwrite=True
        )
        if res.validation and res.validation.valid:
            success_count += 1
            info = res.validation.info
            print(f"DONE! ({info.size_kb:.1f} KB, {info.width}x{info.height})")
        elif res.validation:
            print(f"WARNING: {'; '.join(res.validation.issues)}")
        else:
            print(f"FAILED: {res.error}")

    print("=" * 60)
    print(
        f"Finished! {success_count}/{len(files_to_process)} sticker(s) created in: {out_p}"
    )
    print("Ready to upload directly to @Stickers on Telegram!\n")
    return 0


def main():
    sys.exit(run())


if __name__ == "__main__":
    main()
