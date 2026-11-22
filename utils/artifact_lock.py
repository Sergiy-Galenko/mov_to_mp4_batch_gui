"""Shared reader / exclusive eviction locks on POSIX and Windows."""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def artifact_lock(path: Path, *, shared: bool, timeout: float = 600):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if path.stat().st_size == 0:
            handle.write(b"0")
            handle.flush()
        if os.name == "nt":
            import ctypes
            import msvcrt
            from ctypes import wintypes

            class Overlapped(ctypes.Structure):
                _fields_ = [
                    ("Internal", ctypes.c_size_t),
                    ("InternalHigh", ctypes.c_size_t),
                    ("Offset", wintypes.DWORD),
                    ("OffsetHigh", wintypes.DWORD),
                    ("hEvent", wintypes.HANDLE),
                ]

            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.LockFileEx.argtypes = [
                wintypes.HANDLE,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.DWORD,
                ctypes.POINTER(Overlapped),
            ]
            kernel.LockFileEx.restype = wintypes.BOOL
            kernel.UnlockFileEx.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(Overlapped)]
            kernel.UnlockFileEx.restype = wintypes.BOOL
            descriptor = msvcrt.get_osfhandle(handle.fileno())
            overlapped = Overlapped()

            def acquire():
                if not kernel.LockFileEx(descriptor, 1 if shared else 3, 0, 1, 0, ctypes.byref(overlapped)):
                    code = ctypes.get_last_error()
                    if code == 33:
                        return False
                    raise ctypes.WinError(code)
                return True

            def release():
                if not kernel.UnlockFileEx(descriptor, 0, 1, 0, ctypes.byref(overlapped)):
                    raise ctypes.WinError(ctypes.get_last_error())
        else:
            import fcntl

            def acquire():
                try:
                    fcntl.flock(handle, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
                    return True
                except BlockingIOError:
                    return False

            def release():
                fcntl.flock(handle, fcntl.LOCK_UN)

        deadline = time.monotonic() + timeout
        while not acquire():
            if time.monotonic() >= deadline:
                raise TimeoutError("Cache artifact is currently in use")
            time.sleep(0.05)
        try:
            yield
        finally:
            release()
