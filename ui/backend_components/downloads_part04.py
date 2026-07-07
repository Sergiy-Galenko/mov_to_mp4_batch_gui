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
        self._append_youtube_log("INFO", f"Started: {next_item.get('url')}")
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
                int(next_item.get("rateLimitKbps") or 0),
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

    def _append_youtube_log(self, level: str, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] [{str(level or 'INFO').upper()}] {message}"
        self._youtube_download_log.append(line)
        self._youtube_download_log = self._youtube_download_log[-300:]
        self.youtubeDownloadChanged.emit()

    def _youtube_error_hint(self, message: str) -> str:
        text = str(message or "").lower()
        if "yt-dlp is not installed" in text or "no module named" in text:
            return "Встанови або онови залежності: pip install -r requirements.txt."
        if "unsupported url" in text or "no suitable extractor" in text:
            return "Онови yt-dlp або спробуй пряме посилання на медіафайл."
        if "http 403" in text or "forbidden" in text or "private" in text:
            return "Джерело обмежує доступ. Додай cookies.txt або перевір права доступу."
        if "http 404" in text or "not found" in text:
            return "Посилання або файл не знайдено. Перевір URL."
        if "sign in" in text or "login" in text or "age" in text:
            return "Для цього джерела потрібні cookies з браузера."
        if "ffmpeg" in text:
            return "Перевір шлях до FFmpeg у налаштуваннях."
        return "Перевір URL, cookies, мережу або спробуй оновити yt-dlp."

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
