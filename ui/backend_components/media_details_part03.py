from __future__ import annotations

BODY = r'''            return
        settings = dict(entry.get("settings") or {})
        if not settings:
            self._append_log("WARN", "У цьому запуску немає збережених налаштувань.")
            return
        self._last_settings_map = settings
        self.presetLoaded.emit(settings)
        self._refresh_output_preview(settings)
        self._append_log("OK", "Налаштування запуску завантажено з історії.")

    @QtCore.Slot(int)
    def rerunHistory(self, index: int) -> None:
        entry = self.history_model.entry_at(index)
        if not entry:
            return
        settings = dict(entry.get("settings") or {})
        paths = [Path(str(result.get("path"))) for result in entry.get("results", []) if result.get("path")]
        if paths:
            self._add_paths(paths)
        self._start_conversion(settings, only_paths={path.expanduser() for path in paths})

    @QtCore.Slot(str, result="QVariantMap")
    def getMontageSession(self, path_text: str) -> Dict[str, Any]:
        path = Path(str(path_text or "").strip()).expanduser()
        index = self.queue_model.index_for_path(path)
        task = self.queue_model.item_at(index) if index >= 0 else None
        overrides = dict(task.overrides) if task else None
        return self.montage_service.get_session(path, existing_overrides=overrides)

    @QtCore.Slot(str, result=str)
    def requestMontageWaveform(self, path_text: str) -> str:
        path = Path(str(path_text or "").strip()).expanduser()

        def _bg() -> None:
            wf = self.montage_service.get_audio_waveform(path)
            self.montageWaveformReady.emit(str(path), wf)

        threading.Thread(target=_bg, daemon=True).start()
        return self.montage_service.get_audio_waveform(path)

    @QtCore.Slot(str, "QVariantMap")
    def saveMontageSession(self, path_text: str, session_map: Dict[str, Any]) -> None:
        path = Path(str(path_text or "").strip()).expanduser()
        self.montage_service.save_session(path, session_map)
        self.montageSessionUpdated.emit(str(path))

    @QtCore.Slot(str, "QVariantMap")
    def applyMontageToTask(self, path_text: str, session_map: Dict[str, Any]) -> None:
        path = Path(str(path_text or "").strip()).expanduser()
        data = dict(session_map or {})
        self.montage_service.save_session(path, data)

        in_pt = float(data.get("in_point", 0.0) or 0.0)
        out_pt = float(data.get("out_point", 0.0) or 0.0)
        crop_x = data.get("crop_x")
        crop_y = data.get("crop_y")
        crop_w = data.get("crop_w")
        crop_h = data.get("crop_h")
        audio_enabled = bool(data.get("audio_enabled", True))
        out_format = str(data.get("output_format") or "").strip().lower()

        overrides: Dict[str, Any] = {
            "trim_start": in_pt if in_pt > 0 else None,
            "trim_end": out_pt if out_pt > 0 else None,
            "crop_x": int(crop_x) if crop_x is not None else None,
            "crop_y": int(crop_y) if crop_y is not None else None,
            "crop_w": int(crop_w) if crop_w is not None else None,
            "crop_h": int(crop_h) if crop_h is not None else None,
            "remove_audio": not audio_enabled,
        }
        has_crop = any(
            v is not None for v in (overrides["crop_x"], overrides["crop_y"], overrides["crop_w"], overrides["crop_h"])
        )
        if has_crop:
            overrides["fast_copy"] = False
        if out_format:
            overrides["out_video_format"] = out_format

        self.updateTaskOverrideByPath(str(path), overrides)
        self.montageSessionUpdated.emit(str(path))

    @QtCore.Slot(str, int, result=str)
    def requestMontageProxy(self, path_text: str, target_height: int = 720) -> str:
        path = Path(str(path_text or "").strip()).expanduser()

        def _bg() -> None:
            proxy_path = self.montage_service.create_or_get_proxy(path, target_height=target_height)
            self.montageProxyReady.emit(str(path), proxy_path)

        threading.Thread(target=_bg, daemon=True).start()
        return self.montage_service.get_proxy_path(path, target_height=target_height)

    @QtCore.Slot(str, int, result=bool)
    def isMontageProxyReady(self, path_text: str, target_height: int = 720) -> bool:
        path = Path(str(path_text or "").strip()).expanduser()
        return self.montage_service.is_proxy_ready(path, target_height=target_height)

    @QtCore.Slot(str, int, result=str)
    def getMontageProxyPath(self, path_text: str, target_height: int = 720) -> str:
        path = Path(str(path_text or "").strip()).expanduser()
        return self.montage_service.get_proxy_path(path, target_height=target_height)

    @QtCore.Slot(str, result="QVariantMap")
    def getTimelineProject(self, path_text: str) -> Dict[str, Any]:
        path = Path(str(path_text or "").strip()).expanduser()
        return self.montage_service.get_timeline_project(path)

    @QtCore.Slot(str, "QVariantMap")
    def saveTimelineProject(self, path_text: str, project_map: Dict[str, Any]) -> None:
        path = Path(str(path_text or "").strip()).expanduser()
        self.montage_service.save_timeline_project(path, dict(project_map or {}))
        self.montageSessionUpdated.emit(str(path))

    @QtCore.Slot("QVariantMap", str, bool, result=bool)
    def renderTimelineProject(self, project_map: Dict[str, Any], output_path: str, prefer_proxy: bool = False) -> bool:
        out_p = Path(str(output_path or "").strip()).expanduser()

        def _bg() -> None:
            ok = self.montage_service.render_timeline(dict(project_map or {}), out_p, prefer_proxy=prefer_proxy)
            self.montageTimelineRendered.emit(str(out_p), ok)

        threading.Thread(target=_bg, daemon=True).start()
        return True

    @QtCore.Slot(str, "QVariantList", int, str, result="QVariantMap")
    def diarizeMedia(self, path_text: str, segments: list, num_speakers: int = 2, language: str = "uk") -> Dict[str, Any]:
        path = Path(str(path_text or "").strip()).expanduser()
        seg_list = [dict(s) for s in (segments or [])]
        return self.montage_service.diarize_media(path, seg_list, num_speakers=num_speakers, language=language)

    @QtCore.Slot("QVariantMap", "QVariantMap", result="QVariantMap")
    def applySpeakerAliases(self, diarization_map: Dict[str, Any], aliases_map: Dict[str, str]) -> Dict[str, Any]:
        return self.montage_service.apply_speaker_aliases(dict(diarization_map or {}), dict(aliases_map or {}))

    @QtCore.Slot("QVariantMap", str, str, result=str)
    def exportDiarizedSubtitles(self, diarization_map: Dict[str, Any], output_path: str, format_name: str = "srt") -> str:
        out_p = Path(str(output_path or "").strip()).expanduser()
        return self.montage_service.export_diarized_subtitles(dict(diarization_map or {}), out_p, format_name=format_name)

    @QtCore.Slot("QVariantList", str, str, int, int, result=str)
    def generateStyledSubtitles(
        self,
        segments: list,
        template_name: str = "tiktok_pop",
        output_path: str = "",
        res_x: int = 1080,
        res_y: int = 1920,
    ) -> str:
        seg_list = [dict(s) for s in (segments or [])]
        out_p = Path(str(output_path or "").strip()).expanduser() if output_path else ""
        return self.montage_service.generate_styled_subtitles(
            seg_list, template=template_name, output_path=out_p, res_x=res_x, res_y=res_y
        )

    @QtCore.Slot("QVariantList", "QStringList", str, result="QVariantMap")
    def translateSubtitles(self, segments: list, target_languages: list, source_lang: str = "auto") -> Dict[str, Any]:
        seg_list = [dict(s) for s in (segments or [])]
        langs = [str(l) for l in (target_languages or [])]
        return self.montage_service.translate_subtitles(seg_list, target_languages=langs, source_lang=source_lang)

    @QtCore.Slot(str, str, result="QVariantMap")
    def calculateSmartReframe(self, path_text: str, aspect: str = "9:16") -> Dict[str, Any]:
        path = Path(str(path_text or "").strip()).expanduser()
        return self.montage_service.calculate_smart_reframe(path, aspect=aspect)

    @QtCore.Slot(str, str, "QVariantList", str, result="QVariantMap")
    def trackAndBlurObject(
        self,
        path_text: str,
        target_type: str = "face",
        initial_bbox: list = None,
        blur_style: str = "box",
    ) -> Dict[str, Any]:
        path = Path(str(path_text or "").strip()).expanduser()
        bbox = [int(x) for x in initial_bbox] if initial_bbox and len(initial_bbox) == 4 else None
        return self.montage_service.track_and_blur(
            path, target_type=target_type, initial_bbox=bbox, blur_style=blur_style
        )
'''
