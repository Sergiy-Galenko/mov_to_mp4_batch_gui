from __future__ import annotations

BODY = r'''    @QtCore.Slot()
    def addFiles(self) -> None:
        filt = (
            "Media Files (*.mp4 *.mov *.mkv *.webm *.avi *.m4v *.flv *.wmv *.mts *.m2ts "
            "*.jpg *.jpeg *.png *.bmp *.webp *.tiff *.heic *.heif "
            "*.mp3 *.m4a *.aac *.wav *.flac *.opus *.ogg *.wma *.aiff *.mka "
            "*.srt *.ass *.ssa *.vtt *.webvtt "
            "*.txt *.md *.markdown *.html *.htm *.json *.csv *.tsv *.xml *.yaml *.yml *.log *.rtf "
            "*.pdf *.docx *.docm *.dotx *.doc *.odt *.ott "
            "*.xlsx *.xlsm *.xltx *.xls *.ods *.ots "
            "*.pptx *.pptm *.ppsx *.potx *.ppt *.odp *.otp);;All Files (*)"
        )
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(None, "Додати файли", "", filt)
        paths = [Path(path) for path in files]
        if paths:
            self._remember_folder(str(paths[0].parent))
        self._add_paths(paths)

    @QtCore.Slot(str)
    def addFilesForType(self, media_kind: str) -> None:
        kind = str(media_kind or "").strip().lower()
        filters = {
            "video": "Video Files (*.mp4 *.mov *.mkv *.webm *.avi *.m4v *.flv *.wmv *.mts *.m2ts);;All Files (*)",
            "image": "Photo Files (*.jpg *.jpeg *.png *.bmp *.webp *.tiff *.heic *.heif);;All Files (*)",
            "audio": "Audio Files (*.mp3 *.m4a *.aac *.wav *.flac *.opus *.ogg *.wma *.aiff *.mka);;All Files (*)",
            "subtitle": "Subtitle Files (*.srt *.ass *.ssa *.vtt *.webvtt);;All Files (*)",
            "text": (
                "Text and Office Files (*.txt *.md *.markdown *.html *.htm *.json *.csv *.tsv *.xml *.yaml *.yml *.log *.rtf "
                "*.pdf *.docx *.docm *.dotx *.doc *.odt *.ott "
                "*.xlsx *.xlsm *.xltx *.xls *.ods *.ots "
                "*.pptx *.pptm *.ppsx *.potx *.ppt *.odp *.otp);;All Files (*)"
            ),
        }
        filt = filters.get(kind)
        if not filt:
            self.addFiles()
            return
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(None, "Додати файли", "", filt)
        paths = [Path(path) for path in files]
        if paths:
            self._remember_folder(str(paths[0].parent))
        self._add_paths(paths)

    @QtCore.Slot("QVariantList")
    def addDroppedUrls(self, urls: List[Any]) -> None:
        paths: List[Path] = []
        folders: List[Path] = []
        for value in urls:
            local_path = value.toLocalFile() if isinstance(value, QtCore.QUrl) else QtCore.QUrl(str(value)).toLocalFile()
            if not local_path:
                continue
            path = Path(local_path)
            if path.is_dir():
                folders.append(path)
            else:
                paths.append(path)
        if paths:
            self._remember_folder(str(paths[0].parent))
            self._add_paths(paths)
        for folder in folders:
            self._append_log("INFO", f"Сканую папку у фоні: {folder}")
            threading.Thread(target=self._collect_folder_async, args=(folder,), daemon=True).start()

    @QtCore.Slot()
    def addFolder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(None, "Додати папку")
        if folder:
            base = Path(folder)
            self._append_log("INFO", f"Сканую папку у фоні: {base}")
            threading.Thread(target=self._collect_folder_async, args=(base,), daemon=True).start()

    @QtCore.Slot(str, str)
    def downloadYoutube(self, url: str, mode: str) -> None:
        self.downloadYoutubeAdvanced({"url": url, "mode": mode})

    @QtCore.Slot("QVariantMap")
    def downloadYoutubeAdvanced(self, options: Dict[str, Any]) -> None:
        payload = dict(options or {})
        url_text = str(payload.get("url") or "").strip()
        quality = str(payload.get("quality") or "best").strip().lower()
        clean_mode = str(payload.get("mode") or "").strip().lower()
        if clean_mode not in {"audio", "video"}:
            clean_mode = "audio" if quality == "audio_only" else "video"
        playlist = bool(payload.get("playlist"))
        subtitles = bool(payload.get("subtitles"))
        cookies_file = str(payload.get("cookies_file") or self._youtube_cookies_path or "").strip()
        rate_limit_kbps = self._normalize_download_rate_limit_kbps(payload.get("rate_limit_kbps"))
        urls = self._split_download_urls(url_text)
        if not urls:
            self._append_log("WARN", self._tr("youtube.empty_url"))
            self._append_youtube_log("WARN", self._tr("youtube.empty_url"))
            return
        if not self._ensure_output_dir_selected(prompt=True):
            return

        output_dir = Path(self.outputDir).expanduser()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._append_log("ERROR", self._tr("backend.output_dir_error", error=exc))
            self._append_youtube_log("ERROR", self._tr("backend.output_dir_error", error=exc))
            return

        for clean_url in urls:
            item = self._create_youtube_download_item(clean_url, clean_mode, quality, playlist, subtitles, cookies_file, output_dir, rate_limit_kbps)
            self._youtube_download_queue.append(item)
        self._youtube_playlist_preview = ""
        self._youtube_preview_info = {}
        self.youtubeDownloadChanged.emit()
        self._append_log("INFO", f"Download queued: {len(urls)} URL(s)")
        self._append_youtube_log("INFO", f"Queued {len(urls)} URL(s)")
        if not self._youtube_download_running:
            self._start_next_youtube_download()

    @QtCore.Slot("QVariantMap")
    def importDownloadUrlsFromFile(self, options: Dict[str, Any]) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Імпорт URL", "", "URL lists (*.txt *.csv);;All Files (*)")
        if path:
            self.importDownloadUrlsFromFilePath(path, options)

    @QtCore.Slot(str, "QVariantMap")
    def importDownloadUrlsFromFilePath(self, path_text: str, options: Dict[str, Any]) -> None:
        path = Path(str(path_text or "").strip()).expanduser()
        try:
            urls = self._read_download_urls_file(path)
        except Exception as exc:
            self._append_log("ERROR", f"Не вдалося імпортувати URL: {exc}")
            self._append_youtube_log("ERROR", f"URL import failed: {exc}")
            return
        if not urls:
            self._append_log("WARN", "У файлі не знайдено URL.")
            self._append_youtube_log("WARN", f"No URL found in {path.name}")
            return
        payload = dict(options or {})
        payload["url"] = "\n".join(urls)
        self._append_youtube_log("INFO", f"Imported {len(urls)} URL(s) from {path.name}")
        self.downloadYoutubeAdvanced(payload)

    @QtCore.Slot("QVariantList", "QVariantMap")
    def addDroppedDownloadUrls(self, urls: List[Any], options: Dict[str, Any]) -> None:
        web_urls: List[str] = []
        for value in urls:
            qurl = value if isinstance(value, QtCore.QUrl) else QtCore.QUrl(str(value))
            local_path = qurl.toLocalFile()
            if local_path:
                path = Path(local_path)
                if path.suffix.lower() in {".txt", ".csv"}:
                    self.importDownloadUrlsFromFilePath(str(path), options)
                continue
            text = qurl.toString()
            web_urls.extend(self._split_download_urls(text))
        if web_urls:
            payload = dict(options or {})
            payload["url"] = "\n".join(web_urls)
            self.downloadYoutubeAdvanced(payload)

    def _split_download_urls(self, text: str) -> List[str]:
        raw = str(text or "").strip()
        if not raw:
            return []
        matches = [item.rstrip(".,;") for item in re.findall(r"https?://\S+", raw, flags=re.IGNORECASE)]
        if matches:
            seen: set[str] = set()
            urls: List[str] = []
            for item in matches:
                if item not in seen:
                    urls.append(item)
                    seen.add(item)
            return urls
        return [raw]

    def _read_download_urls_file(self, path: Path) -> List[str]:
        if not path.is_file():
            raise FileNotFoundError(path)
        text_urls: List[str] = []
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as file:
                for row in csv.reader(file):
                    for cell in row:
                        text_urls.extend(self._split_download_urls(str(cell or "")))
        else:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            text_urls.extend(self._split_download_urls(text))
        urls: List[str] = []
        seen: set[str] = set()
        for url in text_urls:
            if url not in seen:
                urls.append(url)
                seen.add(url)
        return urls

    def _normalize_download_rate_limit_kbps(self, value: Any) -> int:
        try:
            parsed = int(float(str(value or "0").strip()))
        except (TypeError, ValueError):
            return 0
        return max(0, parsed)

    def _download_rate_limit_bytes(self, rate_limit_kbps: Any) -> Optional[int]:
        kbps = self._normalize_download_rate_limit_kbps(rate_limit_kbps)
        return kbps * 1024 if kbps > 0 else None

    @QtCore.Slot()
    def cancelYoutubeDownload(self) -> None:
        if self._youtube_cancel_event:
            self._youtube_cancel_event.set()
            self.event_queue.put(("youtube_download_progress", self._youtube_current_download_id, None, self._tr("youtube.cancelling"), None, None, ""))
            self._append_youtube_log("WARN", self._tr("youtube.cancelling"))

    @QtCore.Slot(str)
    def retryYoutubeDownload(self, download_id: str) -> None:
        target_id = str(download_id or "").strip()
        if not target_id:
            return
        for item in self._youtube_download_queue:
            if item.get("id") != target_id:
                continue
            if item.get("status") not in {"failed", "cancelled"}:
                return
            item.update(
                {
                    "status": "queued",
                    "statusText": "Queued",
                    "progress": 0.0,
                    "speedText": "--",
                    "etaText": "--",
                    "message": "Retry queued",
                    "filename": "",
                }
            )
            self._append_youtube_log("INFO", f"Retry queued: {item.get('url')}")
            self.youtubeDownloadChanged.emit()
            if not self._youtube_download_running:
                self._start_next_youtube_download()
            return

    @QtCore.Slot()
    def retryFailedYoutubeDownloads(self) -> None:
        count = 0
        for item in self._youtube_download_queue:
            if item.get("status") in {"failed", "cancelled"}:
                item.update(
                    {
                        "status": "queued",
                        "statusText": "Queued",
                        "progress": 0.0,
                        "speedText": "--",
                        "etaText": "--",
                        "message": "Retry queued",
                        "filename": "",
                    }
                )
                count += 1
        if count:
            self._append_youtube_log("INFO", f"Retry queued for {count} failed download(s)")
            self.youtubeDownloadChanged.emit()
            if not self._youtube_download_running:
                self._start_next_youtube_download()

    @QtCore.Slot()
    def clearYoutubeDownloadLog(self) -> None:
        self._youtube_download_log = []
        self.youtubeDownloadChanged.emit()

    @QtCore.Slot()
    def updateYtdlp(self) -> None:
        if self._ytdlp_update_running:
            return
        self._ytdlp_update_running = True
        self._append_youtube_log("INFO", "Updating yt-dlp...")
        self.youtubeDownloadChanged.emit()
        threading.Thread(target=self._update_ytdlp_async, daemon=True).start()

    def _update_ytdlp_async(self) -> None:
        try:
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            output = (result.stdout or result.stderr or "").strip()
            tail = "\n".join(output.splitlines()[-3:])
            if result.returncode == 0:
                self.event_queue.put(("youtube_ytdlp_update_done", tail or "yt-dlp updated."))
            else:
                self.event_queue.put(("youtube_ytdlp_update_failed", tail or f"pip exited with {result.returncode}"))
        except Exception as exc:
            self.event_queue.put(("youtube_ytdlp_update_failed", str(exc) or exc.__class__.__name__))

    @QtCore.Slot(str)
    def setYoutubeCookiesPath(self, path_text: str) -> None:
        value = str(path_text or "").strip()
        if self._youtube_cookies_path == value:
            return
        self._youtube_cookies_path = value
        self.youtubeHistoryChanged.emit()
        self.youtubeDownloadChanged.emit()
        self._save_state()

    @QtCore.Slot()
    def pickYoutubeCookies(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, self._tr("youtube.cookies_file"), "", "Cookies (*.txt);;All Files (*)")
        if path:
            self.setYoutubeCookiesPath(path)

    @QtCore.Slot()
    def clearYoutubeHistory(self) -> None:
        self._youtube_history = []
        self.youtubeHistoryChanged.emit()
        self._save_state()

    def _download_youtube_async(
        self,
        download_id: str,
        url: str,
        mode: str,
        quality: str,
        playlist: bool,
        subtitles: bool,
        cookies_file: str,
        rate_limit_kbps: int,
        output_dir: Path,
        cancel_event: threading.Event,
    ) -> None:
        def on_progress(progress: DownloadProgress) -> None:
'''
