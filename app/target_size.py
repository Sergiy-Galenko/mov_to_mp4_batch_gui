"""Decimal MB budgets shared by preflight, encoder and output verification."""

import math

MB_BYTES = 1_000_000
MUX_RESERVE = 0.06
MIN_VIDEO_KBPS = 120
TARGET_FORMATS = {"mp4", "mov", "mkv", "avi"}


def target_size_bytes(size_mb: float) -> int:
    if not math.isfinite(size_mb) or size_mb <= 0:
        raise ValueError("Target size має бути додатним скінченним числом.")
    return int(size_mb * MB_BYTES)


def target_mode_error(codec: str, out_format: str, merge: bool = False) -> str:
    if codec not in {"auto", "Авто", "Auto", "H.264 (AVC)", "h264"}:
        return f"Target size несумісний із {codec}. Вибери H.264 або вимкни цільовий розмір."
    if out_format.lower().lstrip(".") not in TARGET_FORMATS:
        return "Target size підтримує MP4, MOV, MKV та AVI (H.264)."
    if merge:
        return "Target size: вимкни об’єднання, щоб задати розмір для кожного відео."
    return ""
