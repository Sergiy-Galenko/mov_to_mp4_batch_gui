from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models import ConversionSettings, MediaInfo, PreviewItem, PreviewSummary, TaskItem
from app.settings import merge_settings_maps, settings_map_to_model
from services.ffmpeg_service import FfmpegService
from services.smart_convert_service import apply_smart_settings
from services.validation_service import OPERATION_LABELS, operation_supports_media
from utils.files import build_merge_output_path, build_output_path


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
        base_settings = settings_map_to_model(settings_map, defaults=ConversionSettings())
        resolved_by_path: Dict[Path, ConversionSettings] = {}
        for task in tasks:
            merged_map = merge_settings_maps(settings_map, task.overrides)
            resolved = settings_map_to_model(merged_map, defaults=ConversionSettings())
            resolved_by_path[task.path] = apply_smart_settings(
                resolved,
                info_cache.get(task.path),
                media_type=task.media_type,
                source_path=task.path,
            )

        merge_candidates = [
            task
            for task in tasks
            if task.media_type == "video" and resolved_by_path[task.path].operation == "convert"
        ]
        merge_enabled = base_settings.merge and len(merge_candidates) >= 2
        merge_paths = {task.path for task in merge_candidates} if merge_enabled else set()
        merge_desired_path: Optional[Path] = None
        merge_preview_path: Optional[Path] = None
        merge_command = ""
        if merge_enabled:
            merge_desired_path = build_merge_output_path(
                out_dir,
                base_settings.merge_name,
                base_settings.out_video_format,
                overwrite=True,
                skip_existing=True,
            )
            merge_preview_path = build_merge_output_path(
                out_dir,
                base_settings.merge_name,
                base_settings.out_video_format,
                overwrite=base_settings.overwrite,
                skip_existing=base_settings.skip_existing,
            )
            merge_command = self.build_merge_command(merge_candidates, base_settings, merge_preview_path, info_cache)

        for index, task in enumerate(tasks, start=1):
            resolved = resolved_by_path[task.path]
            if merge_enabled and task.path in merge_paths and merge_desired_path and merge_preview_path:
                desired_path = merge_desired_path
                preview_path = merge_preview_path
                warnings = self._warnings_for(task, base_settings, desired_path, preview_path)
                command = merge_command
                operation = f"Merge ({len(merge_candidates)} файлів)"
                parameters = self._parameter_summary("merge", base_settings)
            else:
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
                operation = OPERATION_LABELS.get(resolved.operation, resolved.operation)
                parameters = self._parameter_summary(task.media_type, resolved)
            preview = PreviewItem(
                source_path=task.path,
                output_path=preview_path,
                operation=operation,
                parameters=parameters,
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
        if settings.operation == "convert" and task.media_type == "text":
            return f"text-convert {task.path} -> {output_path}"
        if settings.operation == "auto_subtitle":
            return f"whisper {self._format_command([task.path])} -> {output_path}"
        if not self.ffmpeg.ffmpeg_path:
            return "FFmpeg не задано"
        try:
            info_cache = media_info or {}
            op = settings.operation
            if op in {"convert", "subtitle_burn"}:
                if task.media_type == "video":
                    info = info_cache.get(task.path)
                    filter_arg, _, _, _, filters_used = self.ffmpeg.build_video_filter_spec(task.path, settings, output_path.suffix)
                    audio_processing = self.ffmpeg.has_audio_processing(settings) or bool(settings.replace_audio_path.strip())
                    allow_fast, _ = self.ffmpeg.fast_copy_allowed(
                        task.path,
                        output_path.suffix,
                        info,
                        filters_used,
                        audio_processing,
                        allow_remux=settings.smart_convert_enabled and settings.smart_reencode_detection,
                    )
                    if (
                        settings.smart_convert_enabled
                        and settings.smart_reencode_detection
                        and allow_fast
                        and not self.ffmpeg.source_matches_codec_choice(info, settings.video_codec, output_path.suffix)
                    ):
                        allow_fast = False
                    allow_fast = settings.fast_copy and allow_fast
                    cmd = self.ffmpeg.build_video_command(task.path, output_path, settings, info, allow_fast)
                    if settings.smart_two_pass and settings.target_size_mb and not allow_fast:
                        passlog = output_path.with_suffix(output_path.suffix + ".ffmpeg2pass")
                        pass1, pass2 = self.ffmpeg.build_two_pass_commands(cmd, passlog)
                        return self._format_command(pass1) + "\n" + self._format_command(pass2)
                elif task.media_type == "image":
                    cmd = self.ffmpeg.build_image_command(task.path, output_path, settings)
                elif task.media_type == "audio":
                    info = info_cache.get(task.path)
                    cmd = self.ffmpeg.build_audio_command(
                        task.path,
                        output_path,
                        settings,
                        duration=info.duration if info else None,
                    )
                elif task.media_type == "subtitle":
                    cmd = self.ffmpeg.build_subtitle_file_command(task.path, output_path, settings)
                else:
                    return "Невідомий тип файлу"
            elif op == "audio_only":
                info = info_cache.get(task.path)
                cmd = self.ffmpeg.build_audio_command(
                    task.path,
                    output_path,
                    settings,
                    duration=info.duration if info else None,
                )
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

    def build_merge_command(
        self,
        tasks: List[TaskItem],
        settings: ConversionSettings,
        output_path: Path,
        media_info: Optional[Dict[Path, MediaInfo]] = None,
    ) -> str:
        if not self.ffmpeg.ffmpeg_path:
            return "FFmpeg не задано"
        if len(tasks) < 2:
            return "Merge потребує щонайменше 2 відео"
        list_path = ""
        try:
            info_cache = media_info or {}
            paths = [task.path for task in tasks]
            allow_fast = False
            if settings.fast_copy:
                filter_arg, _, _, _, filters_used = self.ffmpeg.build_video_filter_spec(
                    paths[0],
                    settings,
                    output_path.suffix,
                )
                trim_args = self.ffmpeg.build_trim_args(settings)
                allow_fast, _ = self.ffmpeg.merge_copy_allowed(
                    paths,
                    output_path.suffix,
                    info_cache,
                    filters_used,
                    self.ffmpeg.has_audio_processing(settings),
                    trim_args,
                )
            cmd, list_path = self.ffmpeg.build_merge_command(
                paths,
                output_path,
                settings,
                info_cache,
                allow_fast,
            )
            return self._format_command(cmd)
        except Exception as exc:
            return f"Не вдалося зібрати merge dry-run команду: {exc}"
        finally:
            if list_path:
                try:
                    Path(list_path).unlink(missing_ok=True)
                except Exception:
                    pass

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
        if media_type_name == "merge":
            params.append(settings.out_video_format)
            params.append(settings.video_codec)
            params.append(settings.performance_profile)
            params.append(f"target {settings.target_size_mb:g} MB" if settings.target_size_mb else f"CRF {settings.crf}")
            return params
        if settings.operation in {"convert", "subtitle_burn"}:
            if media_type_name == "video":
                params.append(settings.out_video_format)
                params.append(settings.video_codec)
                params.append(settings.performance_profile)
                params.append(f"target {settings.target_size_mb:g} MB" if settings.target_size_mb else f"CRF {settings.crf}")
            elif media_type_name == "image":
                params.append(settings.out_image_format)
                params.append(f"якість {settings.img_quality}")
            elif media_type_name == "audio":
                params.append(settings.out_audio_format)
                params.append(settings.audio_bitrate)
            elif media_type_name == "subtitle":
                params.append(settings.out_subtitle_format)
            elif media_type_name == "text":
                params.append(settings.out_text_format)
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
        if settings.smart_convert_enabled:
            params.append("smart")
        if settings.smart_two_pass and settings.target_size_mb:
            params.append("two-pass")
        if settings.smart_quality_metric != "none":
            params.append(settings.smart_quality_metric.upper())
        return params
