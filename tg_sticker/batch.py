"""Batch folder processing and optional folder watcher for Telegram stickers."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Set

from .converter import ConversionConfig, TelegramConverter
from .exceptions import DirectoryNotFoundError, TelegramStickerError
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
    results: List[BatchFileResult] = field(default_factory=list)


def find_video_files(input_dir: str | Path, recursive: bool = False) -> List[Path]:
    """Finds all supported video/animation files in a directory."""
    in_path = Path(input_dir).resolve()
    if not in_path.is_dir():
        raise DirectoryNotFoundError(f"Directory not found: {in_path}")

    iterator = in_path.rglob("*") if recursive else in_path.iterdir()
    return [p for p in sorted(iterator) if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]


def convert_batch_file(
    converter: TelegramConverter,
    input_file: Path,
    output_file: Path,
    config: ConversionConfig,
    overwrite: bool = False,
) -> BatchFileResult:
    """Encapsulates the single-file conversion lifecycle for batch and watcher workflows."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if output_file.exists() and not overwrite:
        return BatchFileResult(input_file=input_file, output_file=output_file, skipped=True)

    try:
        res = converter.convert(input_file, output_file, config=config)
        return BatchFileResult(input_file=input_file, output_file=output_file, skipped=False, validation=res)
    except TelegramStickerError as e:
        return BatchFileResult(input_file=input_file, output_file=output_file, skipped=False, error=f"[{e.__class__.__name__}] {e}")
    except Exception as e:
        return BatchFileResult(input_file=input_file, output_file=output_file, skipped=False, error=f"Unexpected error: {e}")


def process_batch(
    input_dir: str | Path = "input_videos",
    output_dir: str | Path = "output_stickers",
    config: Optional[ConversionConfig] = None,
    overwrite: bool = False,
    recursive: bool = False,
    progress_callback: Optional[Callable[[Path, int, int], None]] = None,
) -> BatchSummary:
    """Processes all video files in input_dir and saves converted stickers to output_dir."""
    in_p, out_p = Path(input_dir).resolve(), Path(output_dir).resolve()
    in_p.mkdir(parents=True, exist_ok=True)
    out_p.mkdir(parents=True, exist_ok=True)

    cfg = config or ConversionConfig()
    converter = TelegramConverter()
    video_files = find_video_files(in_p, recursive=recursive)
    summary = BatchSummary(total=len(video_files))

    for idx, video_path in enumerate(video_files, 1):
        if progress_callback:
            progress_callback(video_path, idx, len(video_files))

        rel_parent = video_path.parent.relative_to(in_p) if recursive else Path()
        dest_file = out_p / rel_parent / f"{video_path.stem}.webm"

        result = convert_batch_file(converter, video_path, dest_file, cfg, overwrite=overwrite)
        summary.results.append(result)

        if result.skipped:
            summary.skipped += 1
        elif result.validation and result.validation.valid:
            summary.succeeded += 1
        else:
            summary.failed += 1

    return summary


def watch_folder(
    input_dir: str | Path = "input_videos",
    output_dir: str | Path = "output_stickers",
    config: Optional[ConversionConfig] = None,
    poll_interval: float = 2.0,
    on_convert: Optional[Callable[[BatchFileResult], None]] = None,
):
    """Continuously monitors input_dir and converts newly placed videos in real time."""
    in_p, out_p = Path(input_dir).resolve(), Path(output_dir).resolve()
    in_p.mkdir(parents=True, exist_ok=True)
    out_p.mkdir(parents=True, exist_ok=True)

    cfg = config or ConversionConfig()
    converter = TelegramConverter()
    processed_files: Set[str] = {f.stem for f in out_p.glob("*.webm")}

    while True:
        try:
            for item in in_p.iterdir():
                if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS and item.stem not in processed_files:
                    dest_file = out_p / f"{item.stem}.webm"
                    result = convert_batch_file(converter, item, dest_file, cfg, overwrite=True)
                    processed_files.add(item.stem)
                    if on_convert:
                        on_convert(result)
            time.sleep(poll_interval)
        except KeyboardInterrupt:
            break
