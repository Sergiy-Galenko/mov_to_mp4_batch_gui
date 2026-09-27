"""Capture the real QML interface with isolated settings and demo files.

Run from the repository: python scripts/capture_readme.py
No conversion, model download, or user configuration is required.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_QUICK_BACKEND"] = "software"
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
    os.environ["QML_DISABLE_DISK_CACHE"] = "1"
    with tempfile.TemporaryDirectory(prefix="media-converter-docs-") as temporary:
        os.environ["MEDIA_CONVERTER_PORTABLE_DIR"] = temporary

        from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QSettings, QUrl
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtQuickControls2 import QQuickStyle
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication

        from app.models import TaskItem
        from ui.backend import Backend

        QQuickStyle.setStyle("Basic")
        app = QApplication([])
        app.setOrganizationName("MediaConverterDocumentation")
        app.setApplicationName("MediaConverterDocumentation")
        QSettings.setDefaultFormat(QSettings.IniFormat)
        QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, temporary)
        output = ROOT / "docs" / "images"
        output.mkdir(parents=True, exist_ok=True)
        demo = Path(temporary) / "demo"
        demo.mkdir()
        cover = demo / "Обкладинка.png"
        shutil.copyfile(ROOT / "assets" / "app-logo-v2.png", cover)
        notes = demo / "Нотатки.txt"
        notes.write_text("Мій перший проєкт\n\nДодайте файли, оберіть формат і папку результатів.\n", encoding="utf-8")
        captions = demo / "Субтитри.srt"
        captions.write_text("1\n00:00:00,000 --> 00:00:03,000\nВітаємо в Media Converter!\n", encoding="utf-8")

        backend = Backend()
        # Startup normally offers a managed FFmpeg download. Screenshots must
        # remain offline and must not install anything.
        backend._start_ffmpeg_auto_install = lambda **_kwargs: None
        engine = QQmlApplicationEngine()
        try:
            backend.uiLanguage = "uk"
            backend.themeMode = "dark"
            backend.autoDisplayAdaptation = False
            backend.outputDir = str(demo / "Результати")
            Path(backend.outputDir).mkdir()
            backend.queueViewMode = "list"
            backend.queue_model.set_items([
                TaskItem(cover, "image", thumbnail_path=str(cover), size_text="1.4 MB"),
                TaskItem(notes, "text", size_text=f"{notes.stat().st_size} B"),
                TaskItem(captions, "subtitle", size_text=f"{captions.stat().st_size} B"),
            ])
            qml = ROOT / "ui" / "qml"
            engine.addImportPath(str(qml))
            engine.rootContext().setContextProperty("backend", backend)
            engine.load(QUrl.fromLocalFile(str(qml / "Main.qml")))
            if not engine.rootObjects():
                raise RuntimeError("Main.qml did not load")
            window = engine.rootObjects()[0]
            window.resize(1240, 840)
            window.show()
            QTest.qWait(800)
            welcome = window.findChild(QObject, "whatsNewPopup")
            if welcome is not None:
                QMetaObject.invokeMethod(welcome, "close")
            for _ in range(100):
                if not backend.systemProfile.busy:
                    break
                QTest.qWait(50)

            def capture(target, name):
                QTest.qWait(400)
                picture = target.grabWindow()
                if picture.isNull() or not picture.save(str(output / name)):
                    raise RuntimeError(f"Failed to capture {name}")
                print(f"Saved docs/images/{name} ({picture.width()} × {picture.height()})")

            capture(window, "queue-dark.png")
            backend.themeMode = "light"
            capture(window, "queue-light.png")
            backend.themeMode = "dark"
            editor = next(obj for obj in app.allWindows() if obj is not window and obj.metaObject().indexOfMethod("openForFile(QVariant)") >= 0)
            QMetaObject.invokeMethod(editor, "openForFile", Q_ARG("QVariant", str(cover)))
            for _ in range(100):
                QTest.qWait(50)
                if not backend.editorProject.importer.busy:
                    break
            if backend.editorProject.importer.busy:
                raise RuntimeError("Demo media import timed out")
            editor.resize(1440, 980)
            capture(editor, "montage-editor.png")
            editor.setProperty("allowClose", True)
            editor.close()
            window.close()
        finally:
            backend.shutdown()


if __name__ == "__main__":
    main()
