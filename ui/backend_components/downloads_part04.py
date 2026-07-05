from __future__ import annotations

BODY = r'''    def _start_next_youtube_download(self) -> None:
        if self._youtube_download_running:
            return
        next_item = None
        for item in self._youtube_download_queue:
            if item.get("status") == "queued":
                next_item = item
                break
        if not next_item:
            self._youtube_current_download_id = ""
            self._youtube_cancel_event = None
            return
        self._youtube_current_download_id = str(next_item.get("id") or "")
        self._youtube_cancel_event = threading.Event()
        self._update_youtube_download_item(
            self._youtube_current_download_id,
            status="running",
            statusText="Downloading",
            message=self._tr("youtube.downloading"),
            progress=0.0,
        )
        self._set_youtube_download_state(True, 0.0, self._tr("youtube.downloading"))
        threading.Thread(
            target=self._download_youtube_async,
            args=(
                self._youtube_current_download_id,
                str(next_item.get("url") or ""),
                str(next_item.get("modeValue") or "video"),
                str(next_item.get("quality") or "best"),
                bool(next_item.get("playlist")),
                bool(next_item.get("subtitles")),
                str(next_item.get("cookiesFile") or ""),
                Path(str(next_item.get("outputDir") or self.outputDir)).expanduser(),
                self._youtube_cancel_event,
            ),
            daemon=True,
        ).start()

    def _update_youtube_download_item(self, download_id: str, **updates: Any) -> None:
        if not download_id:
            return
        for item in self._youtube_download_queue:
            if item.get("id") == download_id:
                item.update(updates)
                break
        self.youtubeDownloadChanged.emit()

    def _youtube_speed_text(self, speed: Optional[float]) -> str:
        if not speed:
            return "--"
        return f"{format_bytes(int(speed))}/s"

    def _youtube_eta_text(self, eta: Optional[float]) -> str:
        if eta is None:
            return "--"
        return format_time(float(eta))

    def _set_youtube_download_state(self, running: bool, progress: Optional[float], status: str) -> None:
        self._youtube_download_running = running
        if progress is not None:
            self._youtube_download_progress = max(0.0, min(1.0, float(progress)))
        self._youtube_download_status = status
        self.youtubeDownloadChanged.emit()
'''
