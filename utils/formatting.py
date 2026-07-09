import re


def format_time(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "--:--"
    total = round(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_bytes(size: int | None) -> str:
    if size is None:
        return "--"
    value = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PB"


def parse_time_to_seconds(text: str) -> float | None:
    raw = text.strip()
    if not raw:
        return None
    if re.fullmatch(r"\d+(\.\d+)?", raw):
        return float(raw)
    parts = raw.split(":")
    try:
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
    except ValueError:
        return None
    return None


def parse_float(text: str) -> float | None:
    raw = text.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def parse_int(text: str) -> int | None:
    raw = text.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def parse_ffmpeg_time(value: str) -> float | None:
    raw = value.strip()
    if not raw:
        return None
    if re.fullmatch(r"\d+(\.\d+)?", raw):
        return float(raw)
    parts = raw.split(":")
    if len(parts) == 3:
        try:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        except ValueError:
            return None
    return None


def build_atempo_chain(speed: float) -> list[float]:
    if speed <= 0:
        return []
    factors: list[float] = []
    while speed > 2.0:
        factors.append(2.0)
        speed /= 2.0
    while speed < 0.5:
        factors.append(0.5)
        speed /= 0.5
    factors.append(speed)
    return factors
