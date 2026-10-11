from __future__ import annotations

from .common import (
    MONTAGE_MEDIA_FILTER,
    Any,
    ConversionSettings,
    Dict,
    List,
    MediaInfo,
    Path,
    QtCore,
    QtGui,
    QtWidgets,
    ReportService,
    csv,
    format_bytes,
    format_time,
    load_json_file,
    merge_settings_maps,
    os,
    prediction_factor,
    save_json_file,
    settings_map_to_model,
    target_size_bytes,
    threading,
    time,
)


class MediaDetailsMixin:
    def _probe_media_async(self, path: Path) -> None:
        info = self.media_analysis.probe(path)
        self.event_queue.put(("media_info", path, info))

    def _prefetch_probe_async(self, path: Path, media_kind: str) -> None:
        if media_kind not in {"video", "audio"}:
            return
        if not self.ffmpeg_service.ffprobe_path or path in self.media_info_cache or path in self._probe_pending:
            return
        self._probe_pending.add(path)

        def run_probe() -> None:
            info = self.media_analysis.probe(path)
            self.event_queue.put(("media_info", path, info))

        self._probe_executor.submit(run_probe)

    def _ensure_thumbnail_async(self, path: Path, media_kind: str) -> None:
        if media_kind == "image":
            self.queue_model.set_thumbnail(path, str(path))
            return
        if media_kind != "video":
            return
        current = self.queue_model.item_by_path(path)
        if path in self._thumbnail_pending or (current and current.thumbnail_path):
            return
        self._thumbnail_pending.add(path)
        self._thumbnail_executor.submit(self._create_thumbnail_async, path, media_kind)

    def _create_thumbnail_async(self, path: Path, media_kind: str) -> None:
        thumbnail = ""
        try:
            thumbnail = self.media_analysis.thumbnail_for(path, media_kind) or ""
        finally:
            self.event_queue.put(("thumbnail", path, thumbnail))

    def _update_info(self, info: MediaInfo) -> None:
        self._info_duration = format_time(info.duration)
        self._info_codec = f"{info.vcodec or '-'} / {info.acodec or '-'}"
        self._info_res = f"{info.width}x{info.height}" if info.width and info.height else "—"
        self._info_size = format_bytes(info.size_bytes)
        self._info_container = info.format_name or "—"
        analysis_bits: List[str] = []
        if info.fps:
            fps_label = f"{info.fps:.3f} fps"
            if info.frame_rate_mode:
                fps_label += f" ({info.frame_rate_mode})"
            analysis_bits.append(fps_label)
        if info.dynamic_range:
            analysis_bits.append(info.dynamic_range)
        if info.color_space:
            analysis_bits.append(info.color_space)
        if info.rotation not in (None, 0):
            analysis_bits.append(f"rotation {info.rotation}°")
        analysis_bits.append(f"audio {info.audio_streams}")
        analysis_bits.append(f"subs {info.subtitle_streams}")
        if info.chapters:
            analysis_bits.append(f"chapters {len(info.chapters)}")
        self._info_analysis = " | ".join(bit for bit in analysis_bits if bit) or "—"
        self._info_warnings = " | ".join(info.warnings) if info.warnings else "—"
        self.infoChanged.emit()

    def _clear_info(self) -> None:
        self._info_name = "—"
        self._info_duration = "--:--"
        self._info_codec = "—"
        self._info_res = "—"
        self._info_size = "—"
        self._info_container = "—"
        self._info_analysis = "—"
        self._info_warnings = "—"
        self.infoChanged.emit()

    @QtCore.Slot()
    def pickWatermark(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, "Вибрати водяний знак", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)"
        )
        if path:
            self.watermarkPicked.emit(path)

    @QtCore.Slot()
    def pickCoverArt(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, "Вибрати cover art", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)"
        )
        if path:
            self.coverArtPicked.emit(path)

    @QtCore.Slot()
    def pickAudioReplace(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, "Вибрати аудіо для заміни", "", "Audio (*.mp3 *.m4a *.aac *.wav *.flac *.opus *.ogg *.mp4 *.mov *.mkv);;All Files (*)"
        )
        if path:
            self.audioReplacePicked.emit(path)

    @QtCore.Slot()
    def pickFont(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Вибрати шрифт", "", "Fonts (*.ttf *.otf);;All Files (*)")
        if path:
            self.fontPicked.emit(path)

    @QtCore.Slot()
    def pickSubtitle(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, "Вибрати субтитри", "", "Subtitles (*.srt *.ass *.ssa *.vtt *.webvtt);;All Files (*)"
        )
        if path:
            self.subtitlePicked.emit(path)

    @QtCore.Slot(result=str)
    def pickVideoFile(self) -> str:
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(None, "Вибрати медіа для монтажу (відео / фото)", "", MONTAGE_MEDIA_FILTER)
        if files:
            paths = [Path(path) for path in files]
            self._remember_folder(str(paths[0].parent))
            self._add_paths(paths)
            return str(paths[0])
        return ""

    @QtCore.Slot(result=str)
    def pickMediaFile(self) -> str:
        return self.pickVideoFile()

    @QtCore.Slot(str, result=str)
    def readTextPreview(self, path_text: str) -> str:
        path = Path(str(path_text or "").strip()).expanduser()
        if not path.exists() or not path.is_file():
            return ""
        try:
            from services.text_conversion_service import read_text_file

            text, encoding = read_text_file(path)
        except Exception as exc:
            return f"Preview unavailable: {exc}"
        limit = 6000
        suffix = f"\n\n... ({encoding})" if len(text) > limit else f"\n\n({encoding})"
        return text[:limit] + suffix

    @QtCore.Slot("QVariantMap", result="QVariantMap")
    def targetSizeEstimate(self, settings_map: Dict[str, Any]) -> Dict[str, Any]:
        import math

        settings = settings_map_to_model(dict(settings_map), defaults=ConversionSettings())
        if not settings.target_size_mb or not math.isfinite(settings.target_size_mb):
            return {}
        candidates = [task for task in self.queue_model.items() if task.media_type == "video"]
        estimates = []
        for task in candidates:
            info = self.media_info_cache.get(task.path) or task.probe_data
            if not info or not info.duration:
                continue
            minimum = self.ffmpeg_service.minimum_target_size_mb(settings, info)
            duration = self.ffmpeg_service.target_duration(settings, info)
            if not duration:
                continue
            audio = self.ffmpeg_service.target_audio_budget_kbps(settings, info)
            video = max(0, int(target_size_bytes(settings.target_size_mb) * 8 * 0.94 / 1000 / duration - audio))
            width, height = settings.resize_w or info.width or 1920, settings.resize_h or info.height or 1080
            scale = min(1.0, 640 / max(width, height))
            estimates.append(
                {
                    "path": str(task.path),
                    "video_kbps": video,
                    "audio_kbps": audio,
                    "minimum_mb": math.ceil(minimum * 100) / 100,
                    "low_bitrate": video < width * height * (info.fps or 30) * 0.035 / 1000,
                    "suggested_width": max(2, int(width * scale) // 2 * 2),
                    "suggested_height": max(2, int(height * scale) // 2 * 2),
                }
            )
        if not estimates:
            return {"pending": True}
        selected = next(
            (entry for entry in estimates if entry["path"] == self._selected_path), min(estimates, key=lambda entry: entry["video_kbps"])
        )
        return {**selected, "count": len(estimates), "minimum_mb": max(entry["minimum_mb"] for entry in estimates)}

    @QtCore.Slot("QVariantMap", result="QVariantMap")
    def validateSettings(self, settings_map: Dict[str, Any]) -> Dict[str, Any]:
        result = self.validation.validate(
            dict(settings_map),
            tasks=self.queue_model.items(),
            output_dir=self.outputDir,
            ffmpeg_path=self.ffmpegPath,
            include_queue=False,
            require_output_dir=False,
        )
        return self._apply_license_preflight(dict(result), dict(settings_map))

    def _refresh_output_preview(self, settings_map: Dict[str, Any]) -> None:
        summary = self.preview_builder.build(
            settings_map,
            tasks=self.queue_model.items(),
            output_dir=self.outputDir,
            selected_path=self._selected_path,
            media_info=self.media_info_cache,
        )
        for item in summary.items:
            self.queue_model.set_preview_output(item.source_path, str(item.output_path))
        self._refresh_size_predictions(settings_map)
        self._refresh_smart_recommendations(settings_map)
        self._set_output_preview(summary.text)
        self._set_selected_preview(summary.selected_source, summary.selected_output, summary.selected_command)

    def _refresh_size_predictions(self, settings_map: Dict[str, Any]) -> None:
        for task in self.queue_model.items():
            merged_map = merge_settings_maps(settings_map, task.overrides)
            settings = settings_map_to_model(merged_map, defaults=ConversionSettings())
            info = self.media_info_cache.get(task.path) or task.probe_data
            input_bytes = int((info.size_bytes if info else None) or task.input_bytes or 0)
            if not input_bytes:
                try:
                    input_bytes = task.path.stat().st_size
                except Exception:
                    input_bytes = 0
            if settings.target_size_mb:
                predicted = target_size_bytes(settings.target_size_mb)
            else:
                predicted = int(input_bytes * prediction_factor(settings.performance_profile)) if input_bytes else 0
            self.queue_model.set_prediction(task.path, predicted)

    @QtCore.Slot("QVariantMap")
    def refreshOutputPreview(self, settings_map: Dict[str, Any]) -> None:
        self._last_settings_map = dict(settings_map)
        self._refresh_output_preview(dict(settings_map))
        self._save_state()

    def _rename_preview_rows(self, settings_map: Dict[str, Any]) -> List[Dict[str, str]]:
        summary = self.preview_builder.build(
            dict(settings_map),
            tasks=self.queue_model.items(),
            output_dir=self.outputDir,
            selected_path=self._selected_path,
            media_info=self.media_info_cache,
            max_lines=100000,
        )
        return [
            {
                "source": str(item.source_path),
                "output": str(item.output_path),
                "operation": str(item.operation),
                "warnings": "; ".join(item.warnings),
            }
            for item in summary.items
        ]

    @QtCore.Slot("QVariantMap", result="QVariantList")
    def renamePreviewRows(self, settings_map: Dict[str, Any]) -> List[Dict[str, str]]:
        return self._rename_preview_rows(dict(settings_map))

    @QtCore.Slot("QVariantMap")
    def copyRenamePreview(self, settings_map: Dict[str, Any]) -> None:
        rows = self._rename_preview_rows(dict(settings_map))
        if not rows:
            return
        lines = ["source\toutput\toperation\twarnings"]
        lines.extend(f"{row['source']}\t{row['output']}\t{row['operation']}\t{row['warnings']}" for row in rows)
        QtWidgets.QApplication.clipboard().setText("\n".join(lines))
        self._append_log("OK", f"Rename preview copied: {len(rows)} row(s)")

    @QtCore.Slot("QVariantMap")
    def exportRenamePreviewCsv(self, settings_map: Dict[str, Any]) -> None:
        rows = self._rename_preview_rows(dict(settings_map))
        if not rows:
            QtWidgets.QMessageBox.information(None, "Rename preview", "Queue is empty.")
            return
        default_path = Path(self.outputDir or str(Path.home())).expanduser() / "rename-preview.csv"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Export rename preview", str(default_path), "CSV (*.csv)")
        if not path:
            return
        with Path(path).open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["source", "output", "operation", "warnings"])
            writer.writeheader()
            writer.writerows(rows)
        self._append_log("OK", f"Rename preview exported: {path}")

    @QtCore.Slot()
    def restoreSession(self) -> None:
        if self.queue_model.rowCount() > 0:
            self._append_log("INFO", f"Відновлено чергу: {self.queue_model.rowCount()} елементів.")
        if self.settings_manager.state.get("pending_recovery"):
            self._append_log("WARN", "Попередній запуск завершився аварійно; активні задачі повернено у чергу.")
            # Interrupted work was converted back to queued tasks in __init__.
            # Persist that recovery so the next normal launch is not flagged as a crash.
            self._save_state(pending_recovery=False)
        if self._last_settings_map:
            self.presetLoaded.emit(dict(self._last_settings_map))
            self._refresh_output_preview(dict(self._last_settings_map))

    @QtCore.Slot("QVariantMap")
    def exportProject(self, settings_map: Dict[str, Any]) -> None:
        default_path = Path(self.outputDir).expanduser() / "media-converter-project.json"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Експортувати проєкт", str(default_path), "JSON (*.json)")
        if not path:
            return
        payload = {
            "version": 2,
            "exported_at": time.time(),
            "output_dir": self.outputDir,
            "ffmpeg_path": self.ffmpegPath,
            "settings": dict(settings_map),
            "queue_items": [self.queue_manager.serialize_task(item) for item in self.queue_model.items()],
        }
        save_json_file(Path(path), payload)
        self._append_log("OK", f"Проєкт збережено: {path}")

    @QtCore.Slot()
    def importProject(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Імпортувати проєкт", "", "JSON (*.json)")
        if not path:
            return
        payload = load_json_file(Path(path))
        if not isinstance(payload, dict):
            QtWidgets.QMessageBox.warning(None, "Проєкт", "Некоректний JSON проєкту.")
            return
        queue_items = self.queue_manager.deserialize_tasks(payload.get("queue_items", []), pending_recovery=False)
        self.queue_model.set_items(queue_items)
        self._notify_queue_stats()
        self._last_settings_map = dict(payload.get("settings") or {})
        self.outputDir = str(payload.get("output_dir") or self.outputDir)
        imported_ffmpeg = str(payload.get("ffmpeg_path") or "").strip()
        if imported_ffmpeg:
            self.ffmpegPath = imported_ffmpeg
        self._save_state()
        if self._last_settings_map:
            self.presetLoaded.emit(dict(self._last_settings_map))
            self._refresh_output_preview(dict(self._last_settings_map))
        self._append_log("OK", f"Проєкт імпортовано: {path}")

    @QtCore.Slot("QVariantMap")
    def exportCommandScript(self, settings_map: Dict[str, Any]) -> None:
        self._refresh_output_preview(dict(settings_map))
        command = self._selected_preview_command
        if not command or command == "—":
            QtWidgets.QMessageBox.information(None, "FFmpeg command", "Немає команди для експорту.")
            return
        suffix = ".bat" if os.name == "nt" else ".sh"
        default_path = Path(self.outputDir).expanduser() / f"ffmpeg-command{suffix}"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Експорт команди", str(default_path), f"Script (*{suffix});;All Files (*)")
        if not path:
            return
        content = f"@echo off\r\n{command}\r\n" if os.name == "nt" else f"#!/usr/bin/env sh\n{command}\n"
        Path(path).write_text(content, encoding="utf-8")
        self._append_log("OK", f"Команду експортовано: {path}")

    @QtCore.Slot("QVariantMap")
    def copyDryRunCommand(self, settings_map: Dict[str, Any]) -> None:
        self._refresh_output_preview(dict(settings_map))
        if self._selected_preview_command and self._selected_preview_command != "—":
            QtWidgets.QApplication.clipboard().setText(self._selected_preview_command)
            self._append_log("OK", "Dry-run команду скопійовано.")

    @QtCore.Slot()
    def clearHistory(self) -> None:
        self.history_store.clear()
        self.history_model.set_entries(self.history_store.entries)
        self.historyChanged.emit()
        self._append_log("INFO", "Історію запусків очищено.")

    @QtCore.Slot(str)
    def exportHistoryReport(self, fmt: str) -> None:
        clean_fmt = str(fmt or "csv").strip().lower()
        if clean_fmt not in {"csv", "json", "html"}:
            clean_fmt = "csv"
        if clean_fmt in {"json", "html"} and not self._require_pro_feature("advanced_reports", "Advanced reports"):
            return
        if not self.history_store.entries:
            QtWidgets.QMessageBox.information(None, "Report", "Історія запусків порожня.")
            return
        latest = self.history_store.entries[0]
        default_path = Path(self.outputDir or str(Path.home())).expanduser() / f"conversion-report.{clean_fmt}"
        filter_map = {
            "csv": "CSV (*.csv)",
            "json": "JSON (*.json)",
            "html": "HTML (*.html)",
        }
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Експорт звіту", str(default_path), filter_map[clean_fmt])
        if not path:
            return
        ReportService.export_file(
            Path(path),
            list(latest.get("results") or []),
            fmt=clean_fmt,
            settings=dict(latest.get("settings") or {}),
            output_dir=str(latest.get("output_dir") or ""),
            started_at=latest.get("started_at"),
        )
        self._append_log("OK", f"Звіт експортовано: {path}")

    @QtCore.Slot(int)
    def openHistoryOutput(self, index: int) -> None:
        entry = self.history_model.entry_at(index)
        if not entry:
            return
        folder = Path(str(entry.get("output_dir") or "")).expanduser()
        if folder.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(folder)))

    @QtCore.Slot(int)
    def loadHistorySettings(self, index: int) -> None:
        entry = self.history_model.entry_at(index)
        if not entry:
            return
        settings = dict(entry.get("settings") or {})
        if not settings:
            self._append_log("WARN", "У цьому запуску немає збережених налаштувань.")
            return
        self._last_settings_map = settings
        self.presetLoaded.emit(settings)
        self._refresh_output_preview(settings)
        self._append_log("OK", "Налаштування запуску завантажено з історії.")

    @QtCore.Slot(int)
    def rerunHistory(self, index: int) -> None:
        entry = self.history_model.entry_at(index)
        if not entry:
            return
        settings = dict(entry.get("settings") or {})
        paths = [Path(str(result.get("path"))) for result in entry.get("results", []) if result.get("path")]
        if paths:
            self._add_paths(paths)
        self._start_conversion(settings, only_paths={path.expanduser() for path in paths})

    @QtCore.Slot(str, result="QVariantMap")
    def getMontageSession(self, path_text: str) -> Dict[str, Any]:
        path = Path(str(path_text or "").strip()).expanduser()
        index = self.queue_model.index_for_path(path)
        task = self.queue_model.item_at(index) if index >= 0 else None
        overrides = dict(task.overrides) if task else None
        return self.montage_service.get_session(path, existing_overrides=overrides)

    @QtCore.Slot(str, result=str)
    def requestMontageWaveform(self, path_text: str) -> str:
        path = Path(str(path_text or "").strip()).expanduser()

        def _bg() -> None:
            wf = self.montage_service.get_audio_waveform(path)
            self.montageWaveformReady.emit(str(path), wf)

        threading.Thread(target=_bg, daemon=True).start()
        return ""

    @QtCore.Slot(str, "QVariantMap")
    def saveMontageSession(self, path_text: str, session_map: Dict[str, Any]) -> None:
        path = Path(str(path_text or "").strip()).expanduser()
        self.montage_service.save_session(path, session_map)
        self.montageSessionUpdated.emit(str(path))

    @QtCore.Slot(str, "QVariantMap")
    def applyMontageToTask(self, path_text: str, session_map: Dict[str, Any]) -> None:
        path = Path(str(path_text or "").strip()).expanduser()
        data = dict(session_map or {})
        self.montage_service.save_session(path, data)

        in_pt = float(data.get("in_point", 0.0) or 0.0)
        out_pt = float(data.get("out_point", 0.0) or 0.0)
        crop_x = data.get("crop_x")
        crop_y = data.get("crop_y")
        crop_w = data.get("crop_w")
        crop_h = data.get("crop_h")
        audio_enabled = bool(data.get("audio_enabled", True))
        out_format = str(data.get("output_format") or "").strip().lower()

        overrides: Dict[str, Any] = {
            "trim_start": in_pt if in_pt > 0 else None,
            "trim_end": out_pt if out_pt > 0 else None,
            "crop_x": int(crop_x) if crop_x is not None else None,
            "crop_y": int(crop_y) if crop_y is not None else None,
            "crop_w": int(crop_w) if crop_w is not None else None,
            "crop_h": int(crop_h) if crop_h is not None else None,
            "remove_audio": not audio_enabled,
        }
        has_crop = any(v is not None for v in (overrides["crop_x"], overrides["crop_y"], overrides["crop_w"], overrides["crop_h"]))
        if has_crop:
            overrides["fast_copy"] = False
        if out_format:
            overrides["out_video_format"] = out_format

        self.updateTaskOverrideByPath(str(path), overrides)
        self.montageSessionUpdated.emit(str(path))

    @QtCore.Slot(str, int, result=str)
    def requestMontageProxy(self, path_text: str, target_height: int = 720) -> str:
        path = Path(str(path_text or "").strip()).expanduser()

        def _bg() -> None:
            proxy_path = self.montage_service.create_or_get_proxy(path, target_height=target_height)
            self.montageProxyReady.emit(str(path), proxy_path)

        threading.Thread(target=_bg, daemon=True).start()
        return self.montage_service.get_proxy_path(path, target_height=target_height)

    @QtCore.Slot(str, int, result=bool)
    def isMontageProxyReady(self, path_text: str, target_height: int = 720) -> bool:
        path = Path(str(path_text or "").strip()).expanduser()
        return self.montage_service.is_proxy_ready(path, target_height=target_height)

    @QtCore.Slot(str, int, result=str)
    def getMontageProxyPath(self, path_text: str, target_height: int = 720) -> str:
        path = Path(str(path_text or "").strip()).expanduser()
        return self.montage_service.get_proxy_path(path, target_height=target_height)

    @QtCore.Slot(str, result="QVariantMap")
    def getTimelineProject(self, path_text: str) -> Dict[str, Any]:
        path = Path(str(path_text or "").strip()).expanduser()
        return self.montage_service.get_timeline_project(path)

    @QtCore.Slot(str, "QVariantMap")
    def saveTimelineProject(self, path_text: str, project_map: Dict[str, Any]) -> None:
        path = Path(str(path_text or "").strip()).expanduser()
        self.montage_service.save_timeline_project(path, dict(project_map or {}))
        self.montageSessionUpdated.emit(str(path))

    @QtCore.Slot("QVariantMap", str, bool, result=bool)
    def renderTimelineProject(self, project_map: Dict[str, Any], output_path: str, prefer_proxy: bool = False) -> bool:
        out_p = Path(str(output_path or "").strip()).expanduser()

        def _bg() -> None:
            ok = self.montage_service.render_timeline(dict(project_map or {}), out_p, prefer_proxy=prefer_proxy)
            self.montageTimelineRendered.emit(str(out_p), ok)

        threading.Thread(target=_bg, daemon=True).start()
        return True

    @QtCore.Slot(str, "QVariantList", int, str, result="QVariantMap")
    def diarizeMedia(self, path_text: str, segments: list, num_speakers: int = 2, language: str = "uk") -> Dict[str, Any]:
        path = Path(str(path_text or "").strip()).expanduser()
        seg_list = [dict(s) for s in (segments or [])]
        return self.montage_service.diarize_media(path, seg_list, num_speakers=num_speakers, language=language)

    @QtCore.Slot("QVariantMap", "QVariantMap", result="QVariantMap")
    def applySpeakerAliases(self, diarization_map: Dict[str, Any], aliases_map: Dict[str, str]) -> Dict[str, Any]:
        return self.montage_service.apply_speaker_aliases(dict(diarization_map or {}), dict(aliases_map or {}))

    @QtCore.Slot("QVariantMap", str, str, result=str)
    def exportDiarizedSubtitles(self, diarization_map: Dict[str, Any], output_path: str, format_name: str = "srt") -> str:
        out_p = Path(str(output_path or "").strip()).expanduser()
        return self.montage_service.export_diarized_subtitles(dict(diarization_map or {}), out_p, format_name=format_name)

    @QtCore.Slot("QVariantList", str, str, int, int, result=str)
    def generateStyledSubtitles(
        self,
        segments: list,
        template_name: str = "tiktok_pop",
        output_path: str = "",
        res_x: int = 1080,
        res_y: int = 1920,
    ) -> str:
        seg_list = [dict(s) for s in (segments or [])]
        out_p = Path(str(output_path or "").strip()).expanduser() if output_path else ""
        return self.montage_service.generate_styled_subtitles(seg_list, template=template_name, output_path=out_p, res_x=res_x, res_y=res_y)

    @QtCore.Slot("QVariantList", "QStringList", str, result="QVariantMap")
    def translateSubtitles(self, segments: list, target_languages: list, source_lang: str = "auto") -> Dict[str, Any]:
        seg_list = [dict(s) for s in (segments or [])]
        langs = [str(language) for language in (target_languages or [])]
        return self.montage_service.translate_subtitles(seg_list, target_languages=langs, source_lang=source_lang)

    @QtCore.Slot(str, str, result="QVariantMap")
    def calculateSmartReframe(self, path_text: str, aspect: str = "9:16") -> Dict[str, Any]:
        path = Path(str(path_text or "").strip()).expanduser()
        return self.montage_service.calculate_smart_reframe(path, aspect=aspect)

    @QtCore.Slot(str, str, "QVariantList", str, result="QVariantMap")
    def trackAndBlurObject(
        self,
        path_text: str,
        target_type: str = "face",
        initial_bbox: list | None = None,
        blur_style: str = "box",
    ) -> Dict[str, Any]:
        path = Path(str(path_text or "").strip()).expanduser()
        bbox = [int(x) for x in initial_bbox] if initial_bbox and len(initial_bbox) == 4 else None
        return self.montage_service.track_and_blur(path, target_type=target_type, initial_bbox=bbox, blur_style=blur_style)
