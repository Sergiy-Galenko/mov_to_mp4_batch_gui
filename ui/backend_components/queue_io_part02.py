from __future__ import annotations

BODY = r'''            self._save_state()
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
            paid_auto_update_enabled=self._paid_auto_update_enabled,
            paid_update_manifest_url=self._paid_update_manifest_url,
        )

    def _append_log(self, level: str, msg: str) -> None:
        self._log_lines.append(f"{level}: {msg}")
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
        input_bytes = 0
        output_bytes = 0
        for item in self.queue_model.items():
            try:
                if item.path.exists():
                    input_bytes += item.path.stat().st_size
            except Exception:
                pass
            output_text = (item.last_output or "").split(";", 1)[0].strip()
            if not output_text:
                continue
            try:
                output_path = Path(output_text).expanduser()
                if output_path.exists():
                    output_bytes += output_path.stat().st_size
'''
