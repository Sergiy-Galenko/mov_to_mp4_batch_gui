from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6 import QtWidgets

import services.system_tray_service as tray_module
from services.system_tray_service import SystemTrayService


class FakeAction:
    def __init__(self, text):
        self.text = text
        self.triggered = SimpleNamespace(connect=Mock())


class FakeMenu:
    def __init__(self):
        self.actions = []
        self.popup = Mock()

    def addAction(self, text):
        action = FakeAction(text)
        self.actions.append(action)
        return action

    def addSeparator(self):
        pass


class FakeTray:
    def __init__(self, parent):
        self.parent = parent
        self.activated = SimpleNamespace(connect=Mock())
        self.setContextMenu = Mock()
        self.setIcon = Mock()
        self.setToolTip = Mock()
        self.show = Mock()
        self.hide = Mock()


@pytest.mark.parametrize(("platform", "uses_native_menu"), [("darwin", False), ("win32", True)])
def test_setup_uses_native_tray_menu_only_off_macos(monkeypatch, platform, uses_native_menu):
    original_tray_icon = QtWidgets.QSystemTrayIcon
    fake_tray = FakeTray(None)
    fake_tray_icon = Mock(return_value=fake_tray)
    fake_tray_icon.isSystemTrayAvailable.return_value = True
    fake_tray_icon.ActivationReason = original_tray_icon.ActivationReason
    fake_tray_icon.Context = original_tray_icon.Context
    fake_tray_icon.Trigger = original_tray_icon.Trigger
    fake_tray_icon.DoubleClick = original_tray_icon.DoubleClick
    menu = FakeMenu()
    fake_widgets = SimpleNamespace(QSystemTrayIcon=fake_tray_icon, QMenu=lambda: menu)
    monkeypatch.setattr(tray_module, "QtWidgets", fake_widgets)
    system = "Darwin" if platform == "darwin" else "Windows"
    monkeypatch.setattr(tray_module.platform, "system", lambda: system)
    service = SystemTrayService()
    service._create_default_icon = lambda: object()

    service.setup(None)

    assert fake_tray.setContextMenu.called == uses_native_menu
    assert service._menu is menu

    if platform == "darwin":
        show_requested = Mock()
        service.showRequested.connect(show_requested)
        service._on_activated(original_tray_icon.Trigger)
        service._on_activated(original_tray_icon.Context)
        service._on_activated(original_tray_icon.DoubleClick)
        assert menu.popup.call_count == 2
        show_requested.assert_called_once()
