from __future__ import annotations

import shutil
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from app.constants import OUT_AUDIO_FORMATS, OUT_IMAGE_FORMATS, OUT_SUBTITLE_FORMATS, OUT_TEXT_FORMATS, OUT_VIDEO_FORMATS
from app.models import ConversionSettings, TaskItem
from app.paths import find_ffprobe
from app.settings import merge_settings_maps, settings_map_to_model
from services.ffmpeg_service import FfmpegService
from utils.files import build_merge_output_path, build_output_path, is_subtitle, sanitize_file_stem
from utils.formatting import parse_float, parse_time_to_seconds

OPERATION_LABELS = {
    "convert": "Конвертація",
    "audio_only": "Лише аудіо",
    "auto_subtitle": "Авто субтитри",
    "subtitle_extract": "Витяг субтитрів",
    "subtitle_burn": "Вшити субтитри",
    "thumbnail": "Мініатюра",
    "contact_sheet": "Контакт-лист",
}


def operation_supports_media(operation: str, media_type_name: str) -> bool:
    if operation == "convert":
        return media_type_name in {"video", "image", "audio", "subtitle", "text"}
    if operation == "audio_only":
        return media_type_name in {"video", "audio"}
    if operation == "auto_subtitle":
        return media_type_name in {"video", "audio"}
    if operation in {"subtitle_extract", "subtitle_burn", "thumbnail", "contact_sheet"}:
        return media_type_name == "video"
    return False


