import sys
from pathlib import Path

from PySide6 import QtCore, QtQml, QtWidgets
from PySide6.QtQuickControls2 import QQuickStyle

from ui.qml_backend import Backend


def main() -> None:
    QQuickStyle.setStyle("Basic")
    app = QtWidgets.QApplication(sys.argv)

    base_dir = Path(__file__).resolve().parent
    qml_dir = base_dir / "ui" / "qml"
    theme_path = qml_dir / "Theme.qml"
    main_qml = qml_dir / "Main.qml"

    QtQml.qmlRegisterSingletonType(QtCore.QUrl.fromLocalFile(str(theme_path)), "App", 1, 0, "Theme")

    engine = QtQml.QQmlApplicationEngine()
    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)
    engine.load(QtCore.QUrl.fromLocalFile(str(main_qml)))

    if not engine.rootObjects():
        sys.exit(1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
