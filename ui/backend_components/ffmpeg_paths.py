from __future__ import annotations

from .common import FfmpegAutoInstallResult, FfmpegService, Optional, Path, QtCore, QtGui, QtWidgets, find_ffprobe, os, shutil, threading


class FfmpegPathsMixin:
    @QtCore.Slot()
    def refreshEncoders(self) -> None:
        candidate = self.ffmpegPath or self.ffmpeg_service.ffmpeg_path or ""
        if candidate and (
            Path(candidate).expanduser().exists()
            or (
                os.environ.get("MEDIA_CONVERTER_ALLOW_PATH_BINARIES", "").strip().lower() in {"1", "true", "yes"}
                and shutil.which(candidate)
            )
        ):
            self.ffmpeg_service.ffmpeg_path = candidate
        else:
            self.ffmpeg_service.ffmpeg_path = ""
        if not self.ffmpeg_service.ffmpeg_path:
            self._append_log("WARN", "FFmpeg не знайдено. Автоматично завантажую локальну копію...")
            self._start_ffmpeg_auto_install(force=False)
            return
        if self.ffmpeg_auto_installer.should_run(self.ffmpeg_service.ffmpeg_path, auto_update=True, force=False):
            self._start_ffmpeg_auto_install(force=False)
        self._append_log("INFO", "Перевіряю FFmpeg encoder-и...")
        threading.Thread(
            target=self._detect_encoders_async,
            args=(self.ffmpeg_service.ffmpeg_path,),
            daemon=True,
        ).start()

    @QtCore.Slot()
    def updateFfmpeg(self) -> None:
        self._start_ffmpeg_auto_install(force=True)

    def _start_ffmpeg_auto_install(self, *, force: bool = False) -> None:
        if self._ffmpeg_auto_install_running:
            return
        current = self.ffmpegPath or self.ffmpeg_service.ffmpeg_path or ""
        if not self.ffmpeg_auto_installer.should_run(current, auto_update=True, force=force):
            return
        self._ffmpeg_auto_install_running = True
        self._encoder_info = "FFmpeg: завантаження/оновлення..."
        self.encoderInfoChanged.emit()
        threading.Thread(
            target=self._ffmpeg_auto_install_async,
            args=(current, force),
            daemon=True,
        ).start()

    def _ffmpeg_auto_install_async(self, current_path: str, force: bool) -> None:
        def progress(message: str) -> None:
            self.event_queue.put(("ffmpeg_auto_progress", message))

        result = self.ffmpeg_auto_installer.ensure(
            current_path,
            auto_update=True,
            force=force,
            progress_cb=progress,
        )
        self.event_queue.put(("ffmpeg_auto_done", result))

    def _apply_ffmpeg_auto_install_result(self, result: FfmpegAutoInstallResult) -> None:
        self._ffmpeg_auto_install_running = False
        if result.status in {"external", "current"}:
            return
        if result.status == "unsupported":
            self._append_log("WARN", result.message)
            self._encoder_info = self._tr("backend.ffmpeg_missing")
            self.encoderInfoChanged.emit()
            self._send_push_notification("FFmpeg", result.message, "warning")
            return
        if result.status == "error":
            self._append_log("ERROR", result.message)
            self._encoder_info = self._tr("backend.ffmpeg_missing")
            self.encoderInfoChanged.emit()
            self._send_push_notification("FFmpeg", result.message, "error")
            return
        if result.ffmpeg_path:
            self.ffmpegPath = result.ffmpeg_path
            self.ffmpeg_service.set_paths(result.ffmpeg_path, result.ffprobe_path or find_ffprobe(result.ffmpeg_path))
            self.media_preview.ffmpeg_path = self.ffmpeg_service.ffmpeg_path or ""
            self.media_preview.ffprobe_path = self.ffmpeg_service.ffprobe_path or ""
            self._append_log("OK", f"{result.message} {result.ffmpeg_path}")
            self.toastRequested.emit("FFmpeg готовий")
            self._send_push_notification("FFmpeg", "FFmpeg готовий до роботи.")
            self.refreshEncoders()
            self.startSystemScan()

    def _detect_encoders_async(self, ffmpeg_path: str) -> None:
        ffprobe_path = find_ffprobe(ffmpeg_path)
        service = FfmpegService(ffmpeg_path, ffprobe_path)
        caps = service.detect_encoders()
        self.event_queue.put(("encoder_detection", ffmpeg_path, ffprobe_path, caps))

    def _apply_encoder_detection(self, ffmpeg_path: str, ffprobe_path: Optional[str], caps: set[str]) -> None:
        if self.ffmpegPath and str(ffmpeg_path) != self.ffmpegPath:
            return
        self.ffmpeg_service.ffmpeg_path = ffmpeg_path
        self.ffmpeg_service.ffprobe_path = ffprobe_path
        self.ffmpeg_service.encoder_caps = set(caps)
        summary = []
        apple = sorted(caps & {"h264_videotoolbox", "hevc_videotoolbox", "prores_videotoolbox"})
        if apple:
            summary.append("VideoToolbox (" + ", ".join(name.split("_")[0].upper() for name in apple) + ")")
        if {"h264_nvenc", "hevc_nvenc", "av1_nvenc"} & caps:
            summary.append("NVENC")
        if {"h264_qsv", "hevc_qsv", "av1_qsv"} & caps:
            summary.append("QSV")
        if {"h264_amf", "hevc_amf", "av1_amf"} & caps:
            summary.append("AMF")
        if "libx265" in caps:
            summary.append("x265")
        if {"libsvtav1", "libaom-av1"} & caps:
            summary.append("AV1")
        if "libvpx-vp9" in caps:
            summary.append("VP9")
        self._encoder_info = f"Доступні: {', '.join(summary) if summary else 'немає даних'}"
        self.encoderInfoChanged.emit()
        self._append_log("OK", f"FFmpeg: {self.ffmpeg_service.ffmpeg_path}")
        self._append_log(
            "OK" if self.ffmpeg_service.ffprobe_path else "WARN", f"FFprobe: {self.ffmpeg_service.ffprobe_path or 'не знайдено'}"
        )
        self._save_state()

    @QtCore.Slot()
    def pickFfmpeg(self) -> None:
        filt = "FFmpeg (ffmpeg.exe)" if os.name == "nt" else "FFmpeg (ffmpeg)"
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Вкажи ffmpeg", "", f"{filt};;All Files (*)")
        if path:
            self.ffmpegPath = path
            self.refreshEncoders()
            self.startSystemScan()

    @QtCore.Slot()
    def pickOutputDir(self) -> None:
        start_dir = self.outputDir or str(Path.home())
        folder = QtWidgets.QFileDialog.getExistingDirectory(None, self._tr("choose_output_folder"), start_dir)
        if folder:
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
