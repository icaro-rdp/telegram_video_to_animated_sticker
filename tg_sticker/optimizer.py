"""Optimization routines to ensure video files strictly meet Telegram's 256 KB limit."""

from __future__ import annotations

from dataclasses import dataclass

MAX_TELEGRAM_STICKER_BYTES = 256 * 1024  # 262,144 bytes
SAFE_TARGET_BYTES = 250 * 1024  # 256,000 bytes (safety headroom)


@dataclass
class EncodingParams:
    crf: int = 30
    bitrate_kbps: int = 0
    maxrate_kbps: int = 0
    bufsize_kbps: int = 0
    two_pass: bool = False
    fps: int = 30


def calculate_target_bitrate(
    duration_sec: float, target_bytes: int = SAFE_TARGET_BYTES
) -> int:
    """Calculates max allowed average bitrate (in kbps) for a given duration to fit inside byte budget."""
    safe_dur = max(duration_sec, 0.5)
    total_kbits = (target_bytes * 8) / 1000.0
    bitrate_kbps = int(total_kbits / safe_dur)
    # Clamp to reasonable bounds
    return max(min(bitrate_kbps, 1500), 100)


def plan_reencode_strategy(
    current_size_bytes: int,
    duration_sec: float,
    attempt: int,
    current_fps: int = 30,
) -> EncodingParams:
    """
    Given a file that exceeded 256 KB, determines the next encoding strategy.
    attempt 1: Constrained 2-pass with calculated target bitrate.
    attempt 2: Constrained 2-pass with 80% bitrate budget and higher CRF.
    attempt 3: Reduced framerate (24 fps) and 65% bitrate budget.
    attempt 4+: Aggressive compression fallback (20 fps, 50% bitrate).
    """
    base_bitrate = calculate_target_bitrate(duration_sec, SAFE_TARGET_BYTES)

    if attempt == 1:
        # First fallback: 2-pass constrained VBR
        target_bitrate = int(base_bitrate * 0.9)
        return EncodingParams(
            crf=34,
            bitrate_kbps=target_bitrate,
            maxrate_kbps=int(target_bitrate * 1.1),
            bufsize_kbps=target_bitrate * 2,
            two_pass=True,
            fps=current_fps,
        )
    elif attempt == 2:
        # Second fallback: tighter bitrate
        target_bitrate = int(base_bitrate * 0.75)
        return EncodingParams(
            crf=38,
            bitrate_kbps=target_bitrate,
            maxrate_kbps=int(target_bitrate * 1.05),
            bufsize_kbps=target_bitrate * 2,
            two_pass=True,
            fps=current_fps,
        )
    elif attempt == 3:
        # Third fallback: reduce FPS to 24
        target_bitrate = int(base_bitrate * 0.65)
        return EncodingParams(
            crf=42,
            bitrate_kbps=target_bitrate,
            maxrate_kbps=int(target_bitrate * 1.0),
            bufsize_kbps=target_bitrate * 2,
            two_pass=True,
            fps=min(current_fps, 24),
        )
    else:
        # Aggressive fallback: 20 FPS, very low bitrate
        target_bitrate = int(base_bitrate * 0.5)
        return EncodingParams(
            crf=46,
            bitrate_kbps=target_bitrate,
            maxrate_kbps=int(target_bitrate * 1.0),
            bufsize_kbps=target_bitrate * 2,
            two_pass=True,
            fps=min(current_fps, 20),
        )
