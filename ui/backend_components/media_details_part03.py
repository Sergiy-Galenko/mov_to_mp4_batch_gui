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

    @QtCore.Slot(result="QVariantMap")
    def getScriptingConfig(self) -> Dict[str, Any]:
        return self.scripting_service.get_config()

    @QtCore.Slot("QVariantMap", result=bool)
    def saveScriptingConfig(self, config_map: Dict[str, Any]) -> bool:
        try:
            self.scripting_service.save(dict(config_map or {}))
            self.scriptingConfigChanged.emit()
            return True
        except Exception as exc:
            self.toastRequested.emit(f"Помилка збереження скриптів: {exc}")
            return False

    @QtCore.Slot(str, str, "QVariantMap", "QVariantMap", result="QVariantMap")
    def testUserScript(
        self,
        script_type: str,
        code: str,
        sample_file: Dict[str, Any] = None,
        sample_settings: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        s_file = dict(sample_file) if sample_file else None
        s_sett = dict(sample_settings) if sample_settings else None
        return self.scripting_service.test_script(script_type, code, sample_file=s_file, sample_settings=s_sett)

    @QtCore.Slot(str, result=list)
    def getScriptSnippets(self, script_type: str) -> list:
        return self.scripting_service.get_snippets(script_type)

    @QtCore.Slot(str, result=str)
    def resetScriptToDefault(self, script_type: str) -> str:
        return self.scripting_service.reset_script(script_type)

    @QtCore.Slot(result="QVariantMap")
    def checkSpeechHardware(self) -> Dict[str, Any]:
        return self.speech_diagnostic.check_hardware().to_dict()

    @QtCore.Slot(result="QVariantMap")
    def checkSpeechDependencies(self) -> Dict[str, Any]:
        return self.speech_diagnostic.check_dependencies().to_dict()

    @QtCore.Slot(str, result=bool)
    def installSpeechDependencies(self, preferred_engine: str = "auto") -> bool:
        def _bg() -> None:
            self.speechInstallProgress.emit("Встановлення залежностей мовлення...")
            ok, msg = self.speech_diagnostic.install_dependencies(preferred_engine)
            self.speechInstallFinished.emit(ok, msg)
            self.speechDiagnosticChanged.emit()

        threading.Thread(target=_bg, daemon=True).start()
        return True

    @QtCore.Slot(str, result=bool)
    def runSpeechRecognitionTest(self, requested_device: str = "auto") -> bool:
        def _bg() -> None:
            res = self.speech_diagnostic.run_quick_recognition_test(requested_device)
            self.speechTestFinished.emit(res.to_dict())

        threading.Thread(target=_bg, daemon=True).start()
        return True

    @QtCore.Slot(str, result="QVariantMap")
    def runSpeechRecognitionTestSync(self, requested_device: str = "auto") -> Dict[str, Any]:
        return self.speech_diagnostic.run_quick_recognition_test(requested_device).to_dict()
'''
