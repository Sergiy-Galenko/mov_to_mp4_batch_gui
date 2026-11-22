from __future__ import annotations

from .common import (
    RECENT_FOLDERS_LIMIT,
    Dict,
    List,
    LogModel,
    Optional,
    Path,
    QtCore,
    QtWidgets,
    format_bytes,
    format_time,
    load_json_file,
    save_json_file,
    threading,
    time,
)
from .core import CoreMixin


class QueueIoMixin:
    @QtCore.Property(str, notify=CoreMixin.queueStatsChanged)
    def folderTypeFilter(self) -> str:
        return self._folder_type_filter

    @folderTypeFilter.setter
    def folderTypeFilter(self, value: str) -> None:
        self._folder_type_filter = str(value or "").strip()
        self.folder_scanner.type_filter = self._folder_type_filter if self._folder_type_filter else None

    @QtCore.Property(str, notify=CoreMixin.queueStatsChanged)
    def folderExcludePatterns(self) -> str:
        return self._folder_exclude_patterns

    @folderExcludePatterns.setter
    def folderExcludePatterns(self, value: str) -> None:
        self._folder_exclude_patterns = str(value or "").strip()
        if self._folder_exclude_patterns:
            patterns = {p.strip() for p in self._folder_exclude_patterns.split(",") if p.strip()}
            self.folder_scanner.exclude_patterns = patterns
        else:
            from services.folder_scanner import _DEFAULT_EXCLUDES

            self.folder_scanner.exclude_patterns = set(_DEFAULT_EXCLUDES)

    @QtCore.Slot()
    def addFolderFiltered(self) -> None:
        """Add folder with current type filter and exclude patterns."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(None, "Додати папку (з фільтрами)")
        if not folder:
            return
        base = Path(folder)
        self._append_log("INFO", f"Сканую папку з фільтрами: {base}")
        threading.Thread(
            target=self._collect_folder_filtered_async,
            args=(base,),
            daemon=True,
        ).start()

    def _collect_folder_filtered_async(self, folder: Path) -> None:
        try:
            stats = self.folder_scanner.scan_with_stats(folder)
            files = stats["files"]
            excluded = stats["excluded"]
            type_filtered = stats["type_filtered"]
        except Exception as exc:
            self.event_queue.put(("log", "ERROR", f"Не вдалося просканувати папку {folder}: {exc}"))
            return
        self.event_queue.put(("add_paths", files, str(folder)))
        if excluded or type_filtered:
            self.event_queue.put(
                ("log", "INFO", f"Скановано: {stats['total_scanned']} файлів, виключено: {excluded}, по типу: {type_filtered}")
            )

    # --- Clipboard paste ---

    @QtCore.Slot()
    def pasteFromClipboard(self) -> None:
        """Add files/URLs from clipboard text."""
        clipboard = QtWidgets.QApplication.clipboard()
        text = clipboard.text() or ""
        if not text.strip():
            self._append_log("INFO", "Буфер обміну порожній.")
            return

        paths: List[Path] = []
        urls: List[str] = []
        for line in text.strip().splitlines():
            line = line.strip().strip('"').strip("'")
            if not line:
                continue
            if line.startswith(("http://", "https://")):
                urls.append(line)
            else:
                path = Path(line)
                if path.exists():
                    paths.append(path)

        if paths:
            self._add_paths(paths)
            self._append_log("OK", f"Додано з буферу: {len(paths)} файлів")
        if urls:
            self._append_log("INFO", f"URL з буферу: {len(urls)} (відкрий Downloads для завантаження)")
        if not paths and not urls:
            self._append_log("WARN", "Не знайдено дійсних шляхів або URL у буфері обміну.")

    # --- Queue save / load ---

    @QtCore.Slot()
    def saveQueueToFile(self) -> None:
        """Save current queue to a JSON file."""
        default_path = Path(self.outputDir).expanduser() / "queue-export.json"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Зберегти чергу", str(default_path), "JSON (*.json)")
        if not path:
            return
        payload = {
            "version": 1,
            "type": "queue",
            "items": [self.queue_manager.serialize_task(item) for item in self.queue_model.items()],
        }
        save_json_file(Path(path), payload)
        self._append_log("OK", f"Чергу збережено: {path}")

    @QtCore.Slot()
    def loadQueueFromFile(self) -> None:
        """Load queue from a JSON file (appends to existing queue)."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Завантажити чергу", "", "JSON (*.json)")
        if not path:
            return
        payload = load_json_file(Path(path))
        if not isinstance(payload, dict) or payload.get("type") != "queue":
            QtWidgets.QMessageBox.warning(None, "Черга", "Некоректний файл черги.")
            return
        items = self.queue_manager.deserialize_tasks(payload.get("items", []), pending_recovery=False)
        if items:
            self.queue_model.add_items(items)
            self._notify_queue_stats()
            self._refresh_output_preview(dict(self._last_settings_map))
            self._save_state()
            self._append_log("OK", f"Завантажено з файлу: {len(items)} елементів")
        else:
            self._append_log("WARN", "Файл черги порожній.")

    # --- Media preview ---

    @QtCore.Slot(str, str)
    def generateMediaPreview(self, path_text: str, media_kind: str) -> None:
        """Generate preview (thumbnails/waveform) for a media file in background."""
        path = Path(str(path_text or "").strip())
        if not path.exists():
            return
        threading.Thread(
            target=self._generate_preview_async,
            args=(path, media_kind),
            daemon=True,
        ).start()

    def _generate_preview_async(self, path: Path, media_kind: str) -> None:
        self.media_preview.ffmpeg_path = self.ffmpeg_service.ffmpeg_path or ""
        self.media_preview.ffprobe_path = self.ffmpeg_service.ffprobe_path or ""
        preview_data = self.media_preview.generate_preview(path, media_kind)
        self.event_queue.put(("preview_generated", str(path), preview_data))

    def _save_state(self, *, pending_recovery: Optional[bool] = None) -> None:
        self._state_save_timer.stop()
        self.settings_manager.save(
            recent_folders=self._recent_folders[:RECENT_FOLDERS_LIMIT],
            watch_folder=self._watch_folder,
            output_dir=self._output_dir,
            output_dir_configured=self._output_dir_configured,
            ffmpeg_path=self._ffmpeg_path,
            ui_language=self._ui_language,
            last_settings=self._last_settings_map,
            queue_items=[self.queue_manager.serialize_task(item) for item in self.queue_model.items()],
            pending_recovery=self._is_running if pending_recovery is None else pending_recovery,
            onboarding_completed=True,
            youtube_history=list(self._youtube_history),
            youtube_cookies_path=self._youtube_cookies_path,
            tray_enabled=self._tray_enabled,
            push_notifications_enabled=self._push_notifications_enabled,
            watch_auto_convert_enabled=self._watch_auto_convert_enabled,
            watch_rules_text=self._watch_rules_text,
            scheduler_enabled=self._scheduler_enabled,
            scheduler_mode=self._scheduler_mode,
            scheduler_time=self._scheduler_time,
            scheduler_cpu_limit=self._scheduler_cpu_limit,
            scheduler_gpu_limit=self._scheduler_gpu_limit,
            completion_action=self._completion_action,
            webhook_enabled=self._webhook_enabled,
            webhook_url=self._webhook_url,
            discord_webhook_url=self._discord_webhook_url,
            telegram_bot_token=self._telegram_bot_token,
            telegram_chat_id=self._telegram_chat_id,
            license_payload=self._license_payload,
            trial_started_at=self._trial_started_at,
            trial_signature=self._trial_signature,
            paid_auto_update_enabled=self._paid_auto_update_enabled,
            paid_update_manifest_url=self._paid_update_manifest_url,
        )

    def _append_log(self, level: str, msg: str) -> None:
        self._log_lines.append(f"{level}: {msg}")
        del self._log_lines[: -LogModel.MAX_ENTRIES]
        self.log_model.append(level, msg)
        self.logAdded.emit(level, msg)
        if str(level).upper() == "ERROR":
            self._last_error_title = "Помилка виконання"
            self._last_error_details = str(msg or "").strip() or "Перевір повний FFmpeg лог."
            self._last_error_log = "\n".join(self._log_lines[-120:])
            self.errorStateChanged.emit()

    def _set_status(self, text: str) -> None:
        if self._status_text == text:
            return
        self._status_text = text
        self.statusChanged.emit()

    def _set_progress(self, file_pct: float, total_pct: float) -> None:
        if self._file_progress != file_pct:
            self._file_progress = file_pct
            self.fileProgressChanged.emit()
        if self._total_progress != total_pct:
            self._total_progress = total_pct
            self.totalProgressChanged.emit()

    def _refresh_presets(self) -> None:
        self.presets_model.setStringList(self.preset_manager.names())
        self.presetsChanged.emit()

    def _refresh_recent_folders(self) -> None:
        self.recent_folders_model.setStringList(self._recent_folders)
        self.recentFoldersChanged.emit()

    def _remember_folder(self, folder: str) -> None:
        self._recent_folders = self.settings_manager.remember_folder(self._recent_folders, folder)
        self._refresh_recent_folders()

    def _set_output_preview(self, text: str) -> None:
        if self._output_preview_text == text:
            return
        self._output_preview_text = text
        self.outputPreviewChanged.emit()

    def _set_selected_preview(self, source: str, output: str, command: str = "—") -> None:
        source_value = source or "—"
        output_value = output or "—"
        command_value = command or "—"
        if (
            self._selected_preview_source == source_value
            and self._selected_preview_output == output_value
            and self._selected_preview_command == command_value
        ):
            return
        self._selected_preview_source = source_value
        self._selected_preview_output = output_value
        self._selected_preview_command = command_value
        self.outputPreviewChanged.emit()

    def _notify_queue_stats(self) -> None:
        self.queueStatsChanged.emit()
        self._refresh_session_stats()

    def _refresh_session_stats(self, *, total_eta: Optional[float] = None) -> None:
        elapsed = time.monotonic() - self._run_started_monotonic if self._run_started_monotonic else 0.0
        now = time.monotonic()
        if total_eta is not None and total_eta != 0.0 and now - getattr(self, "_last_session_refresh", 0.0) < 0.25:
            return
        self._last_session_refresh = now
        items = self.queue_model.items()
        input_bytes = sum(item.input_bytes for item in items)
        output_bytes = sum(item.output_bytes for item in items)
        saved = max(input_bytes - output_bytes, 0)
        speeds = [point.get("speed", 0.0) for point in self._speed_history if point.get("speed", 0.0) > 0]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
        self._session_elapsed_text = format_time(elapsed)
        self._session_eta_text = format_time(total_eta) if total_eta is not None else self._session_eta_text
        self._session_avg_speed_text = f"{avg_speed:.1f}x" if avg_speed else "--"
        self._session_input_text = format_bytes(input_bytes)
        self._session_output_text = format_bytes(output_bytes)
        self._session_saved_text = format_bytes(saved)
        self.sessionStatsChanged.emit()

    def _refresh_codec_distribution(self) -> None:
        distribution: Dict[str, int] = {}
        for item in self.queue_model.items():
            info = self.media_info_cache.get(item.path) or item.probe_data
            codec = (info.vcodec if info else None) or "Unknown"
            codec = self._display_codec(codec)
            distribution[codec] = distribution.get(codec, 0) + 1
        self._codec_distribution = distribution
        self.codecDistributionChanged.emit(dict(self._codec_distribution))

    def _display_codec(self, codec: str) -> str:
        normalized = str(codec or "").lower()
        if normalized in {"h264", "libx264"}:
            return "H.264"
        if normalized in {"hevc", "h265", "libx265"}:
            return "H.265"
        if "av1" in normalized:
            return "AV1"
        if "vp9" in normalized:
            return "VP9"
        return codec or "Unknown"

    def _sample_resources(self) -> Dict[str, float | None]:
        return self._resource_monitor.sample()

    def _append_resource_sample(self, now: float) -> None:
        if not self._run_started_monotonic:
            return
        sample = self._sample_resources()
        sample["time"] = now - self._run_started_monotonic
        self._resource_history.append(sample)
        self._resource_history = self._resource_history[-120:]
        self._cpu_load_text = f"CPU {sample['cpu']:.0f}%" if sample["cpu"] is not None else "CPU —"
        self._gpu_load_text = f"GPU {sample['gpu']:.0f}%" if sample["gpu"] is not None else "GPU —"
        self._ram_load_text = f"RAM {sample['ram']:.0f}%" if sample["ram"] is not None else "RAM —"
        self.resourceHistoryChanged.emit(list(self._resource_history))

    def _record_file_timing(self, path: Path, status: str) -> None:
        started = self._task_started_at.pop(path, None)
        if started is None:
            return
        duration = max(time.monotonic() - started, 0.0)
        name = path.name
        item = self.queue_model.item_by_path(path)
        self._file_timings = [item for item in self._file_timings if item.get("name") != name]
        self._file_timings.append(
            {
                "name": name,
                "duration": duration,
                "status": status,
                "compression": item.compression_ratio if item else 0.0,
                "predictedSize": item.predicted_output_bytes if item else 0,
            }
        )
        self._file_timings.sort(key=lambda item: float(item.get("duration") or 0), reverse=True)
        self._file_timings = self._file_timings[:10]
        self.fileTimingsChanged.emit(list(self._file_timings))

    @QtCore.Slot()
    def exportDiagnostics(self) -> None:
        if self._diagnostic_job.busy:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, self._tr("system.export_report"), "diagnostics.json", "JSON (*.json)")
        if not path:
            return
        from services.diagnostic_service import export_report
        logs = list(self._log_lines)
        plans = list(self._converter_service.processing_plans) if self._converter_service else []
        def write(context):
            context.progress("report", 20)
            export_report(Path(path), self.ffmpeg_service, logs=logs, plans=plans, context=context)
            return {"saved": True}
        self._diagnostic_job.start_job(write)

    @QtCore.Slot()
    def clearMediaCache(self) -> None:
        from services.cache_manager import CacheManager
        if self._diagnostic_job.busy:
            return
        self._diagnostic_job.start_job(lambda context: {"cache_removed": CacheManager().cleanup(clear=True)})
