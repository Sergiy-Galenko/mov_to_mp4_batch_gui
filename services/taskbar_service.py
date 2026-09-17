"""Windows Taskbar Progress (ITaskbarList3) integration for PySide6."""

from __future__ import annotations

import sys
from typing import Any

# Windows Taskbar Progress Flags
TBPF_NOPROGRESS = 0x0
TBPF_INDETEREINATE = 0x1
TBPF_NORMAL = 0x2
TBPF_ERROR = 0x4
TBPF_OAUSED = 0x8


class TaskbarService:
    """Provides Windows 7/10/11 taskbar progress indicator integration."""

    def __init__(self, hwnd: int | None = None) -> None:
        self._hwnd = hwnd
        self._taskbar: Any = None
        self._init_taskbar()

    def set_hwnd(self, hwnd: int) -> None:
        self._hwnd = hwnd
        self._init_taskbar()

    def _init_taskbar(self) -> None:
        if sys.platform != "win32" or not self._hwnd:
            return
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [
                    ("Data1", wintypes.DWORD),
                    ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD),
                    ("Data4", wintypes.BYTE * 8),
                ]

            CLSID_TaskbarList = GUID(0x56FDF344, 0xFD6D, 0x11D0, (wintypes.BYTE * 8)(0x95, 0x8A, 0x00, 0x60, 0x97, 0xC9, 0xA0, 0x90))
            IID_ITaskbarList3 = GUID(0xEA1AFB91, 0x9E28, 0x4B86, (wintypes.BYTE * 8)(0x90, 0xE9, 0x9E, 0x9F, 0x8A, 0x5E, 0xEF, 0xAF))

            ole32 = ctypes.windll.ole32
            ole32.CoInitialize(None)

            taskbar = ctypes.c_void_p()
            hr = ole32.CoCreateInstance(
                ctypes.byref(CLSID_TaskbarList),
                None,
                1,
                ctypes.byref(IID_ITaskbarList3),
                ctypes.byref(taskbar),
            )
            if hr == 0 and taskbar.value:
                self._taskbar = taskbar
        except Exception:
            self._taskbar = None

    def set_progress_state(self, state: int) -> None:
        if not self._taskbar or not self._hwnd:
            return
        try:
            import ctypes

            vtable = ctypes.cast(self._taskbar, ctypes.POINTER(ctypes.c_void_p))[0]
            vt_ptr = ctypes.cast(vtable, ctypes.POINTER(ctypes.c_void_p))
            func_type = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int)
            func = func_type(vt_ptr[10])
            func(self._taskbar, ctypes.c_void_p(self._hwnd), state)
        except Exception:
            pass

    def set_progress_value(self, completed: int, total: int = 100) -> None:
        if not self._taskbar or not self._hwnd:
            return
        try:
            import ctypes

            vtable = ctypes.cast(self._taskbar, ctypes.POINTER(ctypes.c_void_p))[0]
            vt_ptr = ctypes.cast(vtable, ctypes.POINTER(ctypes.c_void_p))
            func_type = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulonglong, ctypes.c_ulonglong)
            func = func_type(vt_ptr[9])
            func(self._taskbar, ctypes.c_void_p(self._hwnd), max(0, completed), max(1, total))
        except Exception:
            pass

    def clear_progress(self) -> None:
        self.set_progress_state(TBPF_NOPROGRESS)

    def set_running_progress(self, ratio: float) -> None:
        val = int(max(0.0, min(1.0, ratio)) * 1000)
        self.set_progress_state(TBPF_NORMAL)
        self.set_progress_value(val, 1000)

    def set_paused(self) -> None:
        self.set_progress_state(TBPF_OAUSED)

    def set_error(self) -> None:
        self.set_progress_state(TBPF_ERROR)
