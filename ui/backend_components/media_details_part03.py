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
'''
