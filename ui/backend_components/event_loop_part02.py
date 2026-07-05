from __future__ import annotations

BODY = r'''                        self.speedHistoryChanged.emit(list(self._speed_history))
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
                    self._refresh_output_preview(dict(self._last_settings_map))
                elif etype == "thumbnail":
                    _, path, thumbnail_path = event
                    self.queue_model.set_thumbnail(path, thumbnail_path)
                elif etype == "add_paths":
                    _, paths, remember_folder = event
                    if remember_folder:
                        self._remember_folder(remember_folder)
                    self._add_paths(paths)
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
                    self._save_state()
                elif etype == "run_summary":
                    _, summary = event
                    if isinstance(summary, dict):
                        self._record_history(summary)
                elif etype == "preview_generated":
                    _, path_text, preview_data = event
                    self.previewGenerated.emit(str(path_text), dict(preview_data or {}))
        except queue.Empty:
            return
'''
