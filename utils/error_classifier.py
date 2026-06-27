"""FFmpeg error classifier.

Maps raw FFmpeg stderr patterns to user-friendly messages and categories.
Useful for presenting actionable information in the UI instead of raw CLI output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class ErrorClassification:
    """Classified FFmpeg error."""

    category: str  # e.g. "codec", "file", "memory", "permission", "format", "unknown"
    message: str  # user-friendly message
    suggestion: str = ""  # actionable suggestion for the user
    raw_line: str = ""  # original stderr line that matched


# (compiled pattern, category, user message, suggestion)
_RULES: List[Tuple[re.Pattern[str], str, str, str]] = [
    # File access
    (
        re.compile(r"No such file or directory", re.IGNORECASE),
        "file",
        "Файл не знайдено",
        "Перевір, чи файл існує за вказаним шляхом.",
    ),
    (
        re.compile(r"Permission denied", re.IGNORECASE),
        "permission",
        "Немає прав доступу до файлу",
        "Перевір права доступу до файлу або папки виводу.",
    ),
    (
        re.compile(r"Is a directory", re.IGNORECASE),
        "file",
        "Вказано папку замість файлу",
        "Вкажи шлях до файлу, а не до папки.",
    ),
    # Codec errors
    (
        re.compile(r"Unknown encoder", re.IGNORECASE),
        "codec",
        "Невідомий кодек",
        "Перевір, чи FFmpeg скомпільовано з потрібним кодеком.",
    ),
    (
        re.compile(r"Decoder .+ not found", re.IGNORECASE),
        "codec",
        "Декодер не знайдено",
        "Переінсталюй FFmpeg з підтримкою цього формату.",
    ),
    (
        re.compile(r"Encoder .+ not found", re.IGNORECASE),
        "codec",
        "Енкодер не знайдено",
        "Переінсталюй FFmpeg з підтримкою цього кодека.",
    ),
    (
        re.compile(r"codec not currently supported in container", re.IGNORECASE),
        "format",
        "Кодек не підтримується у цьому контейнері",
        "Спробуй інший вихідний формат або кодек.",
    ),
    # Hardware acceleration
    (
        re.compile(r"(nvenc|cuda|cuvid).*(error|fail|not found|unavailable)", re.IGNORECASE),
        "hardware",
        "Помилка GPU-енкодера NVENC",
        "Перевір драйвери NVIDIA або переключись на CPU.",
    ),
    (
        re.compile(r"(qsv|mfx).*(error|fail|not found|unavailable)", re.IGNORECASE),
        "hardware",
        "Помилка GPU-енкодера QSV (Intel)",
        "Перевір драйвери Intel або переключись на CPU.",
    ),
    (
        re.compile(r"(amf|opencl).*(error|fail|not found|unavailable)", re.IGNORECASE),
        "hardware",
        "Помилка GPU-енкодера AMF (AMD)",
        "Перевір драйвери AMD або переключись на CPU.",
    ),
    (
        re.compile(r"Cannot (load|open).*(d3d|dxva|vaapi|vulkan)", re.IGNORECASE),
        "hardware",
        "Помилка апаратного декодера",
        "Перевір драйвери GPU або вимкни апаратне прискорення.",
    ),
    # Format errors
    (
        re.compile(r"Invalid data found when processing input", re.IGNORECASE),
        "format",
        "Вхідний файл пошкоджено або формат не підтримується",
        "Спробуй конвертувати іншим інструментом або перевантаж файл.",
    ),
    (
        re.compile(r"Discarding .+ of corrupted data", re.IGNORECASE),
        "format",
        "Файл містить пошкоджені дані",
        "Частина даних може бути втрачена. Перевір вхідний файл.",
    ),
    (
        re.compile(r"moov atom not found", re.IGNORECASE),
        "format",
        "Файл MP4 не має метаданих (moov atom)",
        "Файл може бути неповністю записаний або пошкоджений.",
    ),
    # Memory / resources
    (
        re.compile(r"Cannot allocate memory", re.IGNORECASE),
        "memory",
        "Недостатньо оперативної пам'яті",
        "Закрий інші програми або зменш якість/роздільність.",
    ),
    (
        re.compile(r"Out of memory", re.IGNORECASE),
        "memory",
        "Вичерпано пам'ять",
        "Зменш роздільність або вимкни фільтри.",
    ),
    (
        re.compile(r"No space left on device", re.IGNORECASE),
        "disk",
        "Недостатньо місця на диску",
        "Звільни місце у папці виводу.",
    ),
    # Filter errors
    (
        re.compile(r"No such filter:", re.IGNORECASE),
        "filter",
        "Фільтр FFmpeg не знайдено",
        "Перевір назву фільтра або оновіть FFmpeg.",
    ),
    (
        re.compile(r"Error (initializing|configuring|applying).+filter", re.IGNORECASE),
        "filter",
        "Помилка ініціалізації фільтра",
        "Перевір параметри фільтра (розмір, кроп, швидкість).",
    ),
    # Subtitle errors
    (
        re.compile(r"Subtitle .+ not found", re.IGNORECASE),
        "subtitle",
        "Потік субтитрів не знайдено",
        "Перевір наявність субтитрів у вхідному файлі.",
    ),
    (
        re.compile(r"Cannot open .+\.(srt|ass|ssa|vtt)", re.IGNORECASE),
        "subtitle",
        "Не вдалося відкрити файл субтитрів",
        "Перевір шлях до файлу субтитрів.",
    ),
    # Audio errors
    (
        re.compile(r"Audio .+ stream .+ not found", re.IGNORECASE),
        "audio",
        "Аудіо потік не знайдено",
        "Файл не містить аудіо або вибрано неправильний трек.",
    ),
    # Generic catch-alls (order matters — these are last)
    (
        re.compile(r"Conversion failed", re.IGNORECASE),
        "generic",
        "Конвертація завершилась з помилкою",
        "Перевір лог для деталей.",
    ),
    (
        re.compile(r"Error .+ occurred", re.IGNORECASE),
        "generic",
        "Сталася помилка під час обробки",
        "Перевір лог для деталей.",
    ),
]


def classify_error(stderr: str) -> ErrorClassification:
    """Classify a single stderr line or block.

    Returns an ``ErrorClassification`` with category, user-friendly message,
    and actionable suggestion.
    """
    if not stderr or not stderr.strip():
        return ErrorClassification(
            category="unknown",
            message="Невідома помилка",
            suggestion="Перевір лог для деталей.",
            raw_line="",
        )

    for pattern, category, message, suggestion in _RULES:
        if pattern.search(stderr):
            return ErrorClassification(
                category=category,
                message=message,
                suggestion=suggestion,
                raw_line=stderr.strip(),
            )

    return ErrorClassification(
        category="unknown",
        message="Невідома помилка FFmpeg",
        suggestion="Перевір повний лог для діагностики.",
        raw_line=stderr.strip(),
    )


def classify_stderr_block(stderr_block: str) -> List[ErrorClassification]:
    """Classify multiple lines of stderr.

    Returns a list of unique classifications (deduplicated by category+message).
    """
    seen = set()
    results: List[ErrorClassification] = []

    for line in stderr_block.splitlines():
        line = line.strip()
        if not line:
            continue
        cls = classify_error(line)
        key = (cls.category, cls.message)
        if key not in seen:
            seen.add(key)
            results.append(cls)

    return results


def error_summary(stderr_block: str) -> str:
    """Return a single-line user-friendly summary from an stderr block."""
    classifications = classify_stderr_block(stderr_block)
    if not classifications:
        return ""
    # Return the first non-unknown classification, or the first one
    for cls in classifications:
        if cls.category != "unknown":
            return f"{cls.message}. {cls.suggestion}"
    return f"{classifications[0].message}. {classifications[0].suggestion}"
