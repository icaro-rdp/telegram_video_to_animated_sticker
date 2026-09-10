"""Batch folder processing and optional folder watcher for Telegram stickers."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from .converter import ConversionConfig, TelegramConverter
from .validator import ValidationResult

SUPPORTED_EXTENSIONS = {
    # Modern & web formats
    ".mp4", ".mov", ".mkv", ".webm", ".m4v",
    # Animation formats
    ".gif", ".webp", ".apng",
    # Legacy & PC formats
    ".avi", ".wmv", ".asf", ".flv", ".f4v",
    # Mobile formats
    ".3gp", ".3g2",
    # MPEG & Broadcast formats
    ".ts", ".mts", ".m2ts", ".vob", ".mpg", ".mpeg", ".m2v", ".ogv", ".ogg"
}


@dataclass
class BatchFileResult:
    input_file: Path
    output_file: Path
    skipped: bool
    error: Optional[str] = None
    validation: Optional[ValidationResult] = None


@dataclass
class BatchSummary:
    total: int = 0
    succeeded: int = 0
    skipped: int = 0
    failed: int = 0
    results: List[BatchFileResult] = None

    def __post_init__(self):
        if self.results is None:
            self.results = []


def find_video_files(input_dir: str | Path, recursive: bool = False) -> List[Path]:
    """Finds all supported video/animation files in a directory."""
    in_path = Path(input_dir).resolve()
    if not in_path.is_dir():
        raise NotADirectoryError(f"Directory not found: {in_path}")

    files: List[Path] = []
    iterator = in_path.rglob("*") if recursive else in_path.iterdir()

    for item in sorted(iterator):
        if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(item)

    return files


def process_batch(
    input_dir: str | Path = "input_videos",
    output_dir: str | Path = "output_stickers",
    config: Optional[ConversionConfig] = None,
    overwrite: bool = False,
    recursive: bool = False,
    progress_callback: Optional[Callable[[Path, int, int], None]] = None,
) -> BatchSummary:
    """
    Processes all video files in input_dir and saves converted .webm stickers to output_dir.
    Skips already converted files unless overwrite=True.
    """
    in_p = Path(input_dir).resolve()
    out_p = Path(output_dir).resolve()

    in_p.mkdir(parents=True, exist_ok=True)
    out_p.mkdir(parents=True, exist_ok=True)

    cfg = config or ConversionConfig()
    converter = TelegramConverter()

    video_files = find_video_files(in_p, recursive=recursive)
    summary = BatchSummary(total=len(video_files))

    for idx, video_path in enumerate(video_files, 1):
        if progress_callback:
            progress_callback(video_path, idx, len(video_files))

        # Destination filename: replace extension with .webm
        dest_filename = f"{video_path.stem}.webm"
        if recursive:
            # Preserve subdirectory structure
            rel_parent = video_path.parent.relative_to(in_p)
            dest_file = out_p / rel_parent / dest_filename
        else:
            dest_file = out_p / dest_filename

        dest_file.parent.mkdir(parents=True, exist_ok=True)

        if dest_file.exists() and not overwrite:
            summary.skipped += 1
            summary.results.append(
                BatchFileResult(
                    input_file=video_path,
                    output_file=dest_file,
                    skipped=True,
                )
            )
            continue

        try:
            res = converter.convert(video_path, dest_file, config=cfg)
            if res.valid:
                summary.succeeded += 1
            else:
                summary.failed += 1
            summary.results.append(
                BatchFileResult(
                    input_file=video_path,
                    output_file=dest_file,
                    skipped=False,
                    validation=res,
                )
            )
        except Exception as e:
            summary.failed += 1
            summary.results.append(
                BatchFileResult(
                    input_file=video_path,
                    output_file=dest_file,
                    skipped=False,
                    error=str(e),
                )
            )

    return summary


def watch_folder(
    input_dir: str | Path = "input_videos",
    output_dir: str | Path = "output_stickers",
    config: Optional[ConversionConfig] = None,
    poll_interval: float = 2.0,
    on_convert: Optional[Callable[[BatchFileResult], None]] = None,
):
    """
    Continuously monitors input_dir and automatically converts new video files as they are placed.
    """
    in_p = Path(input_dir).resolve()
    out_p = Path(output_dir).resolve()

    in_p.mkdir(parents=True, exist_ok=True)
    out_p.mkdir(parents=True, exist_ok=True)

    cfg = config or ConversionConfig()
    converter = TelegramConverter()
    processed_files = set()

    # Pre-populate already existing output files
    for existing in out_p.glob("*.webm"):
        processed_files.add(existing.stem)

    while True:
        try:
            for item in in_p.iterdir():
                if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
                    if item.stem not in processed_files:
                        dest_file = out_p / f"{item.stem}.webm"
                        try:
                            val = converter.convert(item, dest_file, config=cfg)
                            processed_files.add(item.stem)
                            res = BatchFileResult(
                                input_file=item,
                                output_file=dest_file,
                                skipped=False,
                                validation=val,
                            )
                            if on_convert:
                                on_convert(res)
                        except Exception as ex:
                            res = BatchFileResult(
                                input_file=item,
                                output_file=dest_file,
                                skipped=False,
                                error=str(ex),
                            )
                            if on_convert:
                                on_convert(res)
            time.sleep(poll_interval)
        except KeyboardInterrupt:
            break
