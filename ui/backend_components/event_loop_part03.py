from __future__ import annotations

BODY = r'''    def _handle_youtube_event(self, event: tuple) -> None:
        etype = event[0]
        if etype == "youtube_playlist_preview_done":
            self._youtube_playlist_preview = str(event[1] if len(event) > 1 else "")
            self.youtubeDownloadChanged.emit()
            return
        if etype == "youtube_playlist_preview_failed":
            self._youtube_playlist_preview = f"Preview error: {event[1] if len(event) > 1 else ''}"
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
            self._update_youtube_download_item(str(download_id or ""), status="cancelled", statusText="Cancelled", message=str(msg or "Cancelled"))
            self._set_youtube_download_state(False, 0.0, self._tr("youtube.cancelled"))
            self._append_log("WARN", self._tr("youtube.cancelled_detail", error=msg))
            self.toastRequested.emit(self._tr("youtube.cancelled"))
            self._send_push_notification("Downloads", self._tr("youtube.cancelled"), "warning")
            self._youtube_current_download_id = ""
            self._youtube_cancel_event = None
            self._start_next_youtube_download()
            return
        if etype == "youtube_download_failed":
            _, download_id, msg = event if len(event) >= 3 else (etype, self._youtube_current_download_id, "")
            self._update_youtube_download_item(str(download_id or ""), status="failed", statusText="Failed", message=str(msg or "Failed"))
            self._set_youtube_download_state(False, 0.0, self._tr("youtube.failed"))
            self._append_log("ERROR", self._tr("youtube.failed_detail", error=msg))
            self.toastRequested.emit(self._tr("youtube.failed"))
            self._send_push_notification("Downloads", str(msg or self._tr("youtube.failed")), "error")
            self._youtube_current_download_id = ""
            self._youtube_cancel_event = None
            self._start_next_youtube_download()
'''
