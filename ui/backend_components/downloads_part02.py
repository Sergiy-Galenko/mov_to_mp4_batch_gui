from __future__ import annotations

BODY = r'''            self.event_queue.put(("youtube_download_progress", download_id, progress.percent, progress.message, progress.speed, progress.eta, progress.filename))

        try:
            service = YouTubeDownloadService(self.ffmpegPath or self.ffmpeg_service.ffmpeg_path)
            output_paths = service.download_many(
                url,
                output_dir,
                mode=mode,
                quality=quality,
                playlist=playlist,
                subtitles=subtitles,
                cookies_file=cookies_file,
                rate_limit=self._download_rate_limit_bytes(rate_limit_kbps),
                cancel_event=cancel_event,
                progress_callback=on_progress,
            )
        except YouTubeDownloadCancelled as exc:
            self.event_queue.put(("youtube_download_cancelled", download_id, str(exc)))
        except YouTubeDownloadError as exc:
            self.event_queue.put(("youtube_download_failed", download_id, str(exc)))
        except Exception as exc:
            self.event_queue.put(("youtube_download_failed", download_id, str(exc) or exc.__class__.__name__))
        else:
            self.event_queue.put(("youtube_download_done", download_id, output_paths, str(output_dir), url))

    def _remember_youtube_url(self, url: str) -> None:
        value = str(url or "").strip()
        if not value:
            return
        self._youtube_history = [item for item in self._youtube_history if item != value]
        self._youtube_history.insert(0, value)
        self._youtube_history = self._youtube_history[:20]
        self.youtubeHistoryChanged.emit()
        self._save_state()

    def _set_youtube_download_state(self, running: bool, progress: Optional[float], status: str) -> None:
        self._youtube_download_running = running
        if progress is not None:
            self._youtube_download_progress = max(0.0, min(1.0, float(progress)))
        self._youtube_download_status = status
        self.youtubeDownloadChanged.emit()

    def _collect_folder_async(self, folder: Path) -> None:
        try:
            items = [path for path in folder.rglob("*") if path.is_file()]
        except Exception as exc:
            self.event_queue.put(("log", "ERROR", f"Не вдалося просканувати папку {folder}: {exc}"))
            return
        self.event_queue.put(("add_paths", items, str(folder)))

    def _add_paths(self, paths: List[Path]) -> None:
        added, duplicates, unsupported = self.queue_manager.build_items(paths, self.queue_model.paths_set())
        if added:
            self.queue_model.add_items(added)
            for item in added:
                self.queue_model.set_file_size(item.path)
                self._prefetch_probe_async(item.path, item.media_type)
                self._ensure_thumbnail_async(item.path, item.media_type)
            self._notify_queue_stats()
            self._refresh_codec_distribution()
            self._append_log("OK", self._tr("backend.added_files", count=len(added)))
            self._refresh_output_preview(dict(self._last_settings_map))
            self._save_state()
        if duplicates:
            self._append_log("INFO", self._tr("backend.duplicates_skipped", count=duplicates))
        if unsupported:
            self._append_log("WARN", self._tr("backend.unsupported_skipped", count=unsupported))
        if not added and not duplicates and not unsupported:
            self._append_log("WARN", self._tr("backend.no_tasks"))
'''
