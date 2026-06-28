import sys
from pathlib import Path


def main() -> None:
    if "--cli" in sys.argv:
        from cli import main as cli_main

        sys.exit(cli_main(sys.argv[1:]))

    from PySide6 import QtCore, QtQml, QtWidgets
    from PySide6.QtQuickControls2 import QQuickStyle

    from ui.backend import Backend

    QQuickStyle.setStyle("Basic")
    app = QtWidgets.QApplication(sys.argv)

    base_dir = Path(__file__).resolve().parent
    qml_dir = base_dir / "ui" / "qml"
    main_qml = qml_dir / "Main.qml"

    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(qml_dir))
    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)
    engine.load(QtCore.QUrl.fromLocalFile(str(main_qml)))

    if not engine.rootObjects():
        sys.exit(1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
