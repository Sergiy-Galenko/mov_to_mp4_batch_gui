from __future__ import annotations

BODY = r'''    def _poll_events(self) -> None:
        try:
            while True:
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
                        self._file_progress_text = (
                            f"Файл: {int(file_pct * 100):02d}% • {format_time(out_time)} / {format_time(duration)} • ETA {format_time(file_eta)}"
                        )
                    else:
                        self._file_progress_text = "Файл: --"
                    self.fileProgressTextChanged.emit()
                    self._total_progress_text = f"Всього: {int(total_pct * 100):02d}% • ETA {format_time(total_eta)}"
                    self.totalProgressTextChanged.emit()
                    self._set_progress(file_pct or 0.0, total_pct)
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
                    self._file_progress_text = (
                        f"{Path(path).name}: {int((file_pct or 0.0) * 100):02d}% • ETA {format_time(file_eta)}"
                    )
                    self.fileProgressTextChanged.emit()
                    self._total_progress_text = f"Всього: {int(total_pct * 100):02d}% • ETA {format_time(total_eta)}"
                    self.totalProgressTextChanged.emit()
                    self._set_progress(file_pct or 0.0, total_pct)
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
'''
