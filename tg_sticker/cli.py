"""Command Line Interface for Telegram Video to Animated Sticker / Emoji."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from tg_sticker.batch import process_batch, watch_folder
from tg_sticker.converter import ConversionConfig, TelegramConverter
from tg_sticker.exceptions import (
    DependencyError,
    EncodingError,
    MediaNotFoundError,
    TelegramStickerError,
)
from tg_sticker.utils.logger import logger, set_level
from tg_sticker.validator import validate_telegram_webm


def format_size(bytes_val: int) -> str:
    kb = bytes_val / 1024.0
    return f"{kb:.1f} KB"


def cmd_convert(args: argparse.Namespace) -> int:
    is_json = getattr(args, "json", False)
    if is_json:
        set_level("ERROR")

    input_file = Path(args.input).resolve()
    if not input_file.is_file():
        if is_json:
            sys.stdout.write(
                json.dumps(
                    {
                        "success": False,
                        "valid": False,
                        "issues": [f"Input file not found: {input_file}"],
                        "error": f"Input file not found: {input_file}",
                        "error_type": "MediaNotFoundError",
                    }
                )
                + "\n"
            )
        else:
            logger.error("Input file not found: %s", input_file)
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
        loop_mode="pingpong" if getattr(args, "pingpong", False) else "normal",
        fit_mode=args.fit,
        fps=args.fps,
        crf=args.crf,
        remove_bg=args.remove_bg,
    )

    if not is_json:
        logger.info("Converting: %s", input_file.name)
        logger.info(
            "  Mode: %s | Loop: %s | FPS: %d",
            config.mode.capitalize(),
            config.loop_mode,
            config.fps,
        )
        if config.speed_to_fit:
            logger.info("  Speed-to-fit: enabled (accelerating video to fit <= 3s)")
        if config.start_time:
            logger.info("  Start offset: %ss", config.start_time)

    converter = TelegramConverter()
    try:
        res = converter.convert(input_file, output_file, config=config)
    except DependencyError as e:
        if is_json:
            sys.stdout.write(
                json.dumps(
                    {
                        "success": False,
                        "valid": False,
                        "issues": [str(e)],
                        "error": str(e),
                        "error_type": "DependencyError",
                    }
                )
                + "\n"
            )
        else:
            logger.error("[DEPENDENCY ERROR] %s", e)
        return 1
    except MediaNotFoundError as e:
        if is_json:
            sys.stdout.write(
                json.dumps(
                    {
                        "success": False,
                        "valid": False,
                        "issues": [str(e)],
                        "error": str(e),
                        "error_type": "MediaNotFoundError",
                    }
                )
                + "\n"
            )
        else:
            logger.error("[FILE NOT FOUND] %s", e)
        return 1
    except EncodingError as e:
        if is_json:
            sys.stdout.write(
                json.dumps(
                    {
                        "success": False,
                        "valid": False,
                        "issues": [str(e)],
                        "error": str(e),
                        "error_type": "EncodingError",
                    }
                )
                + "\n"
            )
        else:
            logger.error("[ENCODING ERROR] %s", e)
        return 1
    except TelegramStickerError as e:
        if is_json:
            sys.stdout.write(
                json.dumps(
                    {
                        "success": False,
                        "valid": False,
                        "issues": [str(e)],
                        "error": str(e),
                        "error_type": e.__class__.__name__,
                    }
                )
                + "\n"
            )
        else:
            logger.error("[ERROR] %s: %s", e.__class__.__name__, e)
        return 1
    except Exception as e:
        if is_json:
            sys.stdout.write(
                json.dumps(
                    {
                        "success": False,
                        "valid": False,
                        "issues": [str(e)],
                        "error": str(e),
                        "error_type": "UnexpectedError",
                    }
                )
                + "\n"
            )
        else:
            logger.error("[UNEXPECTED ERROR] %s", e)
        return 1

    if is_json:
        info_dict = (
            {
                "width": res.info.width,
                "height": res.info.height,
                "duration": res.info.duration,
                "fps": res.info.fps,
                "size_bytes": res.info.size_bytes,
                "size_kb": res.info.size_kb,
                "codec": res.info.video_codec,
                "has_audio": res.info.has_audio,
                "has_alpha": res.info.has_alpha,
            }
            if res.info
            else None
        )
        payload = {
            "success": True,
            "valid": res.valid,
            "issues": res.issues,
            "output_file": str(output_file),
            "filename": output_file.name,
            "info": info_dict,
        }
        sys.stdout.write(json.dumps(payload) + "\n")
        return 0

    logger.info("Output saved: %s", output_file)
    logger.info(
        "  Size:       %s (Max allowed: 256.0 KB)", format_size(res.info.size_bytes)
    )
    logger.info("  Dimensions: %dx%d", res.info.width, res.info.height)
    logger.info("  Duration:   %.2fs (Max allowed: 3.00s)", res.info.duration)
    logger.info("  Codec:      %s (libvpx-vp9)", res.info.video_codec)
    logger.info("  FPS:        %.1f", res.info.fps)
    logger.info(
        "  Audio:      %s",
        "None (Compliant)" if not res.info.has_audio else "Present (Invalid)",
    )

    if res.valid:
        logger.info(">>> SUCCESS: Ready for Telegram @Stickers bot! <<<")
        return 0
    else:
        logger.warn(">>> WARNING: Output failed one or more Telegram requirements: <<<")
        for issue in res.issues:
            logger.warn("  - %s", issue)
        return 1


def cmd_batch(args: argparse.Namespace) -> int:
    is_json = getattr(args, "json", False)
    if is_json:
        set_level("ERROR")

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
        logger.info("Watching folder: %s", in_dir.resolve())
        logger.info("Output folder:   %s", out_dir.resolve())
        logger.info(
            "Drop videos into the input folder to automatically convert them. Press Ctrl+C to exit."
        )

        def on_convert(res):
            if res.error:
                logger.error(" [FAILED] %s: %s", res.input_file.name, res.error)
            elif res.validation and res.validation.valid:
                logger.info(
                    " [CONVERTED] %s -> %s (%s, %dx%d)",
                    res.input_file.name,
                    res.output_file.name,
                    format_size(res.validation.info.size_bytes),
                    res.validation.info.width,
                    res.validation.info.height,
                )
            else:
                logger.warn(
                    " [INVALID] %s: %s",
                    res.input_file.name,
                    "; ".join(res.validation.issues) if res.validation else "Unknown",
                )

        watch_folder(
            input_dir=in_dir,
            output_dir=out_dir,
            config=config,
            on_convert=on_convert,
        )
        return 0

    if not is_json:
        logger.info("Batch converting videos from: %s", in_dir.resolve())
        logger.info("Saving stickers to:           %s", out_dir.resolve())

    def progress(p: Path, cur: int, tot: int):
        if not is_json:
            logger.info("[%d/%d] Processing %s...", cur, tot, p.name)

    summary = process_batch(
        input_dir=in_dir,
        output_dir=out_dir,
        config=config,
        overwrite=args.overwrite,
        recursive=args.recursive,
        progress_callback=progress,
    )

    if is_json:
        payload = {
            "success": summary.failed == 0,
            "total": summary.total,
            "succeeded": summary.succeeded,
            "skipped": summary.skipped,
            "failed": summary.failed,
        }
        sys.stdout.write(json.dumps(payload) + "\n")
        return 0 if summary.failed == 0 else 1

    logger.divider(length=50)
    logger.info("Batch Conversion Summary:")
    logger.info("  Total videos found: %d", summary.total)
    logger.info("  Successfully converted: %d", summary.succeeded)
    logger.info("  Skipped (already exists): %d", summary.skipped)
    logger.info("  Failed: %d", summary.failed)
    logger.divider(length=50)

    for r in summary.results:
        if r.error:
            logger.error("  x %s: %s", r.input_file.name, r.error)
        elif r.validation and not r.validation.valid:
            logger.warn("  ! %s: %s", r.input_file.name, "; ".join(r.validation.issues))
        elif not r.skipped and r.validation:
            logger.info(
                "  ✓ %s -> %s (%s, %dx%d)",
                r.input_file.name,
                r.output_file.name,
                format_size(r.validation.info.size_bytes),
                r.validation.info.width,
                r.validation.info.height,
            )

    return 0 if summary.failed == 0 else 1


def cmd_check(args: argparse.Namespace) -> int:
    is_json = getattr(args, "json", False)
    if is_json:
        set_level("ERROR")

    target = Path(args.file).resolve()
    if not target.is_file():
        if is_json:
            sys.stdout.write(
                json.dumps({"valid": False, "issues": [f"File not found: {target}"]})
                + "\n"
            )
        else:
            logger.error("Error: File not found: %s", target)
        return 1

    res = validate_telegram_webm(target, mode=args.mode)
    if not is_json:
        logger.info(
            "Checking Telegram Compliance for: %s (Mode: %s)", target.name, args.mode
        )
        logger.divider(length=55)

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
        if not passed:
            all_passed = False
        if not is_json:
            icon = "✓" if passed else "✗"
            status = f"[{icon}] {name:<45} : {val}"
            if passed:
                logger.info("%s", status)
            else:
                logger.error("%s", status)

    if is_json:
        checks_dict = {
            name: {"passed": passed, "value": str(val)} for name, passed, val in checks
        }
        payload = {
            "valid": all_passed,
            "issues": res.issues,
            "checks": checks_dict,
            "info": {
                "format_name": info.format_name,
                "video_codec": info.video_codec,
                "has_audio": info.has_audio,
                "duration": info.duration,
                "fps": info.fps,
                "size_bytes": info.size_bytes,
                "size_kb": info.size_kb,
                "width": info.width,
                "height": info.height,
            },
        }
        sys.stdout.write(json.dumps(payload) + "\n")
        return 0 if all_passed else 1

    logger.divider(length=55)
    if all_passed:
        logger.info("RESULT: PASS - Ready to upload to Telegram @Stickers bot!")
        return 0
    else:
        logger.error("RESULT: FAIL - Video does not meet Telegram requirements.")
        return 1


def cmd_server(args: argparse.Namespace) -> int:
    """Start the Next.js Telegram Sticker Studio frontend.

    Args:
        args: Command line parsed arguments.

    Returns:
        Process exit code (0 on success).
    """
    repo_root = Path(__file__).resolve().parent.parent
    frontend_dir = repo_root / "frontend"
    if not (frontend_dir / "package.json").is_file():
        logger.error("Frontend directory not found at: %s", frontend_dir)
        return 1

    npm_bin = shutil.which("npm")
    if not npm_bin:
        logger.error("Node.js and npm are required to run the Next.js web studio.")
        logger.info(
            "To convert stickers directly from your terminal without Node.js, use the CLI:"
        )
        logger.info("  tg-sticker convert <input_video>")
        return 1

    port = getattr(args, "port", 3000)
    logger.divider(length=55)
    logger.info("  Telegram Sticker Studio (Next.js)")
    logger.info("  Starting on: http://localhost:%d", port)
    logger.divider(length=55)
    logger.info("Press Ctrl+C to stop the studio.")

    try:
        subprocess.run(
            [npm_bin, "run", "dev", "--", "-p", str(port)],
            cwd=str(frontend_dir),
            check=True,
        )
    except KeyboardInterrupt:
        logger.info("Server stopped.")
    except subprocess.CalledProcessError as e:
        logger.error("Next.js server exited with error code %d", e.returncode)
        return e.returncode
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
        "--pingpong",
        action="store_true",
        help="Ping-pong boomerang looping",
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
    p_conv.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
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
    p_batch.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
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
    p_check.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )

    # Server subcommand (with 'web' alias)
    p_server = subparsers.add_parser(
        "server",
        aliases=["web"],
        help="Start the Next.js Telegram Sticker Studio frontend (http://localhost:3000)",
    )
    p_server.add_argument(
        "-p", "--port", type=int, default=3000, help="Port to listen on (default: 3000)"
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
    elif args.command in ("server", "web"):
        return cmd_server(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
