from __future__ import annotations

BODY = r'''        return self.shortcut_manager.all_shortcuts()

    @QtCore.Property("QVariantMap", notify=shortcutsChanged)
    def shortcutsByCategory(self) -> Dict[str, List[Dict[str, str]]]:
        return self.shortcut_manager.shortcuts_by_category()

    @QtCore.Slot(str, result=str)
    def shortcutKey(self, action_id: str) -> str:
        return self.shortcut_manager.get_key(action_id)

    @QtCore.Slot(str, result="QVariantList")
    def globalSearch(self, query: str) -> List[Dict[str, Any]]:
        needle = str(query or "").strip().lower()
        if len(needle) < 2:
            return []
        results: List[Dict[str, Any]] = []

        def add(kind: str, title: str, detail: str, page: int, target: str = "", action: str = "") -> None:
            if len(results) >= 24:
                return
            results.append(
                {
                    "kind": kind,
                    "title": title,
                    "detail": detail,
                    "page": page,
                    "target": target,
                    "action": action,
                }
            )

        for item in self.queue_model.items():
            haystack = " ".join([item.path.name, str(item.path), item.media_type, item.status, item.last_error]).lower()
            if needle in haystack:
                add("Файл", item.path.name, f"{item.media_type} | {item.status} | {item.path}", 0)

        for name in self.preset_manager.names():
            if needle in str(name).lower():
                add("Пресет", str(name), "Відкрити пресети", 2)

        for url in self._youtube_history:
            if needle in str(url).lower():
                add("URL", str(url), "Відкрити Downloads", 4)

        for entry in self.history_store.entries[:30]:
            started = time.strftime("%Y-%m-%d %H:%M", time.localtime(entry.get("started_at", 0) or 0))
            detail = f"{started} | files {entry.get('total_files', 0)} | {entry.get('output_dir', '')}"
            if needle in detail.lower() or needle in str(entry.get("operation", "")).lower():
                add("Історія", str(entry.get("operation", "Run")), detail, 1)

        for line in self._log_lines[-120:]:
            if needle in line.lower():
                add("Лог", line[:80], "Відкрити чергу і лог", 0)

        quick_targets = [
            ("Конвертація", "Черга файлів", 0, ""),
            ("Монтаж", "Відео-редактор", 5, "video_editor"),
            ("Downloads", "Завантаження з URL", 4, ""),
            ("Аналітика", "Графіки та історія", 1, ""),
            ("FFmpeg", "Шлях, кодеки, watch folder", 3, ""),
            ("Налаштування", "Параметри конвертації", 5, "run"),
        ]
        for title, detail, page, target in quick_targets:
            if needle in title.lower() or needle in detail.lower():
                add("Розділ", title, detail, page, target)

        return results

    @QtCore.Slot(str, str)
    def setShortcutKey(self, action_id: str, key: str) -> None:
        conflict = self.shortcut_manager.find_conflict(key, exclude_action=action_id)
        if conflict:
            self._append_log("WARN", f"Shortcut conflict: {key} already used by {self.shortcut_manager.get_label(conflict)}")
            return
        self.shortcut_manager.set_key(action_id, key)
        self.shortcutsChanged.emit()
        self._append_log("OK", f"Shortcut set: {action_id} → {key}")

    @QtCore.Slot(str)
    def resetShortcut(self, action_id: str) -> None:
        self.shortcut_manager.reset_key(action_id)
        self.shortcutsChanged.emit()

    @QtCore.Slot()
    def resetAllShortcuts(self) -> None:
        self.shortcut_manager.reset_all()
        self.shortcutsChanged.emit()
        self._append_log("OK", "All shortcuts reset to defaults.")

    # --- System tray properties ---

    @QtCore.Property(bool, notify=trayVisibilityChanged)
    def trayEnabled(self) -> bool:
        return self._tray_enabled

    @trayEnabled.setter
    def trayEnabled(self, value: bool) -> None:
        next_value = bool(value)
        if self._tray_enabled == next_value:
            return
        self._tray_enabled = next_value
        self.system_tray.set_visible(self._tray_enabled)
        self.trayVisibilityChanged.emit()
        self._save_state()

    @QtCore.Property(bool, notify=pushNotificationsChanged)
    def pushNotificationsEnabled(self) -> bool:
        return self._push_notifications_enabled

    @pushNotificationsEnabled.setter
    def pushNotificationsEnabled(self, value: bool) -> None:
        next_value = bool(value)
        if self._push_notifications_enabled == next_value:
            return
        self._push_notifications_enabled = next_value
        self.system_tray.set_notifications_enabled(self._push_notifications_enabled)
        self.pushNotificationsChanged.emit()
        self._save_state()

    @QtCore.Property(bool, notify=batchWorkflowChanged)
    def watchAutoConvertEnabled(self) -> bool:
        return self._watch_auto_convert_enabled

    @watchAutoConvertEnabled.setter
    def watchAutoConvertEnabled(self, value: bool) -> None:
        next_value = bool(value)
        if next_value and not self._require_pro_feature("batch_automation", "Batch automation"):
            next_value = False
        if self._watch_auto_convert_enabled == next_value:
            return
        self._watch_auto_convert_enabled = next_value
        self.batchWorkflowChanged.emit()
        self._save_state()

    @QtCore.Property(str, notify=batchWorkflowChanged)
    def watchRulesText(self) -> str:
        return self._watch_rules_text

    @watchRulesText.setter
    def watchRulesText(self, value: str) -> None:
        next_value = str(value or "")
        if self._watch_rules_text == next_value:
            return
        self._watch_rules_text = next_value
        self.batchWorkflowChanged.emit()
        self._save_state()

    @QtCore.Property(bool, notify=schedulerChanged)
    def schedulerEnabled(self) -> bool:
        return self._scheduler_enabled

    @schedulerEnabled.setter
    def schedulerEnabled(self, value: bool) -> None:
        next_value = bool(value)
        if next_value and not self._require_pro_feature("batch_automation", "Scheduler"):
            next_value = False
        if self._scheduler_enabled == next_value:
            return
        self._scheduler_enabled = next_value
        self.schedulerChanged.emit()
        self._save_state()

    @QtCore.Property(str, notify=schedulerChanged)
    def schedulerMode(self) -> str:
        return self._scheduler_mode

    @schedulerMode.setter
    def schedulerMode(self, value: str) -> None:
        next_value = str(value or "time").strip().lower()
        if next_value not in {"time", "idle", "time_or_idle", "time_and_idle"}:
            next_value = "time"
        if self._scheduler_mode == next_value:
            return
        self._scheduler_mode = next_value
        self.schedulerChanged.emit()
        self._save_state()

    @QtCore.Property(str, notify=schedulerChanged)
    def schedulerTime(self) -> str:
        return self._scheduler_time

    @schedulerTime.setter
    def schedulerTime(self, value: str) -> None:
        next_value = str(value or "23:00").strip() or "23:00"
        if self._scheduler_time == next_value:
            return
        self._scheduler_time = next_value
        self._scheduler_last_start_key = ""
        self.schedulerChanged.emit()
        self._save_state()

    @QtCore.Property(int, notify=schedulerChanged)
    def schedulerCpuLimit(self) -> int:
        return self._scheduler_cpu_limit

    @schedulerCpuLimit.setter
    def schedulerCpuLimit(self, value: int) -> None:
        next_value = max(1, min(100, int(value or 40)))
        if self._scheduler_cpu_limit == next_value:
            return
        self._scheduler_cpu_limit = next_value
        self.schedulerChanged.emit()
        self._save_state()

    @QtCore.Property(int, notify=schedulerChanged)
    def schedulerGpuLimit(self) -> int:
        return self._scheduler_gpu_limit

    @schedulerGpuLimit.setter
    def schedulerGpuLimit(self, value: int) -> None:
        next_value = max(1, min(100, int(value or 30)))
        if self._scheduler_gpu_limit == next_value:
            return
        self._scheduler_gpu_limit = next_value
        self.schedulerChanged.emit()
        self._save_state()

    @QtCore.Property(str, notify=completionActionChanged)
    def completionAction(self) -> str:
        return self._completion_action

    @completionAction.setter
    def completionAction(self, value: str) -> None:
        next_value = str(value or "none").strip().lower()
        if next_value not in {"none", "open_output", "sleep", "shutdown"}:
            next_value = "none"
        if self._completion_action == next_value:
            return
        self._completion_action = next_value
        self.completionActionChanged.emit()
        self._save_state()

    @QtCore.Property(bool, notify=notificationChannelsChanged)
    def webhookEnabled(self) -> bool:
        return self._webhook_enabled

    @webhookEnabled.setter
    def webhookEnabled(self, value: bool) -> None:
        next_value = bool(value)
        if self._webhook_enabled == next_value:
            return
        self._webhook_enabled = next_value
        self.notificationChannelsChanged.emit()
        self._save_state()

    @QtCore.Property(str, notify=notificationChannelsChanged)
    def webhookUrl(self) -> str:
        return self._webhook_url

    @webhookUrl.setter
    def webhookUrl(self, value: str) -> None:
        next_value = str(value or "").strip()
        if self._webhook_url == next_value:
            return
        self._webhook_url = next_value
        self.notificationChannelsChanged.emit()
        self._save_state()

    @QtCore.Property(str, notify=notificationChannelsChanged)
    def discordWebhookUrl(self) -> str:
        return self._discord_webhook_url

    @discordWebhookUrl.setter
    def discordWebhookUrl(self, value: str) -> None:
        next_value = str(value or "").strip()
        if self._discord_webhook_url == next_value:
            return
        self._discord_webhook_url = next_value
        self.notificationChannelsChanged.emit()
        self._save_state()

    @QtCore.Property(str, notify=notificationChannelsChanged)
    def telegramBotToken(self) -> str:
        return self._telegram_bot_token

    @telegramBotToken.setter
    def telegramBotToken(self, value: str) -> None:
        next_value = str(value or "").strip()
        if self._telegram_bot_token == next_value:
            return
        self._telegram_bot_token = next_value
        self.notificationChannelsChanged.emit()
        self._save_state()

    @QtCore.Property(str, notify=notificationChannelsChanged)
    def telegramChatId(self) -> str:
        return self._telegram_chat_id

    @telegramChatId.setter
    def telegramChatId(self, value: str) -> None:
        next_value = str(value or "").strip()
        if self._telegram_chat_id == next_value:
            return
        self._telegram_chat_id = next_value
        self.notificationChannelsChanged.emit()
        self._save_state()

    @QtCore.Slot()
    def resetWatchRules(self) -> None:
        self.watchRulesText = DEFAULT_FOLDER_RULES

    @QtCore.Slot(str, result="QVariantList")
    def previewWatchRules(self, rules_text: str) -> List[Dict[str, Any]]:
        return self.batch_workflow.preview_rules(rules_text)

    def _license_state(self) -> Dict[str, Any]:
        state = dict(self.settings_manager.state)
        state["license_payload"] = dict(self._license_payload)
        state["trial_started_at"] = float(self._trial_started_at or 0.0)
        state["trial_signature"] = str(self._trial_signature or "")
        return state

    def _refresh_license_info(self) -> None:
        self._license_info = self.license_service.info_from_state(self._license_state())
        self.licenseChanged.emit()

    def _pro_features_enabled(self) -> bool:
        self._license_info = self.license_service.info_from_state(self._license_state())
        return bool(self._license_info.pro_enabled)

    def _commercial_export_allowed(self) -> bool:
        self._license_info = self.license_service.info_from_state(self._license_state())
        return bool(self._license_info.commercial_export_allowed)

    def _require_pro_feature(self, feature: str, label: str) -> bool:
        if self._pro_features_enabled() and feature in set(self._license_info.features):
            return True
        self._append_log("WARN", f"{label} requires Trial or Commercial license.")
        self.toastRequested.emit(f"{label} requires Trial or Commercial license.")
        return False

    @QtCore.Property(str, notify=licenseChanged)
    def licenseStatusText(self) -> str:
        return self._license_info.message or self._license_info.status

    @QtCore.Property(str, notify=licenseChanged)
    def licensePlan(self) -> str:
        return self._license_info.plan

    @QtCore.Property(str, notify=licenseChanged)
    def licenseHolder(self) -> str:
        return self._license_info.holder

    @QtCore.Property(str, notify=licenseChanged)
    def licenseId(self) -> str:
        return self._license_info.license_id

    @QtCore.Property(str, notify=licenseChanged)
    def licenseExpiresAt(self) -> str:
        return self._license_info.expires_at or "Never"

    @QtCore.Property(bool, notify=licenseChanged)
    def licenseActive(self) -> bool:
        return self._license_info.is_license_active

    @QtCore.Property(bool, notify=licenseChanged)
    def trialActive(self) -> bool:
        return self._license_info.is_trial_active

    @QtCore.Property(str, notify=licenseChanged)
    def trialRemainingText(self) -> str:
        if self._trial_started_at <= 0:
            return "Trial not started"
        days = self.license_service.trial_days_remaining(self._trial_started_at)
        return f"{days} day(s) remaining" if days else "Trial expired"

    @QtCore.Property(bool, notify=licenseChanged)
    def proFeaturesEnabled(self) -> bool:
        return self._pro_features_enabled()

    @QtCore.Property(bool, notify=licenseChanged)
    def commercialExportAllowed(self) -> bool:
        return self._commercial_export_allowed()

    @QtCore.Property("QVariantList", notify=licenseChanged)
    def licenseFeatures(self) -> List[str]:
        return list(self._license_info.features)

    @QtCore.Slot(str, result=bool)
    def activateLicenseKey(self, key: str) -> bool:
        try:
            self._license_payload = self.license_service.activate_key(key)
        except Exception as exc:
            self._append_log("ERROR", f"License activation failed: {exc}")
            self.toastRequested.emit(f"License activation failed: {exc}")
            self._refresh_license_info()
            self._save_state()
            return False
        self._refresh_license_info()
        self._save_state()
        self._append_log("OK", f"Commercial license activated: {self._license_info.plan}")
        self.toastRequested.emit("Commercial license activated.")
        return True

    @QtCore.Slot(result=bool)
    def loadOfflineLicenseFile(self) -> bool:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Load offline license", "", "License (*.json *.lic);;JSON (*.json);;All Files (*)")
        if not path:
            return False
        try:
            self._license_payload = self.license_service.load_offline_file(Path(path))
        except Exception as exc:
            self._append_log("ERROR", f"Offline license failed: {exc}")
            self.toastRequested.emit(f"Offline license failed: {exc}")
            self._refresh_license_info()
            self._save_state()
            return False
        self._refresh_license_info()
        self._save_state()
        self._append_log("OK", f"Offline commercial license loaded: {path}")
        self.toastRequested.emit("Offline commercial license loaded.")
        return True

    @QtCore.Slot()
    def startTrial(self) -> None:
        if self._trial_started_at > 0:
            self._refresh_license_info()
            self.toastRequested.emit(self.trialRemainingText)
            return
        updated = self.license_service.start_trial(self._license_state())
        self._trial_started_at = float(updated.get("trial_started_at") or 0.0)
        self._trial_signature = str(updated.get("trial_signature") or "")
        self._refresh_license_info()
        self._save_state()
        self._append_log("OK", "Trial started.")
        self.toastRequested.emit("Trial started.")

    @QtCore.Slot()
    def clearLicense(self) -> None:
        self._license_payload = {}
        self._paid_auto_update_enabled = False
        self._paid_update_available = False
        self._paid_update_download_url = ""
        self._paid_update_status = "Paid auto-update disabled until a Commercial license is active."
        self._refresh_license_info()
        self.paidUpdateChanged.emit()
        self._save_state()
        self._append_log("INFO", "Commercial license removed.")

    @QtCore.Property(bool, notify=paidUpdateChanged)
    def paidAutoUpdateEnabled(self) -> bool:
        return self._paid_auto_update_enabled

    @paidAutoUpdateEnabled.setter
    def paidAutoUpdateEnabled(self, value: bool) -> None:
        next_value = bool(value)
        if next_value and not self._commercial_export_allowed():
            next_value = False
            self._paid_update_status = "Paid auto-update requires an active Commercial license."
        if self._paid_auto_update_enabled == next_value:
            self.paidUpdateChanged.emit()
            return
        self._paid_auto_update_enabled = next_value
        self.paidUpdateChanged.emit()
        self._save_state()

    @QtCore.Property(str, notify=paidUpdateChanged)
    def paidUpdateManifestUrl(self) -> str:
        return self._paid_update_manifest_url

    @paidUpdateManifestUrl.setter
    def paidUpdateManifestUrl(self, value: str) -> None:
        next_value = str(value or "").strip()
        if self._paid_update_manifest_url == next_value:
            return
        self._paid_update_manifest_url = next_value
        self.paidUpdateChanged.emit()
        self._save_state()

    @QtCore.Property(str, notify=paidUpdateChanged)
    def paidUpdateStatus(self) -> str:
        return self._paid_update_status

    @QtCore.Property(bool, notify=paidUpdateChanged)
    def paidUpdateAvailable(self) -> bool:
        return self._paid_update_available

    @QtCore.Slot()
    def checkPaidUpdate(self) -> None:
        if not self._commercial_export_allowed():
            self._paid_update_status = "Paid auto-update requires an active Commercial license."
            self._paid_update_available = False
            self.paidUpdateChanged.emit()
            return
        self._paid_update_status = "Checking paid update..."
        self.paidUpdateChanged.emit()
        threading.Thread(target=self._check_paid_update_async, daemon=True).start()

    def _maybe_check_paid_update_on_startup(self) -> None:
        if self._paid_auto_update_enabled and self._commercial_export_allowed() and self._paid_update_manifest_url:
            self.checkPaidUpdate()

    def _check_paid_update_async(self) -> None:
        info = self.paid_update_service.check(self._paid_update_manifest_url, APP_VERSION)
        self.event_queue.put(("paid_update_done", info))

    def _apply_paid_update_result(self, info: PaidUpdateInfo) -> None:
        self._paid_update_status = info.message
        self._paid_update_available = bool(info.available)
        self._paid_update_download_url = info.download_url
        self.paidUpdateChanged.emit()
        level = "OK" if info.available else "INFO"
        self._append_log(level, f"Paid update: {info.message}")

    @QtCore.Slot()
    def openPaidUpdateDownload(self) -> None:
        if self._paid_update_download_url.startswith("https://"):
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(self._paid_update_download_url))

    @QtCore.Slot()
'''
