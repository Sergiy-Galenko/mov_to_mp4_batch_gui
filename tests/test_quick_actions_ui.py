import os
from pathlib import Path
from unittest.mock import Mock

from PySide6.QtCore import Q_ARG, Q_RETURN_ARG, QMetaObject, QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models import MediaInfo, TaskItem, TaskStatus
from ui.backend import Backend


def invoke(window, name, *args):
    return QMetaObject.invokeMethod(window, name, *(Q_ARG("QVariant", arg) for arg in args))


def settings(window):
    value = QMetaObject.invokeMethod(window, "collectSettings", Q_RETURN_ARG("QVariant"))
    return value.toVariant() if hasattr(value, "toVariant") else value


def test_quick_actions_audio_conversion_and_results(tmp_path):
    app = QApplication.instance() or QApplication([])
    backend = Backend()
    backend.settings_manager.save = Mock()
    backend._start_conversion = Mock()
    source = tmp_path / "Interview.mp4"
    source.write_bytes(b"s" * 1000)
    output = tmp_path / "Interview.mp3"
    output.write_bytes(b"a" * 250)
    info = MediaInfo(duration=60, width=1920, height=1080, audio_streams=2)
    backend.queue_model.set_items([TaskItem(source, "video", status=TaskStatus.SUCCESS, last_output=str(output), probe_data=info)])
    backend.media_info_cache[source] = info
    engine = QQmlApplicationEngine()
    qml = Path(__file__).resolve().parents[1] / "ui" / "qml"
    engine.addImportPath(str(qml))
    engine.rootContext().setContextProperty("backend", backend)
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
    try:
        engine.load(QUrl.fromLocalFile(str(qml / "Main.qml")))
        assert engine.rootObjects(), warnings
        window = engine.rootObjects()[0]
        QTest.qWait(100)
        assert window.property("simpleMode")
        invoke(window, "selectQueuePath", str(source), 0, 0, source.name, "video", "")
        invoke(window, "quickAction", "audio")
        QTest.qWait(200)
        assert settings(window)["operation"] == "audio_only"
        assert settings(window)["out_audio_fmt"] == "mp3"
        assert QMetaObject.invokeMethod(window.findChild(QObject, "inspectorConvertButton"), "clicked")
        call = backend._start_conversion.call_args
        assert call.args[0]["operation"] == "audio_only"
        assert call.args[0]["out_audio_fmt"] == "mp3"
        assert call.kwargs["only_paths"] == {source}
        tracks = window.findChild(QObject, "inspectorAudioTrack")
        assert tracks.property("count") == 2
        tracks.setProperty("currentIndex", 1)
        QMetaObject.invokeMethod(tracks, "activated", Q_ARG(int, 1))
        assert backend.queue_model.item_at(0).overrides["audio_track_index"] == 1
        details = backend.queueItemDetails(str(source))
        assert details["outputExists"]
        assert details["sizeChangePercent"] == 75.0
        assert details["durationSec"] == 60
        invoke(window, "setQualityProfile", 2)
        assert settings(window)["audio_bitrate"] == "320k"
        invoke(window, "quickAction", "compress")
        assert settings(window)["operation"] == "convert"
        assert settings(window)["crf"] == 28
        assert not settings(window)["fast_copy"]
        invoke(window, "quickAction", "subtitles")
        assert not window.property("simpleMode")
        assert window.property("pendingSettingsTarget") == "audio_subtitles"
        invoke(window, "applyPreset", {"operation": "Лише аудіо", "out_audio_fmt": "mp3"})
        assert settings(window)["operation"] == "audio_only"
        invoke(window, "openSidebarSection", 0, "", -1)
        window.setProperty("simpleMode", True)
        window.setProperty("width", 1440)
        window.setProperty("height", 960)
        QTest.qWait(200)
        if os.environ.get("MEDIA_CONVERTER_UI_CAPTURE"):
            window.grabWindow().save(os.environ["MEDIA_CONVERTER_UI_CAPTURE"])
        backend.queue_model.update_task_state(source, TaskStatus.FAILED, "Permission denied")
        failed = backend.queueItemDetails(str(source))
        assert failed["errorCategory"] == "permission"
        assert "Немає прав" in failed["errorText"]
        assert not [w for w in warnings if "ReferenceError" in w or "TypeError" in w], warnings
    finally:
        for window in engine.rootObjects():
            window.close()
            window.deleteLater()
        engine.deleteLater()
        app.processEvents()
        backend.shutdown()
