from __future__ import annotations

from .common import (
    Any,
    ConversionSettings,
    Dict,
    List,
    MediaInfo,
    Optional,
    Path,
    QtCore,
    QtWidgets,
    TaskItem,
    TaskStatus,
    merge_settings_maps,
    os,
    re,
    recommend_settings,
    settings_map_to_model,
    subprocess,
    threading,
    time,
)


class QueueActionsMixin:
    @QtCore.Slot()
    def deduplicateQueue(self) -> None:
        unique, removed = self.queue_manager.deduplicate_by_path(self.queue_model.items())
        self.queue_model.set_items(unique)
        self._notify_queue_stats()
        self._refresh_codec_distribution()
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()
        self._append_log("INFO", f"Видалено дублікатів: {removed}")

    @QtCore.Slot()
    def deduplicateQueueByHash(self) -> None:
        items = self.queue_model.items()
        if not items:
            return
        self._append_log("INFO", "Hash-дедуплікація запущена у фоні.")
        threading.Thread(target=self._deduplicate_hash_async, args=(items,), daemon=True).start()

    def _deduplicate_hash_async(self, items: List[TaskItem]) -> None:
        unique, removed, log_lines = self.queue_manager.deduplicate_by_hash(items)
        self.event_queue.put(("dedupe_hash_done", unique, removed, log_lines))

    def _move_selected(self, indices: List[int], direction: str) -> None:
        items = self.queue_manager.reorder(self.queue_model.items(), indices, direction)
        self.queue_model.set_items(items)
        self._selected_index = self.queue_model.index_for_path(Path(self._selected_path)) if self._selected_path else -1
        self._notify_queue_stats()
        self._refresh_codec_distribution()
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()

    def _move_selected_paths(self, paths: List[Any], direction: str) -> None:
        selected_paths = self.queue_manager.paths_from_payload(paths)
        indices = self.queue_manager.selected_indices_for_paths(self.queue_model.items(), selected_paths)
        self._move_selected(indices, direction)

    @QtCore.Slot("QVariantList")
    def moveSelectedUp(self, indices: List[int]) -> None:
        self._move_selected(indices, "up")

    @QtCore.Slot("QVariantList")
    def moveSelectedDown(self, indices: List[int]) -> None:
        self._move_selected(indices, "down")

    @QtCore.Slot("QVariantList")
    def moveSelectedTop(self, indices: List[int]) -> None:
        self._move_selected(indices, "top")

    @QtCore.Slot("QVariantList")
    def moveSelectedBottom(self, indices: List[int]) -> None:
        self._move_selected(indices, "bottom")

    @QtCore.Slot("QVariantList")
    def moveSelectedPathsUp(self, paths: List[Any]) -> None:
        self._move_selected_paths(paths, "up")

    @QtCore.Slot("QVariantList")
    def moveSelectedPathsDown(self, paths: List[Any]) -> None:
        self._move_selected_paths(paths, "down")

    @QtCore.Slot("QVariantList")
    def moveSelectedPathsTop(self, paths: List[Any]) -> None:
        self._move_selected_paths(paths, "top")

    @QtCore.Slot("QVariantList")
    def moveSelectedPathsBottom(self, paths: List[Any]) -> None:
        self._move_selected_paths(paths, "bottom")

    @QtCore.Slot(str, int)
    def movePathToIndex(self, path_text: str, target_index: int) -> None:
        items = self.queue_manager.move_path_to_index(
            self.queue_model.items(),
            Path(str(path_text or "").strip()).expanduser(),
            target_index,
        )
        self.queue_model.set_items(items)
        self._notify_queue_stats()
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()

    @QtCore.Slot("QVariantList")
    def removeSelected(self, indices: List[int]) -> None:
        items, removed = self.queue_manager.remove_indices(self.queue_model.items(), indices)
        self.queue_model.set_items(items)
        self._after_queue_removed(removed)

    @QtCore.Slot("QVariantList")
    def removeSelectedPaths(self, paths: List[Any]) -> None:
        selected = self.queue_manager.paths_from_payload(paths)
        items, removed = self.queue_manager.remove_paths(self.queue_model.items(), selected)
        self.queue_model.set_items(items)
        self._after_queue_removed(removed)

    @QtCore.Slot(str)
    def removeTaskPath(self, path_text: str) -> None:
        self.removeSelectedPaths([path_text])

    def _after_queue_removed(self, removed: int) -> None:
        if removed <= 0:
            return
        self._selected_index = -1
        self._selected_path = ""
        self._notify_queue_stats()
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()
        self._append_log("INFO", f"Видалено: {removed}")

    @QtCore.Slot()
    def clearQueue(self) -> None:
        self.queue_model.set_items([])
        self._selected_index = -1
        self._selected_path = ""
        self._clear_info()
        self._set_output_preview("Черга порожня.")
        self._set_selected_preview("—", "—")
        self._notify_queue_stats()
        self._refresh_codec_distribution()
        self._save_state()
        self._append_log("INFO", "Чергу очищено")

    @QtCore.Slot()
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
        if not self._watch_auto_convert_enabled:
            return
        self._watch_pending_paths.update(item.path for item in items)
        self._start_pending_watch_items()

    def _start_pending_watch_items(self) -> bool:
        if not self._watch_auto_convert_enabled or self._is_running:
            return False
        if self.runner.is_running:
            QtCore.QTimer.singleShot(150, self._start_pending_watch_items)
            return True
        if not self._output_dir_configured or not self.outputDir:
            self._append_log("WARN", "Watch auto-convert skipped: output folder is not configured.")
            return False
        paths = {
            item.path
            for item in self.queue_model.items()
            if item.path in self._watch_pending_paths and item.status in {TaskStatus.QUEUED, TaskStatus.READY}
        }
        if not paths:
            return False
        self._watch_pending_paths.difference_update(paths)
        self._append_log("INFO", f"Watch auto-convert starting: {len(paths)} file(s)")
        self._start_conversion(dict(self._last_settings_map), only_paths=paths)
        return self._is_running

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
        if stopped:
            self._watch_pending_paths.clear()
        elif not self._start_pending_watch_items():
            self._run_completion_action()

    def _send_http_notifications(self, summary: Dict[str, Any]) -> None:
        if not self._webhook_enabled:
            return
        if not any(
            [
                self._webhook_url.strip(),
                self._discord_webhook_url.strip(),
                self._telegram_bot_token.strip() and self._telegram_chat_id.strip(),
            ]
        ):
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
                cmd = (
                    ["shutdown", "/s", "/t", "30", "/c", "Media Converter batch finished"] if os.name == "nt" else ["shutdown", "-h", "+1"]
                )
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

    def _run_preflight(self, settings_map: Dict[str, Any], *, only_paths: Optional[set[Path]] = None) -> Dict[str, Any]:
        result = self.validation.validate(
            dict(settings_map),
            tasks=self.queue_model.items(),
            output_dir=self.outputDir,
            ffmpeg_path=self.ffmpegPath,
            include_queue=True,
            only_paths=only_paths,
            media_info=self.media_info_cache,
        )
        self._preflight_result = self._apply_license_preflight(dict(result), dict(settings_map))
        self.preflightChanged.emit()
        return self._preflight_result

    def _apply_license_preflight(self, result: Dict[str, Any], settings_map: Dict[str, Any]) -> Dict[str, Any]:
        errors = dict(result.get("errors") or {})
        warnings = list(result.get("warnings") or [])
        settings = settings_map_to_model(settings_map, defaults=ConversionSettings())
        if settings.commercial_export and not self._commercial_export_allowed():
            errors["commercial_license"] = "Watermark-free commercial export requires an active Commercial license."
        active_features = set(self._license_info.features) if self._pro_features_enabled() else set()
        if settings.cloud_upload_enabled and "cloud_upload" not in active_features:
            errors["cloud_upload"] = "Cloud upload is a Pro feature. Start trial or activate a Commercial license."
        if settings.ai_blur_enabled:
            if "ai_blur" not in active_features:
                errors["ai_blur"] = "AI blur is a Pro feature. Start trial or activate a Commercial license."
            elif "AI blur engine requires" not in " ".join(warnings):
                warnings.append("AI blur is license-enabled; automatic detection still requires an external ML/API integration.")
        bits = []
        if errors:
            bits.append(f"Критичних помилок: {len(errors)}")
        if warnings:
            bits.append(f"Попереджень: {len(warnings)}")
        result["errors"] = errors
        result["warnings"] = warnings
        result["ok"] = not errors
        result["summary"] = " | ".join(bits) if bits else str(result.get("summary") or "Перевірка пройдена.")
        return result

    @QtCore.Slot("QVariantMap", result="QVariantMap")
    def refreshPreflight(self, settings_map: Dict[str, Any]) -> Dict[str, Any]:
        self._last_settings_map = dict(settings_map)
        self._refresh_output_preview(dict(settings_map))
        return self._run_preflight(dict(settings_map))

    def _video_can_remux(self, task: TaskItem, settings: ConversionSettings, info: Optional[MediaInfo]) -> bool:
        if not info:
            return False
        codec = str(info.vcodec or "").strip().lower()
        out_fmt = str(settings.out_video_format or "").strip().lower()
        if out_fmt in {"mp4", "mov"}:
            return codec in {"h264", "hevc", "h265", "av1"}
        if out_fmt == "mkv":
            return codec in {"h264", "hevc", "h265", "av1", "vp9", "mpeg2video"}
        if out_fmt == "webm":
            return codec in {"vp9", "av1"}
        return task.path.suffix.lower().lstrip(".") == out_fmt and bool(codec)

    def _smart_recommendation_for_task(self, task: TaskItem, settings_map: Dict[str, Any]) -> str:
        if task.media_type != "video":
            return ""
        merged_map = merge_settings_maps(settings_map, task.overrides)
        settings = settings_map_to_model(merged_map, defaults=ConversionSettings())
        if settings.operation not in {"convert", "subtitle_burn"}:
            return ""
        info = self.media_info_cache.get(task.path) or task.probe_data
        source_fmt = task.path.suffix.lower().lstrip(".")
        out_fmt = str(settings.out_video_format or "").strip().lower()
        requested_codec = str(settings.video_codec or "auto").strip().lower()
        if settings.smart_reencode_detection and info and self._video_can_remux(task, settings, info):
            if source_fmt == out_fmt and requested_codec in {"auto", "copy"}:
                return "можна не перекодовувати"
            return "краще remux"
        recommendation = recommend_settings(settings, info, task.path)
        if "H.265" in recommendation.video_codec:
            return f"краще H.265 | CRF {recommendation.crf} | {recommendation.preset}"
        return f"{recommendation.video_codec} | CRF {recommendation.crf} | {recommendation.reason}"

    def _refresh_smart_recommendations(self, settings_map: Dict[str, Any]) -> None:
        for task in self.queue_model.items():
            self.queue_model.set_smart_recommendation(
                task.path,
                self._smart_recommendation_for_task(task, settings_map),
            )

    def _refresh_queue_layout_state(self) -> None:
        self._selected_index = self.queue_model.index_for_path(Path(self._selected_path)) if self._selected_path else -1
        self._notify_queue_stats()
        self._refresh_codec_distribution()
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()

    @QtCore.Slot(str)
    def cleanupQueue(self, mode: str) -> None:
        normalized = str(mode or "").strip().lower()
        kept: List[TaskItem] = []
        removed = 0
        for item in self.queue_model.items():
            remove = False
            if normalized in {"done", "completed", "ready"}:
                remove = item.status in {TaskStatus.SUCCESS, TaskStatus.SKIPPED}
            elif normalized in {"failed", "errors"}:
                remove = item.status in {TaskStatus.FAILED, TaskStatus.CANCELLED}
            elif normalized in {"missing", "absent"}:
                remove = not item.path.exists()
            if remove:
                removed += 1
            else:
                kept.append(item)
        if removed <= 0:
            self._append_log("INFO", f"Cleanup queue: 0 ({normalized or 'all'})")
            return
        self.queue_model.set_items(kept)
        if self._selected_path and self.queue_model.index_for_path(Path(self._selected_path)) < 0:
            self._selected_path = ""
            self._selected_index = -1
            self._clear_info()
        self._refresh_queue_layout_state()
        self._append_log("INFO", f"Cleanup queue: {removed} ({normalized})")

    @QtCore.Slot(str)
    def toggleTaskPinned(self, path_text: str) -> None:
        task_path = Path(str(path_text or "").strip()).expanduser()
        task = self.queue_model.item_by_path(task_path)
        if not task:
            return
        self.queue_model.set_pinned(task_path, not task.pinned)
        self.sortQueueByPriority()

    @QtCore.Slot(str, int)
    def setTaskPriority(self, path_text: str, priority: int) -> None:
        task_path = Path(str(path_text or "").strip()).expanduser()
        if self.queue_model.item_by_path(task_path) is None:
            return
        self.queue_model.set_priority(task_path, priority)
        self.sortQueueByPriority()

    @QtCore.Slot()
    def sortQueueByPriority(self) -> None:
        ranked = sorted(
            enumerate(self.queue_model.items()),
            key=lambda pair: (not pair[1].pinned, -int(pair[1].priority), pair[0]),
        )
        self.queue_model.set_items([item for _, item in ranked])
        self._refresh_queue_layout_state()
