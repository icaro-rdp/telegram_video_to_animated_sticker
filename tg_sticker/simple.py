"""One-command simple runner for Telegram sticker conversion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tg_sticker.batch import SUPPORTED_EXTENSIONS, convert_batch_file, find_video_files
from tg_sticker.converter import ConversionConfig, TelegramConverter
from tg_sticker.utils.logger import logger


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
        "--crop",
        default=None,
        help="Custom crop boundaries as 'x,y,w,h' (in pixels or 0.0-1.0 fractions) e.g. '100,50,400,400'",
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
                logger.warn("File or directory not found: %s", arg)
    else:
        files_to_process = find_video_files(in_p)

    if not files_to_process:
        logger.divider(length=60)
        logger.info("  Telegram Sticker Converter - One-Click Mode")
        logger.divider(length=60)
        logger.info("No videos found in: %s", in_p)
        logger.info("How to use:")
        logger.info("1. Drop any video or GIF into the '%s' folder.", in_p.name)
        logger.info(
            "   Supported: %s, etc.",
            ", ".join(sorted(SUPPORTED_EXTENSIONS)[:8]),
        )
        logger.info("2. Run 'convert' again.")
        logger.divider(length=60)
        return 0

    logger.divider(length=60)
    logger.info(
        "  Converting %d video(s) into Telegram stickers...", len(files_to_process)
    )
    logger.divider(length=60)

    converter = TelegramConverter()
    config = ConversionConfig(
        mode=args.mode,
        start_time=args.start,
        duration=args.duration,
        speed_to_fit=args.speed_to_fit,
        loop_mode="pingpong" if args.pingpong else "normal",
        fit_mode=args.fit,
        crop=getattr(args, "crop", None),
        fps=args.fps,
        crf=args.crf,
        remove_bg=args.remove_bg,
    )
    success_count = 0

    for idx, video_path in enumerate(files_to_process, 1):
        dest_file = out_p / f"{video_path.stem}.webm"
        logger.info(
            "[%d/%d] Processing: %s ...",
            idx,
            len(files_to_process),
            video_path.name,
        )

        res = convert_batch_file(
            converter, video_path, dest_file, config=config, overwrite=True
        )
        if res.validation and res.validation.valid:
            success_count += 1
            info = res.validation.info
            logger.info(
                "  -> DONE! (%.1f KB, %dx%d)", info.size_kb, info.width, info.height
            )
        elif res.validation:
            logger.warn("  -> WARNING: %s", "; ".join(res.validation.issues))
        else:
            logger.error("  -> FAILED: %s", res.error)

    logger.divider(length=60)
    logger.info(
        "Finished! %d/%d sticker(s) created in: %s",
        success_count,
        len(files_to_process),
        out_p,
    )
    logger.info("Ready to upload directly to @Stickers on Telegram!")
    return 0


def main():
    sys.exit(run())


if __name__ == "__main__":
    main()
