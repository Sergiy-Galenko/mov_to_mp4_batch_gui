from __future__ import annotations

from .common import ANALYTICS_EMIT_INTERVAL_SEC, RESOURCE_SAMPLE_INTERVAL_SEC, Path, TaskStatus, format_time, queue, time


class EventLoopMixin:
    def _poll_events(self) -> None:
        deadline = time.monotonic() + 0.008
        try:
            for _ in range(128):
                if time.monotonic() >= deadline:
                    break
                event = self.event_queue.get_nowait()
                etype = event[0]
                if etype == "log":
                    _, level, msg = event
                    self._append_log(level, msg)
                elif etype == "encoder_detection":
                    _, ffmpeg_path, ffprobe_path, caps = event
                    self._apply_encoder_detection(ffmpeg_path, ffprobe_path, caps)
                elif etype == "ffmpeg_auto_progress":
                    _, msg = event
                    self._append_log("INFO", str(msg))
                    self._set_status(str(msg))
                elif etype == "ffmpeg_auto_done":
                    _, result = event
                    self._apply_ffmpeg_auto_install_result(result)
                elif etype == "status":
                    _, msg = event
                    self._set_status(msg)
                elif str(etype).startswith("youtube_"):
                    self._handle_youtube_event(event)
                elif etype == "youtube_download_done":
                    _, output_paths, remember_folder, source_url = event
                    paths = [Path(path) for path in output_paths]
                    self._set_youtube_download_state(False, 1.0, self._tr("youtube.done"))
                    if paths:
                        if len(paths) == 1:
                            self._append_log("OK", self._tr("youtube.added_to_queue", file=paths[0].name))
                        else:
                            self._append_log("OK", self._tr("youtube.added_many_to_queue", count=len(paths)))
                    self._remember_youtube_url(str(source_url or ""))
                    if remember_folder:
                        self._remember_folder(remember_folder)
                    self._add_paths(paths)
                    self.toastRequested.emit(self._tr("youtube.done"))
                    file_word = "файл" if len(paths) == 1 else "файлів"
                    self._send_push_notification("Downloads", f"Завантажено {len(paths)} {file_word}.")
                    self._youtube_cancel_event = None
                elif etype == "youtube_download_cancelled":
                    _, msg = event
                    self._set_youtube_download_state(False, 0.0, self._tr("youtube.cancelled"))
                    self._append_log("WARN", self._tr("youtube.cancelled_detail", error=msg))
                    self.toastRequested.emit(self._tr("youtube.cancelled"))
                    self._send_push_notification("Downloads", self._tr("youtube.cancelled"), "warning")
                    self._youtube_cancel_event = None
                elif etype == "youtube_download_failed":
                    _, msg = event
                    self._set_youtube_download_state(False, 0.0, self._tr("youtube.failed"))
                    self._append_log("ERROR", self._tr("youtube.failed_detail", error=msg))
                    self.toastRequested.emit(self._tr("youtube.failed"))
                    self._send_push_notification("Downloads", str(msg or self._tr("youtube.failed")), "error")
                    self._youtube_cancel_event = None
                elif etype == "progress":
                    if len(event) >= 8:
                        _, file_pct, out_time, duration, file_eta, total_pct, total_eta, speed = event
                    else:
                        _, file_pct, out_time, duration, file_eta, total_pct, total_eta = event
                        speed = None
                    if file_pct is not None:
                        self._file_progress_text = f"Файл: {int(file_pct * 100):02d}% • {format_time(out_time)} / {format_time(duration)} • ETA {format_time(file_eta)}"
                    else:
                        self._file_progress_text = "Файл: --"
                    self.fileProgressTextChanged.emit()
                    self._total_progress_text = f"Всього: {int(total_pct * 100):02d}% • ETA {format_time(total_eta)}"
                    self.totalProgressTextChanged.emit()
                    self._set_progress(file_pct or 0.0, total_pct)
                    self.taskbar.set_running_progress(total_pct)
                    if self._tray_enabled or self._push_notifications_enabled:
                        self.system_tray.update_progress(total_pct, True)
                    if self._active_task_path and file_pct is not None:
                        self.queue_model.set_task_progress(
                            Path(self._active_task_path),
                            file_pct,
                            format_time(file_eta),
                            f"{float(speed):.1f}x" if speed else "",
                        )
                    now = time.monotonic()
                    if speed and self._run_started_monotonic and now - self._last_analytics_emit >= ANALYTICS_EMIT_INTERVAL_SEC:
                        self._last_analytics_emit = now
                        self._speed_history.append(
                            {
                                "time": now - self._run_started_monotonic,
                                "speed": float(speed),
                            }
                        )
                        self._speed_history = self._speed_history[-120:]
                        self.speedHistoryChanged.emit(list(self._speed_history))
                    if self._run_started_monotonic and now - self._last_resource_emit >= RESOURCE_SAMPLE_INTERVAL_SEC:
                        self._last_resource_emit = now
                        self._append_resource_sample(now)
                    self._refresh_session_stats(total_eta=total_eta)
                elif etype == "task_progress":
                    _, path, file_pct, file_eta, speed, total_pct, total_eta = event
                    self.queue_model.set_task_progress(
                        path,
                        file_pct or 0.0,
                        format_time(file_eta),
                        f"{float(speed):.1f}x" if speed else "",
                    )
                    self._file_progress_text = f"{Path(path).name}: {int((file_pct or 0.0) * 100):02d}% • ETA {format_time(file_eta)}"
                    self.fileProgressTextChanged.emit()
                    self._total_progress_text = f"Всього: {int(total_pct * 100):02d}% • ETA {format_time(total_eta)}"
                    self.totalProgressTextChanged.emit()
                    self._set_progress(file_pct or 0.0, total_pct)
                    self.taskbar.set_running_progress(total_pct)
                    now = time.monotonic()
                    if speed and self._run_started_monotonic and now - self._last_analytics_emit >= ANALYTICS_EMIT_INTERVAL_SEC:
                        self._last_analytics_emit = now
                        self._speed_history.append(
                            {
                                "time": now - self._run_started_monotonic,
                                "speed": float(speed),
                            }
                        )
                        self._speed_history = self._speed_history[-120:]
                        self.speedHistoryChanged.emit(list(self._speed_history))
                    if self._run_started_monotonic and now - self._last_resource_emit >= RESOURCE_SAMPLE_INTERVAL_SEC:
                        self._last_resource_emit = now
                        self._append_resource_sample(now)
                    self._refresh_session_stats(total_eta=total_eta)
                elif etype == "set_total":
                    self._set_progress(0.0, 0.0)
                elif etype == "done":
                    _, stopped = event
                    self._active_task_path = ""
                    self._is_running = False
                    self.isRunningChanged.emit()
                    if self._is_paused:
                        self._is_paused = False
                        self.isPausedChanged.emit()
                    if stopped:
                        self._cancel_active_items()
                    self._set_status(self._tr("backend.stopped") if stopped else self._tr("backend.ready"))
                    self.toastRequested.emit(self._tr("backend.stopped") if stopped else self._tr("toast.conversion_done"))
                    self._refresh_session_stats(total_eta=0.0)
                    self._save_state(pending_recovery=False)
                    self.taskbar.clear_progress()
                    if self._tray_enabled or self._push_notifications_enabled:
                        self.system_tray.update_progress(0.0, False)
                    if self._push_notifications_enabled:
                        if stopped:
                            self._send_push_notification("Конвертацію зупинено", self._tr("backend.stopped"), "warning")
                        else:
                            done = self.completedCount
                            failed = self.failedCount
                            message = f"Готово: {done} файлів" + (f", помилки: {failed}" if failed else "")
                            self._send_push_notification(
                                "Конвертацію завершено",
                                message,
                                "error" if failed else "info",
                            )
                    self._handle_batch_completion(stopped)
                elif etype == "media_info":
                    _, path, info = event
                    self._probe_pending.discard(path)
                    if info:
                        self.media_info_cache[path] = info
                        self.converter.prefetched_media_info[path] = info
                        self.queue_model.set_media_summary(path, info)
                        self._refresh_codec_distribution()
                    current = self.queue_model.item_by_path(path)
                    if current and current.status == TaskStatus.ANALYZING:
                        self.queue_model.update_task_state(path, TaskStatus.READY)
                        self._notify_queue_stats()
                    selected = self.queue_model.item_at(self._selected_index)
                    if info and selected and selected.path == path:
                        self._update_info(info)
                    self._schedule_output_preview()
                elif etype == "thumbnail":
                    _, path, thumbnail_path = event
                    self._thumbnail_pending.discard(path)
                    self.queue_model.set_thumbnail(path, thumbnail_path)
                    if str(path) == self._selected_path:
                        self.selectedDetailsChanged.emit()
                elif etype == "add_paths":
                    _, paths, remember_folder = event
                    if remember_folder:
                        self._remember_folder(remember_folder)
                    self._add_paths(paths)
                elif etype == "watch_paths":
                    _, paths, remember_folder = event
                    self._handle_watch_paths(paths, remember_folder)
                elif etype == "paid_update_done":
                    _, info = event
                    self._apply_paid_update_result(info)
                elif etype == "source_update_done":
                    _, info = event
                    self._apply_source_update_result(info)
                elif etype == "dedupe_hash_done":
                    _, unique, removed, log_lines = event
                    self.queue_model.set_items(unique)
                    self._notify_queue_stats()
                    self._refresh_output_preview(dict(self._last_settings_map))
                    self._save_state()
                    for line in log_lines:
                        self._append_log("INFO", line)
                    self._append_log("INFO", f"Видалено hash-дублікатів: {removed}")
                elif etype == "task_state":
                    _, path, status, message, output_path = event
                    if status in {TaskStatus.RUNNING, TaskStatus.PAUSED}:
                        self._active_task_path = str(path)
                        self._task_started_at.setdefault(path, time.monotonic())
                    self.queue_model.update_task_state(path, status, message, output_path)
                    if status == TaskStatus.SUCCESS and output_path:
                        self.queue_model.set_output_stats(path, output_path)
                    if status in {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.SKIPPED, TaskStatus.CANCELLED}:
                        self._record_file_timing(path, status)
                        if str(path) == self._active_task_path:
                            self._active_task_path = ""
                    self._notify_queue_stats()
                    self._schedule_state_save()
                elif etype == "run_summary":
                    _, summary = event
                    if isinstance(summary, dict):
                        self._record_history(summary)
                elif etype == "preview_generated":
                    _, path_text, preview_data = event
                    self.previewGenerated.emit(str(path_text), dict(preview_data or {}))
        except queue.Empty:
            return

    def _handle_youtube_event(self, event: tuple) -> None:
        etype = event[0]
        if etype == "youtube_playlist_preview_done":
            self._youtube_playlist_preview = str(event[1] if len(event) > 1 else "")
            self._youtube_preview_info = dict(event[2]) if len(event) > 2 and isinstance(event[2], dict) else {}
            self._append_youtube_log("INFO", self._youtube_playlist_preview)
            self.youtubeDownloadChanged.emit()
            return
        if etype == "youtube_playlist_preview_failed":
            msg = str(event[1] if len(event) > 1 else "")
            self._youtube_playlist_preview = f"Preview error: {msg}"
            self._youtube_preview_info = {
                "error": msg,
                "hint": self._youtube_error_hint(msg),
            }
            self._append_youtube_log("ERROR", f"Preview failed: {msg}")
            self.youtubeDownloadChanged.emit()
            return
        if etype == "youtube_ytdlp_update_done":
            msg = str(event[1] if len(event) > 1 else "yt-dlp updated.")
            self._ytdlp_update_running = False
            self._append_youtube_log("OK", msg)
            self.toastRequested.emit("yt-dlp оновлено.")
            self.youtubeDownloadChanged.emit()
            return
        if etype == "youtube_ytdlp_update_failed":
            msg = str(event[1] if len(event) > 1 else "yt-dlp update failed.")
            self._ytdlp_update_running = False
            self._append_youtube_log("ERROR", f"yt-dlp update failed: {msg}")
            self.toastRequested.emit("yt-dlp не вдалося оновити.")
            self.youtubeDownloadChanged.emit()
            return
        if etype == "youtube_download_progress":
            if len(event) >= 7:
                _, download_id, progress, msg, speed, eta, filename = event
                self._update_youtube_download_item(
                    str(download_id or ""),
                    status="running",
                    statusText="Downloading",
                    progress=max(0.0, min(1.0, float(progress))) if progress is not None else 0.0,
                    speedText=self._youtube_speed_text(speed),
                    etaText=self._youtube_eta_text(eta),
                    message=str(msg or self._tr("youtube.downloading")),
                    filename=str(filename or ""),
                )
                self._set_youtube_download_state(True, progress, str(msg or self._tr("youtube.downloading")))
            else:
                _, progress, msg = event
                self._set_youtube_download_state(True, progress, str(msg or self._tr("youtube.downloading")))
            return
        if etype == "youtube_download_done":
            if len(event) >= 5:
                _, download_id, output_paths, remember_folder, source_url = event
            else:
                _, output_paths, remember_folder, source_url = event
                download_id = self._youtube_current_download_id
            paths = [Path(path) for path in output_paths]
            self._update_youtube_download_item(
                str(download_id or ""),
                status="done",
                statusText="Done",
                progress=1.0,
                speedText="--",
                etaText="--",
                message=self._tr("youtube.done"),
            )
            self._set_youtube_download_state(False, 1.0, self._tr("youtube.done"))
            if paths:
                if len(paths) == 1:
                    self._append_log("OK", self._tr("youtube.added_to_queue", file=paths[0].name))
                else:
                    self._append_log("OK", self._tr("youtube.added_many_to_queue", count=len(paths)))
            self._append_youtube_log("OK", f"Done: {len(paths)} file(s)")
            self._remember_youtube_url(str(source_url or ""))
            if remember_folder:
                self._remember_folder(remember_folder)
            self._add_paths(paths)
            self.toastRequested.emit(self._tr("youtube.done"))
            self._send_push_notification("Downloads", f"Завантажено {len(paths)} файл(ів).")
            self._youtube_current_download_id = ""
            self._youtube_cancel_event = None
            self._start_next_youtube_download()
            return
        if etype == "youtube_download_cancelled":
            _, download_id, msg = event if len(event) >= 3 else (etype, self._youtube_current_download_id, "")
            self._update_youtube_download_item(
                str(download_id or ""), status="cancelled", statusText="Cancelled", message=str(msg or "Cancelled")
            )
            self._set_youtube_download_state(False, 0.0, self._tr("youtube.cancelled"))
            self._append_log("WARN", self._tr("youtube.cancelled_detail", error=msg))
            self._append_youtube_log("WARN", f"Cancelled: {msg}")
            self.toastRequested.emit(self._tr("youtube.cancelled"))
            self._send_push_notification("Downloads", self._tr("youtube.cancelled"), "warning")
            self._youtube_current_download_id = ""
            self._youtube_cancel_event = None
            self._start_next_youtube_download()
            return
        if etype == "youtube_download_failed":
            _, download_id, msg = event if len(event) >= 3 else (etype, self._youtube_current_download_id, "")
            hint = self._youtube_error_hint(str(msg or ""))
            message = f"{msg} | {hint}" if msg else hint
            self._update_youtube_download_item(str(download_id or ""), status="failed", statusText="Failed", message=message)
            self._set_youtube_download_state(False, 0.0, self._tr("youtube.failed"))
            self._append_log("ERROR", self._tr("youtube.failed_detail", error=message))
            self._append_youtube_log("ERROR", f"Failed: {message}")
            self.toastRequested.emit(self._tr("youtube.failed"))
            self._send_push_notification("Downloads", str(message or self._tr("youtube.failed")), "error")
            self._youtube_current_download_id = ""
            self._youtube_cancel_event = None
            self._start_next_youtube_download()
