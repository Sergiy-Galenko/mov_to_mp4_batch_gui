from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.models import ConversionSettings, MediaInfo, PreviewItem, PreviewSummary, TaskItem
from core.settings import merge_settings_maps, settings_map_to_model
from services.ffmpeg_service import FfmpegService
from services.validation_service import OPERATION_LABELS, operation_supports_media
from utils.files import build_output_path


class PreviewBuilder:
    def __init__(self, ffmpeg: FfmpegService) -> None:
        self.ffmpeg = ffmpeg

    def build(
        self,
        settings_map: Dict[str, Any],
        *,
        tasks: List[TaskItem],
        output_dir: str,
        selected_path: str = "",
        media_info: Optional[Dict[Path, MediaInfo]] = None,
        max_lines: int = 20,
    ) -> PreviewSummary:
        if not tasks:
            return PreviewSummary(text="Черга порожня.")

        info_cache = media_info or {}
        out_dir = Path(output_dir).expanduser()
        items: List[PreviewItem] = []
        lines: List[str] = []
        selected = Path(selected_path).expanduser() if selected_path else None
        selected_item: Optional[PreviewItem] = None

        for index, task in enumerate(tasks, start=1):
            merged_map = merge_settings_maps(settings_map, task.overrides)
            resolved = settings_map_to_model(merged_map, defaults=ConversionSettings())
            out_ext = self.ffmpeg.output_extension_for(task.media_type, resolved)
            desired_path = build_output_path(
                out_dir,
                task.path,
                out_ext,
                template=resolved.output_template,
                index=index,
                operation=resolved.operation,
                media_type_name=task.media_type,
                overwrite=True,
                skip_existing=True,
            )
            preview_path = build_output_path(
                out_dir,
                task.path,
                out_ext,
                template=resolved.output_template,
                index=index,
                operation=resolved.operation,
                media_type_name=task.media_type,
                overwrite=resolved.overwrite,
                skip_existing=resolved.skip_existing,
            )
            warnings = self._warnings_for(task, resolved, desired_path, preview_path)
            command = self.build_command(task, resolved, preview_path, info_cache)
            preview = PreviewItem(
                source_path=task.path,
                output_path=preview_path,
                operation=OPERATION_LABELS.get(resolved.operation, resolved.operation),
                parameters=self._parameter_summary(task.media_type, resolved),
                warnings=warnings,
                command=command,
            )
            items.append(preview)
            if selected and task.path == selected:
                selected_item = preview
            elif selected_item is None and index == 1:
                selected_item = preview

            warning_text = f" | {'; '.join(warnings)}" if warnings else ""
            params = ", ".join(preview.parameters[:4])
            lines.append(
                f"{index:02d}. {task.path.name} -> {preview_path.name} | {preview.operation}"
                f"{' | ' + params if params else ''}{warning_text}"
            )

        visible_lines = lines
        if len(visible_lines) > max_lines:
            remaining = len(visible_lines) - max_lines
            visible_lines = visible_lines[:max_lines] + [f"... ще {remaining} файлів"]

        summary = PreviewSummary(
            items=items,
            text="\n".join(visible_lines),
            warnings=[warning for item in items for warning in item.warnings],
        )
        if selected_item is not None:
            summary.selected_source = str(selected_item.source_path)
            summary.selected_output = str(selected_item.output_path)
            summary.selected_command = selected_item.command or "—"
        return summary

    def build_command(
        self,
        task: TaskItem,
        settings: ConversionSettings,
        output_path: Path,
        media_info: Optional[Dict[Path, MediaInfo]] = None,
    ) -> str:
        if not operation_supports_media(settings.operation, task.media_type):
            return "Операція не підтримує тип цього файлу"
        if settings.operation == "auto_subtitle":
            return f"whisper {self._format_command([task.path])} -> {output_path}"
        if not self.ffmpeg.ffmpeg_path:
            return "FFmpeg не задано"
        try:
            info_cache = media_info or {}
            op = settings.operation
            if op in {"convert", "subtitle_burn"}:
                if task.media_type == "video":
                    cmd = self.ffmpeg.build_video_command(task.path, output_path, settings, info_cache.get(task.path), False)
                elif task.media_type == "image":
                    cmd = self.ffmpeg.build_image_command(task.path, output_path, settings)
                elif task.media_type == "audio":
                    cmd = self.ffmpeg.build_audio_command(task.path, output_path, settings)
                elif task.media_type == "subtitle":
                    cmd = self.ffmpeg.build_subtitle_file_command(task.path, output_path, settings)
                else:
                    return "Невідомий тип файлу"
            elif op == "audio_only":
                cmd = self.ffmpeg.build_audio_command(task.path, output_path, settings)
            elif op == "subtitle_extract":
                cmd = self.ffmpeg.build_subtitle_extract_command(task.path, output_path, settings)
            elif op == "thumbnail":
                cmd = self.ffmpeg.build_thumbnail_command(task.path, output_path, settings)
            elif op == "contact_sheet":
                cmd = self.ffmpeg.build_contact_sheet_command(task.path, output_path, settings)
            else:
                return "Dry-run недоступний для цієї операції"
            return self._format_command(cmd)
        except Exception as exc:
            return f"Не вдалося зібрати dry-run команду: {exc}"

    def _format_command(self, cmd: List[Any]) -> str:
        return subprocess.list2cmdline([str(part) for part in cmd])

    def _warnings_for(
        self,
        task: TaskItem,
        settings: ConversionSettings,
        desired_path: Path,
        preview_path: Path,
    ) -> List[str]:
        warnings: List[str] = []
        if not operation_supports_media(settings.operation, task.media_type):
            warnings.append("операція не підтримує цей тип")
        if desired_path.exists():
            if settings.overwrite:
                warnings.append("буде перезаписано")
            elif settings.skip_existing:
                warnings.append("буде пропущено")
            elif desired_path != preview_path:
                warnings.append(f"буде перейменовано в {preview_path.name}")
        return warnings

    def _parameter_summary(self, media_type_name: str, settings: ConversionSettings) -> List[str]:
        params: List[str] = []
        if settings.operation in {"convert", "subtitle_burn"}:
            if media_type_name == "video":
                params.append(settings.out_video_format)
                params.append(settings.video_codec)
                params.append(f"CRF {settings.crf}")
            elif media_type_name == "image":
                params.append(settings.out_image_format)
                params.append(f"якість {settings.img_quality}")
            elif media_type_name == "audio":
                params.append(settings.out_audio_format)
                params.append(settings.audio_bitrate)
            elif media_type_name == "subtitle":
                params.append(settings.out_subtitle_format)
        elif settings.operation == "audio_only":
            params.append(settings.out_audio_format)
            params.append(settings.audio_bitrate)
        elif settings.operation in {"subtitle_extract", "auto_subtitle"}:
            params.append(settings.out_subtitle_format)
        elif settings.operation in {"thumbnail", "contact_sheet"}:
            params.append(settings.out_image_format)
        if settings.trim_start is not None or settings.trim_end is not None:
            params.append("trim")
        if settings.resize_w or settings.resize_h:
            params.append("resize")
        if settings.crop_w and settings.crop_h:
            params.append("crop")
        if settings.speed:
            params.append(f"speed {settings.speed:g}x")
        if settings.watermark_path:
            params.append("watermark")
        if settings.text_wm:
            params.append("text")
        return params
