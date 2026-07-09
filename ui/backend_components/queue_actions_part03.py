from __future__ import annotations

BODY = r'''    def _run_preflight(self, settings_map: Dict[str, Any], *, only_paths: Optional[set[Path]] = None) -> Dict[str, Any]:
        result = self.validation.validate(
            dict(settings_map),
            tasks=self.queue_model.items(),
            output_dir=self.outputDir,
            ffmpeg_path=self.ffmpegPath,
            include_queue=True,
            only_paths=only_paths,
        )
        self._preflight_result = self._apply_license_preflight(dict(result), dict(settings_map))
        self.preflightChanged.emit()
        return self._preflight_result

    def _apply_license_preflight(self, result: Dict[str, Any], settings_map: Dict[str, Any]) -> Dict[str, Any]:
        errors = dict(result.get("errors") or {})
        warnings = list(result.get("warnings") or [])
        settings = settings_map_to_model(settings_map, defaults=ConversionSettings())
        if settings.commercial_export and not self._commercial_export_allowed():
            errors["commercial_license"] = "Watermark-free commercial export requires an active Commercial license."
        active_features = set(self._license_info.features) if self._pro_features_enabled() else set()
        if settings.cloud_upload_enabled and "cloud_upload" not in active_features:
            errors["cloud_upload"] = "Cloud upload is a Pro feature. Start trial or activate a Commercial license."
        if settings.ai_blur_enabled:
            if "ai_blur" not in active_features:
                errors["ai_blur"] = "AI blur is a Pro feature. Start trial or activate a Commercial license."
            elif "AI blur engine requires" not in " ".join(warnings):
                warnings.append("AI blur is license-enabled; automatic detection still requires an external ML/API integration.")
        bits = []
        if errors:
            bits.append(f"Критичних помилок: {len(errors)}")
        if warnings:
            bits.append(f"Попереджень: {len(warnings)}")
        result["errors"] = errors
        result["warnings"] = warnings
        result["ok"] = not errors
        result["summary"] = " | ".join(bits) if bits else str(result.get("summary") or "Перевірка пройдена.")
        return result

    @QtCore.Slot("QVariantMap", result="QVariantMap")
    def refreshPreflight(self, settings_map: Dict[str, Any]) -> Dict[str, Any]:
        self._last_settings_map = dict(settings_map)
        self._refresh_output_preview(dict(settings_map))
        return self._run_preflight(dict(settings_map))

    def _video_can_remux(self, task: TaskItem, settings: ConversionSettings, info: Optional[MediaInfo]) -> bool:
        if not info:
            return False
        codec = str(info.vcodec or "").strip().lower()
        out_fmt = str(settings.out_video_format or "").strip().lower()
        if out_fmt in {"mp4", "mov"}:
            return codec in {"h264", "hevc", "h265", "av1"}
        if out_fmt == "mkv":
            return codec in {"h264", "hevc", "h265", "av1", "vp9", "mpeg2video"}
        if out_fmt == "webm":
            return codec in {"vp9", "av1"}
        return task.path.suffix.lower().lstrip(".") == out_fmt and bool(codec)

    def _smart_recommendation_for_task(self, task: TaskItem, settings_map: Dict[str, Any]) -> str:
        if task.media_type != "video":
            return ""
        merged_map = merge_settings_maps(settings_map, task.overrides)
        settings = settings_map_to_model(merged_map, defaults=ConversionSettings())
        if settings.operation not in {"convert", "subtitle_burn"}:
            return ""
        info = self.media_info_cache.get(task.path) or task.probe_data
        source_fmt = task.path.suffix.lower().lstrip(".")
        out_fmt = str(settings.out_video_format or "").strip().lower()
        requested_codec = str(settings.video_codec or "auto").strip().lower()
        if settings.smart_reencode_detection and info and self._video_can_remux(task, settings, info):
            if source_fmt == out_fmt and requested_codec in {"auto", "copy"}:
                return "можна не перекодовувати"
            return "краще remux"
        recommendation = recommend_settings(settings, info, task.path)
        if "H.265" in recommendation.video_codec:
            return f"краще H.265 | CRF {recommendation.crf} | {recommendation.preset}"
        return f"{recommendation.video_codec} | CRF {recommendation.crf} | {recommendation.reason}"

    def _refresh_smart_recommendations(self, settings_map: Dict[str, Any]) -> None:
        for task in self.queue_model.items():
            self.queue_model.set_smart_recommendation(
                task.path,
                self._smart_recommendation_for_task(task, settings_map),
            )

    def _refresh_queue_layout_state(self) -> None:
        self._selected_index = self.queue_model.index_for_path(Path(self._selected_path)) if self._selected_path else -1
        self._notify_queue_stats()
        self._refresh_codec_distribution()
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()

    @QtCore.Slot(str)
    def cleanupQueue(self, mode: str) -> None:
        normalized = str(mode or "").strip().lower()
        kept: List[TaskItem] = []
        removed = 0
        for item in self.queue_model.items():
            remove = False
            if normalized in {"done", "completed", "ready"}:
                remove = item.status in {TaskStatus.SUCCESS, TaskStatus.SKIPPED}
            elif normalized in {"failed", "errors"}:
                remove = item.status in {TaskStatus.FAILED, TaskStatus.CANCELLED}
            elif normalized in {"missing", "absent"}:
                remove = not item.path.exists()
            if remove:
                removed += 1
            else:
                kept.append(item)
        if removed <= 0:
            self._append_log("INFO", f"Cleanup queue: 0 ({normalized or 'all'})")
            return
        self.queue_model.set_items(kept)
        if self._selected_path and self.queue_model.index_for_path(Path(self._selected_path)) < 0:
            self._selected_path = ""
            self._selected_index = -1
            self._clear_info()
        self._refresh_queue_layout_state()
        self._append_log("INFO", f"Cleanup queue: {removed} ({normalized})")

    @QtCore.Slot(str)
    def toggleTaskPinned(self, path_text: str) -> None:
        task_path = Path(str(path_text or "").strip()).expanduser()
        task = self.queue_model.item_by_path(task_path)
        if not task:
            return
        self.queue_model.set_pinned(task_path, not task.pinned)
        self.sortQueueByPriority()

    @QtCore.Slot(str, int)
    def setTaskPriority(self, path_text: str, priority: int) -> None:
        task_path = Path(str(path_text or "").strip()).expanduser()
        if self.queue_model.item_by_path(task_path) is None:
            return
        self.queue_model.set_priority(task_path, priority)
        self.sortQueueByPriority()

    @QtCore.Slot()
    def sortQueueByPriority(self) -> None:
        ranked = sorted(
            enumerate(self.queue_model.items()),
            key=lambda pair: (not pair[1].pinned, -int(pair[1].priority), pair[0]),
        )
        self.queue_model.set_items([item for _, item in ranked])
        self._refresh_queue_layout_state()
'''
