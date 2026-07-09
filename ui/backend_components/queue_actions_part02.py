from __future__ import annotations

BODY = r'''    @QtCore.Slot()
    def exportLog(self) -> None:
        default_path = Path(self.outputDir).expanduser() / "media-converter-log.txt"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Експортувати лог", str(default_path), "Text (*.txt)")
        if path:
            Path(path).write_text("\n".join(self._log_lines), encoding="utf-8")
            self._append_log("OK", f"Лог збережено: {path}")

    @QtCore.Slot()
    def pickWatchFolder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(None, "Watch folder", self.watchFolder or "")
        if folder:
            self.watchFolder = folder

    @QtCore.Slot()
    def startWatching(self) -> None:
        folder = Path(self.watchFolder).expanduser()
        if not self.watchFolder or not folder.exists():
            QtWidgets.QMessageBox.warning(None, "Watch folder", "Обери існуючу папку для моніторингу.")
            return
        try:
            self.watch_service.start(folder)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(None, "Watch folder", str(exc))
            return
        self._watch_seen = set()
        self._watch_running = True
        self.watchRunningChanged.emit()
        self._append_log("OK", f"Watch folder активовано: {folder}")

    @QtCore.Slot()
    def stopWatching(self) -> None:
        self.watch_service.stop()
        self._watch_running = False
        self.watchRunningChanged.emit()
        self._watch_timer.stop()
        self._append_log("INFO", "Watch folder зупинено")

    def _on_watch_files(self, paths: List[Path]) -> None:
        folder = self.watch_service.folder
        self.event_queue.put(("watch_paths", list(paths), str(folder) if folder else ""))
        self.event_queue.put(("log", "INFO", f"Watch folder додав файлів: {len(paths)}"))

    def _scan_watch_folder(self) -> None:
        if not self._watch_running or not self.watchFolder:
            return
        base = Path(self.watchFolder).expanduser()
        if not base.exists():
            self.stopWatching()
            return
        new_paths = self.watch_service.scan_once()
        if new_paths:
            self._handle_watch_paths(new_paths, str(base))
            self._append_log("INFO", f"Watch folder додав файлів: {len(new_paths)}")

    def _handle_watch_paths(self, paths: List[Path], remember_folder: str = "") -> None:
        if remember_folder:
            self._remember_folder(remember_folder)
        added = self._add_paths(paths, apply_watch_rules=True)
        if added:
            self.sortQueueByPriority()
            self._maybe_auto_convert_watch_items(added)

    def _maybe_auto_convert_watch_items(self, items: List[TaskItem]) -> None:
        if not self._watch_auto_convert_enabled or self._is_running or self.runner.is_running:
            return
        if not self._output_dir_configured or not self.outputDir:
            self._append_log("WARN", "Watch auto-convert skipped: output folder is not configured.")
            return
        paths = {item.path for item in items if item.status in {TaskStatus.QUEUED, TaskStatus.READY}}
        if not paths:
            return
        self._append_log("INFO", f"Watch auto-convert starting: {len(paths)} file(s)")
        self._start_conversion(dict(self._last_settings_map), only_paths=paths)

    def _runnable_queue_paths(self) -> set[Path]:
        runnable = {TaskStatus.QUEUED, TaskStatus.READY, TaskStatus.FAILED, TaskStatus.CANCELLED}
        return {item.path for item in self.queue_model.items() if item.status in runnable}

    def _check_scheduler(self) -> None:
        if not self._scheduler_enabled or self._is_running or self.runner.is_running:
            return
        paths = self._runnable_queue_paths()
        if not paths:
            return
        if not self._output_dir_configured or not self.outputDir:
            return
        now = time.localtime()
        if not self._scheduler_due(now):
            return
        key = self._scheduler_start_key(now)
        if key and key == self._scheduler_last_start_key:
            return
        self._scheduler_last_start_key = key
        self._append_log("INFO", f"Scheduler starting queue: mode={self._scheduler_mode}, files={len(paths)}")
        self._start_conversion(dict(self._last_settings_map), only_paths=paths)

    def _scheduler_due(self, now: time.struct_time) -> bool:
        mode = str(self._scheduler_mode or "time").strip().lower()
        time_due = self._scheduler_time_due(now)
        idle_due = self._scheduler_idle_due()
        if mode == "idle":
            return idle_due
        if mode == "time_or_idle":
            return time_due or idle_due
        if mode == "time_and_idle":
            return time_due and idle_due
        return time_due

    def _scheduler_time_due(self, now: time.struct_time) -> bool:
        match = re.match(r"^(\d{1,2}):(\d{2})$", str(self._scheduler_time or "").strip())
        if not match:
            return False
        target_minutes = max(0, min(23, int(match.group(1)))) * 60 + max(0, min(59, int(match.group(2))))
        current_minutes = now.tm_hour * 60 + now.tm_min
        return current_minutes >= target_minutes

    def _scheduler_idle_due(self) -> bool:
        sample = self._sample_resources()
        cpu_ok = sample.get("cpu", 0.0) <= max(1, min(100, self._scheduler_cpu_limit))
        gpu_value = sample.get("gpu", 0.0)
        gpu_ok = gpu_value <= 0.0 or gpu_value <= max(1, min(100, self._scheduler_gpu_limit))
        return cpu_ok and gpu_ok

    def _scheduler_start_key(self, now: time.struct_time) -> str:
        if str(self._scheduler_mode or "").strip().lower() == "idle":
            return f"{time.strftime('%Y-%m-%d %H:%M', now)} idle"
        return f"{time.strftime('%Y-%m-%d', now)} {self._scheduler_time}"

    def _batch_completion_summary(self, stopped: bool) -> Dict[str, Any]:
        return {
            "completed": self.completedCount,
            "failed": self.failedCount,
            "skipped": self.skippedCount,
            "cancelled": self.cancelledCount,
            "stopped": bool(stopped),
            "output_dir": self.outputDir,
        }

    def _handle_batch_completion(self, stopped: bool) -> None:
        summary = self._batch_completion_summary(stopped)
        self._send_http_notifications(summary)
        if not stopped:
            self._run_completion_action()

    def _send_http_notifications(self, summary: Dict[str, Any]) -> None:
        if not self._webhook_enabled:
            return
        if not any([self._webhook_url.strip(), self._discord_webhook_url.strip(), self._telegram_bot_token.strip() and self._telegram_chat_id.strip()]):
            return
        title = "Media Converter batch finished"
        message = (
            f"Done: {summary.get('completed', 0)}, failed: {summary.get('failed', 0)}, "
            f"skipped: {summary.get('skipped', 0)}, cancelled: {summary.get('cancelled', 0)}"
        )
        threading.Thread(
            target=self._send_http_notifications_async,
            args=(title, message, summary),
            daemon=True,
        ).start()

    def _send_http_notifications_async(self, title: str, message: str, summary: Dict[str, Any]) -> None:
        results = self.notification_service.send_batch_done(
            title=title,
            message=message,
            summary=summary,
            webhook_url=self._webhook_url,
            discord_webhook_url=self._discord_webhook_url,
            telegram_bot_token=self._telegram_bot_token,
            telegram_chat_id=self._telegram_chat_id,
        )
        for result in results:
            level = "OK" if result.ok else "WARN"
            self.event_queue.put(("log", level, f"Notification {result.target}: {result.message}"))

    def _run_completion_action(self) -> None:
        action = str(self._completion_action or "none").strip().lower()
        if action == "none":
            return
        if action == "open_output":
            self.openOutputDir()
            return
        if action not in {"sleep", "shutdown"}:
            return
        try:
            if action == "sleep":
                cmd = ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"] if os.name == "nt" else ["systemctl", "suspend"]
            else:
                cmd = ["shutdown", "/s", "/t", "30", "/c", "Media Converter batch finished"] if os.name == "nt" else ["shutdown", "-h", "+1"]
            kwargs: Dict[str, Any] = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
            if os.name == "nt":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            subprocess.Popen(cmd, **kwargs)
            self._append_log("INFO", f"Completion action started: {action}")
        except Exception as exc:
            self._append_log("WARN", f"Completion action failed ({action}): {exc}")

    @QtCore.Slot(int)
    def selectQueueIndex(self, index: int) -> None:
        self._selected_index = index
        task = self.queue_model.item_at(index)
        if task is None:
            self._selected_path = ""
            self._clear_info()
            self._set_selected_preview("—", "—")
            self.taskOverrideLoaded.emit({})
            return
        self._selected_path = str(task.path)
        self._info_name = task.path.name
        self._info_duration = "--:--"
        self._info_codec = "—"
        self._info_res = "—"
        self._info_size = task.size_text or "—"
        self._info_container = "—"
        self._info_analysis = f"Тип: {task.media_type}"
        self._info_warnings = task.last_error or "—"
        self.infoChanged.emit()
        self.taskOverrideLoaded.emit(dict(task.overrides))
        self._refresh_output_preview(dict(self._last_settings_map))
        info = self.media_info_cache.get(task.path)
        if info:
            self._update_info(info)
            return
        if self.ffmpeg_service.ffprobe_path and task.media_type in {"video", "audio"}:
            self.queue_model.update_task_state(task.path, TaskStatus.ANALYZING)
            self._notify_queue_stats()
            threading.Thread(target=self._probe_media_async, args=(task.path,), daemon=True).start()
        self._ensure_thumbnail_async(task.path, task.media_type)

    @QtCore.Slot(str)
    def selectQueuePath(self, path_text: str) -> None:
        self.selectQueueIndex(self.queue_model.index_for_path(Path(str(path_text or "").strip()).expanduser()))

    @QtCore.Slot(int, result=str)
    def queuePathAt(self, index: int) -> str:
        task = self.queue_model.item_at(index)
        return str(task.path) if task else ""
'''