class ValidationService:
    def __init__(self, ffmpeg: FfmpegService) -> None:
        self.ffmpeg = ffmpeg

    def validate(
        self,
        raw: dict[str, Any],
        *,
        tasks: Iterable[TaskItem],
        output_dir: str,
        ffmpeg_path: str,
        include_queue: bool = True,
        require_output_dir: bool = True,
        only_paths: set[Path] | None = None,
    ) -> dict[str, Any]:
        errors: dict[str, str] = {}
        warnings: list[str] = []

        def add_error(field: str, message: str) -> None:
            errors.setdefault(field, message)

        def add_warning(message: str) -> None:
            if message not in warnings:
                warnings.append(message)

        self._validate_fields(raw, add_error)

        output_text = str(output_dir or "").strip()
        output_path = Path(output_text).expanduser() if output_text else Path.cwd()
        if require_output_dir:
            if not output_text:
                add_error("output_dir", "Папку виводу не задано.")
            elif output_path.exists() and not output_path.is_dir():
                add_error("output_dir", "Шлях виводу має бути папкою.")
            elif not output_path.exists():
                parent = output_path.parent
                if parent and not parent.exists():
                    add_error("output_dir", "Батьківська папка для виводу не існує.")

        queue_items = [item for item in tasks if only_paths is None or item.path in only_paths]
        settings = settings_map_to_model(raw, defaults=ConversionSettings())

        if settings.trim_start is not None and settings.trim_end is not None and settings.trim_end <= settings.trim_start:
            add_error("trim_end", "Кінець обрізання має бути більшим за початок.")
        if settings.smart_two_pass and not settings.target_size_mb:
            add_warning("Smart two-pass працює тільки коли задано цільовий розмір.")
        if settings.smart_quality_metric == "vmaf":
            add_warning("VMAF потребує FFmpeg із фільтром libvmaf; якщо фільтра немає, буде warning після конвертації.")
        if settings.smart_ab_test and not settings.smart_ab_crfs.strip():
            add_warning("A/B тест увімкнено, але список CRF порожній.")

        if include_queue:
            if not queue_items:
                add_error("queue", "Черга порожня.")
            needs_ffmpeg = not queue_items or any(
                item.media_type != "text" or settings_map_to_model(merge_settings_maps(raw, item.overrides), defaults=ConversionSettings()).operation != "convert"
                for item in queue_items
            )
            if needs_ffmpeg:
                self._validate_ffmpeg(ffmpeg_path, add_error, add_warning)
            self._validate_queue(queue_items, raw, settings, output_path, add_error, add_warning)

        self._validate_format_compat(raw, add_warning)

        if include_queue and output_path.exists():
            self._validate_disk_space(queue_items, settings, output_path, add_error, add_warning)

        summary_bits = []
        if errors:
            summary_bits.append(f"Критичних помилок: {len(errors)}")
        if warnings:
            summary_bits.append(f"Попереджень: {len(warnings)}")
        summary = " | ".join(summary_bits) if summary_bits else "Перевірка пройдена."
        return {"ok": not errors, "errors": errors, "warnings": warnings, "summary": summary}

    def _validate_fields(self, raw: dict[str, Any], add_error) -> None:
        positive_int_fields = {
            "resize_w": "Ширина resize",
            "resize_h": "Висота resize",
            "crop_w": "Ширина crop",
            "crop_h": "Висота crop",
            "sheet_cols": "Колонки контакт-листа",
            "sheet_rows": "Рядки контакт-листа",
            "sheet_width": "Ширина кадру контакт-листа",
            "sheet_interval": "Інтервал контакт-листа",
        }
        non_negative_int_fields = {
            "crop_x": "Crop X",
            "crop_y": "Crop Y",
        }
        for field, label in positive_int_fields.items():
            value = str(raw.get(field, "")).strip()
            if value and (not value.isdigit() or int(value) <= 0):
                add_error(field, f"{label}: очікується додатне число.")
        for field, label in non_negative_int_fields.items():
            value = str(raw.get(field, "")).strip()
            if value and not value.isdigit():
                add_error(field, f"{label}: очікується 0 або додатне число.")

        for field, label in {"trim_start": "Початок", "trim_end": "Кінець", "thumbnail_time": "Час мініатюри"}.items():
            value = str(raw.get(field, "")).strip()
            if value and parse_time_to_seconds(value) is None:
                add_error(field, f"{label}: формат має бути секундами або hh:mm:ss.")

        speed_value = str(raw.get("speed", "")).strip()
        if speed_value:
            parsed_speed = parse_float(speed_value)
            if parsed_speed is None or parsed_speed <= 0:
                add_error("speed", "Швидкість має бути числом більше 0.")

        for field, label in {
            "audio_bitrate": "Бітрейт аудіо",
            "silence_duration": "Тривалість тиші",
            "audio_peak_limit_db": "Peak limit",
        }.items():
            value = str(raw.get(field, "")).strip()
            if field == "audio_bitrate":
                if value and not any(ch.isdigit() for ch in value):
                    add_error(field, f"{label}: вкажи значення на кшталт 192k.")
                continue
            if value and parse_float(value) is None:
                add_error(field, f"{label}: очікується число.")

        for field, label in {
            "wm_path": "Водяний знак",
            "cover_art_path": "Cover art",
            "text_font": "Шрифт",
            "subtitle_path": "Субтитри",
            "replace_audio_path": "Аудіо для заміни",
        }.items():
            value = str(raw.get(field, "")).strip()
            if value and not Path(value).expanduser().exists():
                add_error(field, f"{label}: файл не знайдено.")

        subtitle_path = str(raw.get("subtitle_path", "")).strip()
        if subtitle_path and not is_subtitle(Path(subtitle_path).expanduser()):
            add_error("subtitle_path", "Субтитри: формат не підтримується.")

    def _validate_ffmpeg(self, ffmpeg_path: str, add_error, add_warning) -> None:
        if not ffmpeg_path:
            add_error("ffmpeg", "FFmpeg не знайдено або не задано.")
            return
        ffmpeg_text = str(ffmpeg_path).strip()
        if not Path(ffmpeg_text).expanduser().exists() and shutil.which(ffmpeg_text) is None:
            add_error("ffmpeg", "FFmpeg недоступний за вказаним шляхом.")
            return
        if not find_ffprobe(ffmpeg_text):
            add_warning("FFprobe не знайдено; аналіз медіа, ETA і preflight будуть обмежені.")

    def _validate_queue(
        self,
        queue_items: list[TaskItem],
        raw: dict[str, Any],
        settings: ConversionSettings,
        output_dir: Path,
        add_error,
        add_warning,
    ) -> None:
        unsupported = [item for item in queue_items if not operation_supports_media(settings.operation, item.media_type)]
        if unsupported:
            label = OPERATION_LABELS.get(settings.operation, settings.operation)
            add_error(
                "queue",
                f"Операція '{label}' не підтримує частину файлів у черзі: {len(unsupported)}.",
            )
        for item in queue_items:
            if not item.path.exists():
                add_error("queue", f"Файл не знайдено: {item.path}")
                break

        resolved_by_path: dict[Path, ConversionSettings] = {}
        for item in queue_items:
            merged = merge_settings_maps(raw, item.overrides)
            resolved_by_path[item.path] = settings_map_to_model(merged, defaults=ConversionSettings())

        merge_candidates = [
            item
            for item in queue_items
            if item.media_type == "video" and resolved_by_path[item.path].operation == "convert"
        ]
        merge_enabled = settings.merge and len(merge_candidates) >= 2
        merge_paths = {item.path for item in merge_candidates} if merge_enabled else set()

        seen_outputs: dict[Path, str] = {}
        if merge_enabled:
            desired = build_merge_output_path(
                output_dir,
                settings.merge_name,
                settings.out_video_format,
                overwrite=True,
                skip_existing=True,
            )
            seen_outputs[desired] = f"merge ({len(merge_candidates)} відео)"
            if desired.exists():
                if settings.overwrite:
                    add_warning(f"{desired.name}: буде перезаписано.")
                elif settings.skip_existing:
                    add_warning(f"{desired.name}: буде пропущено.")
                else:
                    add_warning(f"{desired.name}: є конфлікт імені, буде створено безпечну копію.")

        for idx, item in enumerate(queue_items, start=1):
            if item.path in merge_paths:
                continue
            resolved = resolved_by_path[item.path]
            try:
                out_ext = self.ffmpeg.output_extension_for(item.media_type, resolved)
                desired = build_output_path(
                    output_dir,
                    item.path,
                    out_ext,
                    template=resolved.output_template,
                    index=idx,
                    operation=resolved.operation,
                    media_type_name=item.media_type,
                    overwrite=True,
                    skip_existing=True,
                )
                if resolved.output_collision_policy == "parent":
                    desired = desired.with_name(f"{sanitize_file_stem(item.path.parent.name)}_{desired.name}")
            except Exception as exc:
                add_error("output_template", f"Не вдалося розрахувати вихідний шлях: {exc}")
                return
            previous = seen_outputs.get(desired)
            if previous is not None:
                if resolved.output_collision_policy in {"stop", "overwrite"}:
                    add_error("output_template", f"Конфлікт імен: {previous} і {item.path.name} -> {desired.name}")
                    break
                add_warning(f"Конфлікт імен {desired.name}: буде застосовано політику '{resolved.output_collision_policy}'.")
            seen_outputs[desired] = item.path.name
            if desired.exists():
                if resolved.output_collision_policy == "overwrite":
                    add_warning(f"{desired.name}: буде перезаписано.")
                elif resolved.output_collision_policy == "stop":
                    add_error("output_template", f"{desired.name}: файл уже існує, batch зупинено політикою колізій.")
                    break
                else:
                    add_warning(f"{desired.name}: є конфлікт імені, буде створено безпечну назву.")

    def _validate_format_compat(self, raw: dict[str, Any], add_warning) -> None:
        out_video = str(raw.get("out_video_fmt", "")).strip().lower()
        out_image = str(raw.get("out_image_fmt", "")).strip().lower()
        out_audio = str(raw.get("out_audio_fmt", "")).strip().lower()
        out_subtitle = str(raw.get("out_subtitle_fmt", raw.get("subtitle_out_fmt", ""))).strip().lower()
        out_text = str(raw.get("out_text_fmt", "")).strip().lower()
        codec = str(raw.get("codec", "")).strip()

        if out_video and out_video not in OUT_VIDEO_FORMATS:
            add_warning(f"Відеоформат '{out_video}' не входить до стандартного списку.")
        if out_image and out_image not in OUT_IMAGE_FORMATS:
            add_warning(f"Формат зображень '{out_image}' не входить до стандартного списку.")
        if out_audio and out_audio not in OUT_AUDIO_FORMATS:
            add_warning(f"Аудіоформат '{out_audio}' не входить до стандартного списку.")
        if out_subtitle and out_subtitle not in OUT_SUBTITLE_FORMATS:
            add_warning(f"Формат субтитрів '{out_subtitle}' не входить до стандартного списку.")
        if out_text and out_text not in OUT_TEXT_FORMATS:
            add_warning(f"Текстовий формат '{out_text}' не входить до стандартного списку.")
        if out_video == "webm" and codec in {"H.264 (AVC)", "H.265 (HEVC)"}:
            add_warning("WebM не сумісний з H.264/H.265; буде використано VP9 або AV1.")
        if out_video in {"mp4", "mov", "avi"} and codec == "VP9 (WebM)":
            add_warning("VP9 краще виводити у WebM; для MP4/MOV буде заміна на H.264.")

    def _validate_disk_space(
        self,
        queue_items: list[TaskItem],
        settings: ConversionSettings,
        output_dir: Path,
        add_error,
        add_warning,
    ) -> None:
        try:
            source_size = sum(item.path.stat().st_size for item in queue_items if item.path.exists())
            free = shutil.disk_usage(output_dir).free
            if not source_size:
                return
            target_bytes = int(settings.target_size_mb * 1024 * 1024) if settings.target_size_mb else 0
            estimated_outputs = target_bytes * len(queue_items) if target_bytes else source_size
            largest_output = target_bytes or max(item.path.stat().st_size for item in queue_items if item.path.exists())
            temporary_bytes = largest_output
            if settings.smart_ab_test:
                temporary_bytes += largest_output * 3
            if settings.smart_two_pass:
                temporary_bytes += max(64 * 1024 * 1024, largest_output // 20)
            margin = settings.disk_safety_margin_mb * 1024 * 1024
            required = estimated_outputs + temporary_bytes + margin
            if free < required:
                add_error(
                    "disk_space",
                    "Недостатньо місця: потрібно приблизно "
                    f"{required / 1024 / 1024:.0f} MiB (включно з тимчасовими файлами), доступно {free / 1024 / 1024:.0f} MiB.",
                )
            elif free < required + 256 * 1024 * 1024:
                add_warning(
                    "Малий запас місця: потрібно приблизно "
                    f"{required / 1024 / 1024:.0f} MiB, доступно {free / 1024 / 1024:.0f} MiB."
                )
        except Exception:
            return
