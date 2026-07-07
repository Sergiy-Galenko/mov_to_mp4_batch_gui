from __future__ import annotations

BODY = r'''    @QtCore.Slot(str, bool, str)
    def previewYoutubePlaylist(self, url: str, playlist: bool, cookies_file: str) -> None:
        clean_url = str(url or "").strip()
        if not clean_url:
            self._youtube_playlist_preview = "URL порожній."
            self.youtubeDownloadChanged.emit()
            return
        cookies = str(cookies_file or self._youtube_cookies_path or "").strip()
        self._youtube_playlist_preview = "Перевіряю playlist..."
        self.youtubeDownloadChanged.emit()
        threading.Thread(
            target=self._preview_youtube_playlist_async,
            args=(clean_url, bool(playlist), cookies),
            daemon=True,
        ).start()

    def _preview_youtube_playlist_async(self, url: str, playlist: bool, cookies_file: str) -> None:
        try:
            service = YouTubeDownloadService(self.ffmpegPath or self.ffmpeg_service.ffmpeg_path)
            info = service.preview(url, playlist=playlist, cookies_file=cookies_file)
            title = str(info.get("title") or "Source")
            count = int(info.get("count") or 0)
            if bool(info.get("is_playlist")):
                message = f"Playlist: {count} відео | {title}"
            else:
                duration = str(info.get("duration_text") or "--:--")
                quality = str(info.get("quality_summary") or "Best available")
                source_type = str(info.get("source_type") or info.get("media_kind") or "video")
                message = f"{source_type}: {duration} | {quality} | {title}"
            self.event_queue.put(("youtube_playlist_preview_done", message, dict(info)))
        except Exception as exc:
            self.event_queue.put(("youtube_playlist_preview_failed", str(exc) or exc.__class__.__name__))

    def _create_youtube_download_item(
        self,
        url: str,
        mode: str,
        quality: str,
        playlist: bool,
        subtitles: bool,
        cookies_file: str,
        output_dir: Path,
        rate_limit_kbps: int = 0,
    ) -> Dict[str, Any]:
        download_id = f"yt-{int(time.time() * 1000)}-{len(self._youtube_download_queue) + 1}"
        return {
            "id": download_id,
            "url": url,
            "mode": "Audio only" if mode == "audio" else "Video",
            "modeValue": mode,
            "quality": quality,
            "playlist": bool(playlist),
            "subtitles": bool(subtitles),
            "cookiesFile": cookies_file,
            "outputDir": str(output_dir),
            "rateLimitKbps": int(rate_limit_kbps or 0),
            "status": "queued",
            "statusText": "Queued",
            "progress": 0.0,
            "speedText": "--",
            "etaText": "--",
            "message": "Queued",
            "filename": "",
        }
'''
