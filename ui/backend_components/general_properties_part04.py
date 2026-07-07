from __future__ import annotations

BODY = r'''    @QtCore.Property("QVariantList", notify=youtubeDownloadChanged)
    def youtubeDownloadQueue(self) -> List[Dict[str, Any]]:
        return [dict(item) for item in self._youtube_download_queue]

    @QtCore.Property(str, notify=youtubeDownloadChanged)
    def youtubeCookiesStatus(self) -> str:
        path_text = str(self._youtube_cookies_path or "").strip()
        if not path_text:
            return "Cookies: не підключено"
        path = Path(path_text).expanduser()
        if path.is_file():
            return "Cookies: підключено"
        return "Cookies: файл не знайдено"

    @QtCore.Property(str, notify=youtubeDownloadChanged)
    def youtubePlaylistPreview(self) -> str:
        return self._youtube_playlist_preview

    @QtCore.Property("QVariantMap", notify=youtubeDownloadChanged)
    def youtubePreviewInfo(self) -> Dict[str, Any]:
        return dict(self._youtube_preview_info)

    @QtCore.Property("QVariantList", notify=youtubeDownloadChanged)
    def youtubeDownloadLog(self) -> List[str]:
        return list(self._youtube_download_log)

    @QtCore.Property(bool, notify=youtubeDownloadChanged)
    def ytdlpUpdateRunning(self) -> bool:
        return self._ytdlp_update_running

    @QtCore.Property(bool, notify=preflightChanged)
    def preflightOk(self) -> bool:
        return bool(self._preflight_result.get("ok", True))

    @QtCore.Property(str, notify=preflightChanged)
    def preflightSummary(self) -> str:
        return str(self._preflight_result.get("summary") or "")

    @QtCore.Property("QVariantList", notify=preflightChanged)
    def preflightErrors(self) -> List[str]:
        errors = self._preflight_result.get("errors") or {}
        if isinstance(errors, dict):
            return [str(value) for value in errors.values()]
        return [str(value) for value in errors]

    @QtCore.Property("QVariantList", notify=preflightChanged)
    def preflightWarnings(self) -> List[str]:
        return [str(value) for value in self._preflight_result.get("warnings") or []]
'''
