from __future__ import annotations

BODY = r'''    def _probe_media_async(self, path: Path) -> None:
        info = self.media_analysis.probe(path)
        self.event_queue.put(("media_info", path, info))

    def _prefetch_probe_async(self, path: Path, media_kind: str) -> None:
        if media_kind not in {"video", "audio"}:
            return
        if not self.ffmpeg_service.ffprobe_path or path in self.media_info_cache or path in self._probe_pending:
            return
        self._probe_pending.add(path)

        def run_probe() -> None:
            info = self.media_analysis.probe(path)
            self.event_queue.put(("media_info", path, info))

        self._probe_executor.submit(run_probe)

    def _ensure_thumbnail_async(self, path: Path, media_kind: str) -> None:
        if media_kind == "image":
            self.queue_model.set_thumbnail(path, str(path))
            return
        if media_kind != "video":
            return
        current = self.queue_model.item_by_path(path)
        if current and current.thumbnail_path:
            return
        threading.Thread(target=self._create_thumbnail_async, args=(path, media_kind), daemon=True).start()

    def _create_thumbnail_async(self, path: Path, media_kind: str) -> None:
        thumbnail = self.media_analysis.thumbnail_for(path, media_kind)
        if thumbnail:
            self.event_queue.put(("thumbnail", path, thumbnail))

    def _update_info(self, info: MediaInfo) -> None:
        self._info_duration = format_time(info.duration)
        self._info_codec = f"{info.vcodec or '-'} / {info.acodec or '-'}"
        self._info_res = f"{info.width}x{info.height}" if info.width and info.height else "—"
        self._info_size = format_bytes(info.size_bytes)
        self._info_container = info.format_name or "—"
        analysis_bits: List[str] = []
        if info.fps:
            fps_label = f"{info.fps:.3f} fps"
            if info.frame_rate_mode:
                fps_label += f" ({info.frame_rate_mode})"
            analysis_bits.append(fps_label)
        if info.dynamic_range:
            analysis_bits.append(info.dynamic_range)
        if info.color_space:
            analysis_bits.append(info.color_space)
        if info.rotation not in (None, 0):
            analysis_bits.append(f"rotation {info.rotation}°")
        analysis_bits.append(f"audio {info.audio_streams}")
        analysis_bits.append(f"subs {info.subtitle_streams}")
        if info.chapters:
            analysis_bits.append(f"chapters {len(info.chapters)}")
        self._info_analysis = " | ".join(bit for bit in analysis_bits if bit) or "—"
        self._info_warnings = " | ".join(info.warnings) if info.warnings else "—"
        self.infoChanged.emit()

    def _clear_info(self) -> None:
        self._info_name = "—"
        self._info_duration = "--:--"
        self._info_codec = "—"
        self._info_res = "—"
        self._info_size = "—"
        self._info_container = "—"
        self._info_analysis = "—"
        self._info_warnings = "—"
        self.infoChanged.emit()

    @QtCore.Slot()
    def pickWatermark(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Вибрати водяний знак", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)")
        if path:
            self.watermarkPicked.emit(path)

    @QtCore.Slot()
    def pickCoverArt(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Вибрати cover art", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)")
        if path:
            self.coverArtPicked.emit(path)

    @QtCore.Slot()
    def pickAudioReplace(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Вибрати аудіо для заміни", "", "Audio (*.mp3 *.m4a *.aac *.wav *.flac *.opus *.ogg *.mp4 *.mov *.mkv);;All Files (*)")
        if path:
            self.audioReplacePicked.emit(path)

    @QtCore.Slot()
    def pickFont(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Вибрати шрифт", "", "Fonts (*.ttf *.otf);;All Files (*)")
        if path:
            self.fontPicked.emit(path)

    @QtCore.Slot()
    def pickSubtitle(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Вибрати субтитри", "", "Subtitles (*.srt *.ass *.ssa *.vtt *.webvtt);;All Files (*)")
        if path:
            self.subtitlePicked.emit(path)

    @QtCore.Slot(str, result=str)
    def readTextPreview(self, path_text: str) -> str:
        path = Path(str(path_text or "").strip()).expanduser()
        if not path.exists() or not path.is_file():
            return ""
        try:
            from services.text_conversion_service import read_text_file

            text, encoding = read_text_file(path)
        except Exception as exc:
            return f"Preview unavailable: {exc}"
        limit = 6000
        suffix = f"\n\n... ({encoding})" if len(text) > limit else f"\n\n({encoding})"
        return text[:limit] + suffix

    @QtCore.Slot("QVariantMap", result="QVariantMap")
    def validateSettings(self, settings_map: Dict[str, Any]) -> Dict[str, Any]:
        return self.validation.validate(
            dict(settings_map),
            tasks=self.queue_model.items(),
            output_dir=self.outputDir,
            ffmpeg_path=self.ffmpegPath,
            include_queue=False,
            require_output_dir=False,
        )

    def _refresh_output_preview(self, settings_map: Dict[str, Any]) -> None:
        summary = self.preview_builder.build(
            settings_map,
            tasks=self.queue_model.items(),
            output_dir=self.outputDir,
            selected_path=self._selected_path,
            media_info=self.media_info_cache,
        )
        for item in summary.items:
            self.queue_model.set_preview_output(item.source_path, str(item.output_path))
'''
