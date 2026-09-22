"""Command Line Interface for Telegram Video to Animated Sticker / Emoji."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .batch import process_batch, watch_folder
from .converter import ConversionConfig, TelegramConverter
from .exceptions import (
    DependencyError,
    EncodingError,
    MediaNotFoundError,
    TelegramStickerError,
)
from .validator import validate_telegram_webm


def format_size(bytes_val: int) -> str:
    kb = bytes_val / 1024.0
    return f"{kb:.1f} KB"


def cmd_convert(args: argparse.Namespace) -> int:
    input_file = Path(args.input).resolve()
    if not input_file.is_file():
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        return 1

    if args.output:
        output_file = Path(args.output).resolve()
    else:
        output_file = input_file.parent / f"{input_file.stem}_sticker.webm"

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

    print(f"Converting: {input_file.name}")
    print(
        f"  Mode: {config.mode.capitalize()} | Loop: {config.loop_mode} | FPS: {config.fps}"
    )
    if config.speed_to_fit:
        print("  Speed-to-fit: enabled (accelerating video to fit <= 3s)")
    if config.start_time:
        print(f"  Start offset: {config.start_time}s")

    converter = TelegramConverter()
    try:
        res = converter.convert(input_file, output_file, config=config)
    except DependencyError as e:
        print(f"\n[DEPENDENCY ERROR] {e}", file=sys.stderr)
        return 1
    except MediaNotFoundError as e:
        print(f"\n[FILE NOT FOUND] {e}", file=sys.stderr)
        return 1
    except EncodingError as e:
        print(f"\n[ENCODING ERROR] {e}", file=sys.stderr)
        return 1
    except TelegramStickerError as e:
        print(f"\n[ERROR] {e.__class__.__name__}: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n[UNEXPECTED ERROR] {e}", file=sys.stderr)
        return 1

    print(f"\nOutput saved: {output_file}")
    print(f"  Size:       {format_size(res.info.size_bytes)} (Max allowed: 256.0 KB)")
    print(f"  Dimensions: {res.info.width}x{res.info.height}")
    print(f"  Duration:   {res.info.duration:.2f}s (Max allowed: 3.00s)")
    print(f"  Codec:      {res.info.video_codec} (libvpx-vp9)")
    print(f"  FPS:        {res.info.fps:.1f}")
    print(
        f"  Audio:      {'None (Compliant)' if not res.info.has_audio else 'Present (Invalid)'}"
    )

    if res.valid:
        print("\n>>> SUCCESS: Ready for Telegram @Stickers bot! <<<")
        return 0
    else:
        print(
            "\n>>> WARNING: Output failed one or more Telegram requirements: <<<",
            file=sys.stderr,
        )
        for issue in res.issues:
            print(f"  - {issue}", file=sys.stderr)
        return 1


def cmd_batch(args: argparse.Namespace) -> int:
    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)

    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    config = ConversionConfig(
        mode=args.mode,
        duration=args.duration,
        speed_to_fit=args.speed_to_fit,
        loop_mode="pingpong" if args.pingpong else "normal",
        fit_mode=args.fit,
        fps=args.fps,
        crf=args.crf,
        remove_bg=args.remove_bg,
    )

    if args.watch:
        print(f"Watching folder: {in_dir.resolve()}")
        print(f"Output folder:   {out_dir.resolve()}")
        print(
            "Drop videos into the input folder to automatically convert them. Press Ctrl+C to exit.\n"
        )

        def on_convert(res):
            if res.error:
                print(f" [FAILED] {res.input_file.name}: {res.error}")
            elif res.validation and res.validation.valid:
                print(
                    f" [CONVERTED] {res.input_file.name} -> {res.output_file.name} "
                    f"({res.validation.info.size_kb:.1f} KB, {res.validation.info.width}x{res.validation.info.height})"
                )
            else:
                print(
                    f" [INVALID] {res.input_file.name}: {'; '.join(res.validation.issues)}"
                )

        watch_folder(
            input_dir=in_dir,
            output_dir=out_dir,
            config=config,
            on_convert=on_convert,
        )
        return 0

    print(f"Batch converting videos from: {in_dir.resolve()}")
    print(f"Saving stickers to:           {out_dir.resolve()}")

    def progress(p: Path, cur: int, tot: int):
        print(f"[{cur}/{tot}] Processing {p.name}...", end="\r", flush=True)

    summary = process_batch(
        input_dir=in_dir,
        output_dir=out_dir,
        config=config,
        overwrite=args.overwrite,
        recursive=args.recursive,
        progress_callback=progress,
    )

    print("\n" + "=" * 50)
    print("Batch Conversion Summary:")
    print(f"  Total videos found: {summary.total}")
    print(f"  Successfully converted: {summary.succeeded}")
    print(f"  Skipped (already exists): {summary.skipped}")
    print(f"  Failed: {summary.failed}")
    print("=" * 50)

    for r in summary.results:
        if r.error:
            print(f"  x {r.input_file.name}: {r.error}")
        elif r.validation and not r.validation.valid:
            print(f"  ! {r.input_file.name}: {'; '.join(r.validation.issues)}")
        elif not r.skipped and r.validation:
            print(
                f"  ✓ {r.input_file.name} -> {r.output_file.name} "
                f"({r.validation.info.size_kb:.1f} KB, {r.validation.info.width}x{r.validation.info.height})"
            )

    return 0 if summary.failed == 0 else 1


def cmd_check(args: argparse.Namespace) -> int:
    target = Path(args.file).resolve()
    if not target.is_file():
        print(f"Error: File not found: {target}", file=sys.stderr)
        return 1

    res = validate_telegram_webm(target, mode=args.mode)
    print(f"\nChecking Telegram Compliance for: {target.name} (Mode: {args.mode})")
    print("-" * 55)

    info = res.info
    checks = [
        (
            "Container format (.WEBM)",
            "webm" in info.format_name or "matroska" in info.format_name,
            info.format_name,
        ),
        ("Video codec (VP9)", info.video_codec == "vp9", info.video_codec or "unknown"),
        (
            "No audio stream",
            not info.has_audio,
            "No audio" if not info.has_audio else "Audio detected!",
        ),
        ("Duration <= 3.0s", info.duration <= 3.05, f"{info.duration:.2f}s"),
        (
            "Frame rate <= 30 FPS",
            (info.fps or 0) <= 30.05,
            f"{info.fps:.1f} FPS" if info.fps else "N/A",
        ),
        (
            "File size <= 256 KB",
            info.size_bytes <= 256 * 1024,
            f"{info.size_kb:.1f} KB",
        ),
    ]

    if args.mode == "sticker":
        max_d = max(info.width or 0, info.height or 0)
        min_d = min(info.width or 0, info.height or 0)
        checks.append(
            (
                "Sticker dimensions (one side 512px, other <= 512px)",
                max_d == 512 and min_d <= 512,
                f"{info.width}x{info.height}",
            )
        )
    else:
        checks.append(
            (
                "Emoji dimensions (exactly 100x100px)",
                info.width == 100 and info.height == 100,
                f"{info.width}x{info.height}",
            )
        )

    all_passed = True
    for name, passed, val in checks:
        icon = "✓" if passed else "✗"
        status = f"[{icon}] {name:<45} : {val}"
        print(status)
        if not passed:
            all_passed = False

    print("-" * 55)
    if all_passed:
        print("RESULT: PASS - Ready to upload to Telegram @Stickers bot!\n")
        return 0
    else:
        print(
            "RESULT: FAIL - Video does not meet Telegram requirements.\n",
            file=sys.stderr,
        )
        return 1


def cmd_web(args: argparse.Namespace) -> int:
    from .web.server import start_server

    start_server(host=args.host, port=args.port)
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="tg-sticker",
        description="Convert videos into Telegram animated stickers and emoji (.webm VP9)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Convert subcommand
    p_conv = subparsers.add_parser("convert", help="Convert a single video or GIF file")
    p_conv.add_argument("input", help="Path to input video or GIF")
    p_conv.add_argument("-o", "--output", help="Path to output .webm file")
    p_conv.add_argument(
        "--mode",
        choices=["sticker", "emoji"],
        default="sticker",
        help="Sticker (512px) or Emoji (100x100)",
    )
    p_conv.add_argument(
        "-ss", "--start", type=float, default=None, help="Start time offset in seconds"
    )
    p_conv.add_argument(
        "-t",
        "--duration",
        type=float,
        default=None,
        help="Duration in seconds (max 3.0)",
    )
    p_conv.add_argument(
        "--speed-to-fit",
        action="store_true",
        help="Speed up longer video to fit into 3.0s",
    )
    p_conv.add_argument(
        "--fit",
        choices=["contain", "crop", "pad", "stretch"],
        default=None,
        help="Fit method: contain (preserve aspect ratio, default for sticker), crop (square 1:1, default for emoji), pad, or stretch",
    )
    p_conv.add_argument(
        "--fps", type=int, default=30, help="Target FPS (default 30, max 30)"
    )
    p_conv.add_argument(
        "--crf", type=int, default=30, help="Base VP9 CRF quality (0-63, default 30)"
    )
    p_conv.add_argument(
        "--remove-bg",
        default=None,
        help="Color to key out (e.g. green, white, black, or #hex)",
    )

    # Batch subcommand
    p_batch = subparsers.add_parser(
        "batch", help="Batch convert videos from an input folder to an output folder"
    )
    p_batch.add_argument(
        "-i",
        "--input-dir",
        default="input_videos",
        help="Input directory containing videos (default: input_videos)",
    )
    p_batch.add_argument(
        "-o",
        "--output-dir",
        default="output_stickers",
        help="Output directory for stickers (default: output_stickers)",
    )
    p_batch.add_argument(
        "--mode", choices=["sticker", "emoji"], default="sticker", help="Target mode"
    )
    p_batch.add_argument(
        "-t",
        "--duration",
        type=float,
        default=None,
        help="Max duration per clip (max 3.0)",
    )
    p_batch.add_argument(
        "--speed-to-fit",
        action="store_true",
        help="Speed up longer videos to fit into 3.0s",
    )
    p_batch.add_argument(
        "--pingpong", action="store_true", help="Ping-pong boomerang looping"
    )
    p_batch.add_argument(
        "--fit",
        choices=["contain", "crop", "pad", "stretch"],
        default=None,
        help="Fit method: contain (preserve aspect ratio, default for sticker), crop (square 1:1, default for emoji), pad, or stretch",
    )
    p_batch.add_argument("--fps", type=int, default=30, help="Target FPS (max 30)")
    p_batch.add_argument("--crf", type=int, default=30, help="Base VP9 CRF")
    p_batch.add_argument("--remove-bg", default=None, help="Color to remove")
    p_batch.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing output files"
    )
    p_batch.add_argument(
        "-r", "--recursive", action="store_true", help="Recursively process subfolders"
    )
    p_batch.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="Watch input directory and continuously convert newly added videos",
    )

    # Check subcommand
    p_check = subparsers.add_parser(
        "check", help="Verify if a .webm file satisfies Telegram sticker/emoji rules"
    )
    p_check.add_argument("file", help="Path to .webm file to inspect")
    p_check.add_argument(
        "--mode",
        choices=["sticker", "emoji"],
        default="sticker",
        help="Validation mode",
    )

    # Web subcommand
    p_web = subparsers.add_parser("web", help="Launch local browser-based UI")
    p_web.add_argument(
        "--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)"
    )
    p_web.add_argument(
        "-p", "--port", type=int, default=8080, help="Port to listen on (default: 8080)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "convert":
        return cmd_convert(args)
    elif args.command == "batch":
        return cmd_batch(args)
    elif args.command == "check":
        return cmd_check(args)
    elif args.command == "web":
        return cmd_web(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
