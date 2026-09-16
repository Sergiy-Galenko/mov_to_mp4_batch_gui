import sys
from pathlib import Path


def _bootstrap_dependencies() -> None:
    base_dir = Path(__file__).resolve().parent
    try:
        from app.dependency_bootstrap import ensure_runtime_dependencies

        installed = ensure_runtime_dependencies(base_dir / "requirements.txt")
        if installed:
            print("Installed missing Python libraries: " + ", ".join(installed))
    except Exception as exc:
        print(f"Dependency bootstrap failed: {exc}", file=sys.stderr)
        raise


def main() -> None:
    if sys.argv[1:2] == ["--transcribe-worker"]:
        from services.transcription_service import run_transcription_worker

        sys.exit(run_transcription_worker(sys.argv[2:]))
    _bootstrap_dependencies()

    if "--cli" in sys.argv:
        from cli import main as cli_main

        sys.exit(cli_main(sys.argv[1:]))

    from PySide6 import QtCore, QtGui, QtQml, QtWidgets
    from PySide6.QtQuickControls2 import QQuickStyle

    from ui.backend import Backend

    QQuickStyle.setStyle("Basic")
    app = QtWidgets.QApplication(sys.argv)
    # QApplication selects the native widget style for the host OS. Keep that
    # style for system dialogs; the QML controls use our platform theme.
    app.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.GeneralFont))
    app.setOrganizationName("MediaConverter")
    app.setApplicationName("MediaConverter")

    base_dir = Path(__file__).resolve().parent
    logo_path = base_dir / "assets" / "app-logo-v2.png"
    if logo_path.exists():
        app.setWindowIcon(QtGui.QIcon(str(logo_path)))

    qml_dir = base_dir / "ui" / "qml"
    main_qml = qml_dir / "Main.qml"

    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(qml_dir))
    backend = Backend()
    app.aboutToQuit.connect(backend.shutdown)
    engine.rootContext().setContextProperty("backend", backend)
    engine.load(QtCore.QUrl.fromLocalFile(str(main_qml)))

    if not engine.rootObjects():
        sys.exit(1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
