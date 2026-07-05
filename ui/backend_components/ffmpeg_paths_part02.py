from __future__ import annotations

BODY = r'''        if folder:
            self.outputDir = folder

    @QtCore.Slot(result=bool)
    def ensureOutputDirSelected(self) -> bool:
        return self._ensure_output_dir_selected(prompt=True)

    def _ensure_output_dir_selected(self, *, prompt: bool = False) -> bool:
        if self._output_dir_configured and self.outputDir:
            return True
        if not prompt:
            return False
        start_dir = self.outputDir or str(Path.home())
        folder = QtWidgets.QFileDialog.getExistingDirectory(None, self._tr("choose_output_folder"), start_dir)
        if folder:
            self.outputDir = folder
            return True
        self._append_log("WARN", self._tr("backend.output_dir_required"))
        self.toastRequested.emit(self._tr("backend.output_dir_required"))
        return False

    @QtCore.Slot()
    def dismissOnboarding(self) -> None:
        self._show_onboarding = False
        self.onboardingChanged.emit()

    @QtCore.Slot(int, str)
    def useRecentFolder(self, index: int, target: str) -> None:
        if 0 <= index < len(self._recent_folders):
            if target == "watch":
                self.watchFolder = self._recent_folders[index]
            else:
                self.outputDir = self._recent_folders[index]

    @QtCore.Slot()
    def openOutputDir(self) -> None:
        folder = Path(self.outputDir).expanduser()
        if not folder.exists():
            QtWidgets.QMessageBox.warning(None, "Папка", "Папка виводу не існує.")
            return
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(folder)))

    def _open_path(self, path: Path) -> bool:
        path = path.expanduser()
        if not path.exists():
            return False
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path)))
        return True

    @QtCore.Slot(str)
    def openSourcePath(self, path_text: str) -> None:
        path = Path(str(path_text or "").strip()).expanduser()
        if not self._open_path(path):
            QtWidgets.QMessageBox.warning(None, "Джерело", "Файл джерела не знайдено.")

    @QtCore.Slot(str)
    def openOutputForPath(self, path_text: str) -> None:
        task = self.queue_model.item_by_path(Path(str(path_text or "").strip()).expanduser())
        if task is None:
            return
        output_text = (task.last_output or task.preview_output or "").split(";", 1)[0].strip()
        if not output_text:
            QtWidgets.QMessageBox.information(None, "Output", "Output для цього файлу ще не розраховано.")
            return
        output = Path(output_text).expanduser()
        if output.exists():
            self._open_path(output)
        elif output.parent.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(output.parent)))

    @QtCore.Slot(int)
    def copyLogLine(self, index: int) -> None:
        line = self.log_model.line_at(index)
        if line:
            QtWidgets.QApplication.clipboard().setText(line)

    @QtCore.Slot()
    def clearLog(self) -> None:
        self._log_lines = []
        self.log_model.clear()

    @QtCore.Slot(str)
    def openPathFromText(self, text: str) -> None:
        source = str(text or "")
        for item in self.queue_model.items():
            if str(item.path) in source or item.path.name in source:
                self.openSourcePath(str(item.path))
                return
        self._append_log("WARN", "Не вдалося знайти файл для цього повідомлення.")
'''
