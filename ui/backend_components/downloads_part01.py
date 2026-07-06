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
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(None, "Р”РѕРґР°С‚Рё С„Р°Р№Р»Рё", "", filt)
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
        clean_url = str(payload.get("url") or "").strip()
        quality = str(payload.get("quality") or "best").strip().lower()
        clean_mode = str(payload.get("mode") or "").strip().lower()
        if clean_mode not in {"audio", "video"}:
            clean_mode = "audio" if quality == "audio_only" else "video"
        playlist = bool(payload.get("playlist"))
        subtitles = bool(payload.get("subtitles"))
        cookies_file = str(payload.get("cookies_file") or self._youtube_cookies_path or "").strip()
        if not clean_url:
            self._append_log("WARN", self._tr("youtube.empty_url"))
            return
        if not self._ensure_output_dir_selected(prompt=True):
            return

        output_dir = Path(self.outputDir).expanduser()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._append_log("ERROR", self._tr("backend.output_dir_error", error=exc))
            return

        item = self._create_youtube_download_item(clean_url, clean_mode, quality, playlist, subtitles, cookies_file, output_dir)
        self._youtube_download_queue.append(item)
        self._youtube_playlist_preview = ""
        self.youtubeDownloadChanged.emit()
        self._append_log("INFO", f"YouTube queued: {clean_url}")
        if not self._youtube_download_running:
            self._start_next_youtube_download()

    @QtCore.Slot()
    def cancelYoutubeDownload(self) -> None:
        if self._youtube_cancel_event:
            self._youtube_cancel_event.set()
            self.event_queue.put(("youtube_download_progress", self._youtube_current_download_id, None, self._tr("youtube.cancelling"), None, None, ""))

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
        output_dir: Path,
        cancel_event: threading.Event,
    ) -> None:
        def on_progress(progress: DownloadProgress) -> None:
'''
