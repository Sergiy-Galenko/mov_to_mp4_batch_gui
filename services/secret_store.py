from __future__ import annotations

import base64
import ctypes
import sys
from ctypes import wintypes

DPAPI_PREFIX = "dpapi:"


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def protect_text(value: str) -> str:
    text = str(value or "")
    if not text or text.startswith(DPAPI_PREFIX) or sys.platform != "win32":
        return text
    try:
        raw = text.encode("utf-8")
        in_blob, buffer = _blob_from_bytes(raw)
        out_blob = _DataBlob()
        if not ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(in_blob),
            None,
            None,
            None,
            None,
            0x01,
            ctypes.byref(out_blob),
        ):
            return text
        try:
            encrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)
        return DPAPI_PREFIX + base64.b64encode(encrypted).decode("ascii")
    except Exception:
        return text
    finally:
        _ = locals().get("buffer")


def unprotect_text(value: str) -> str:
    text = str(value or "")
    if not text.startswith(DPAPI_PREFIX) or sys.platform != "win32":
        return text
    try:
        raw = base64.b64decode(text[len(DPAPI_PREFIX) :])
        in_blob, buffer = _blob_from_bytes(raw)
        out_blob = _DataBlob()
        if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(in_blob),
            None,
            None,
            None,
            None,
            0x01,
            ctypes.byref(out_blob),
        ):
            return ""
        try:
            decrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)
        return decrypted.decode("utf-8")
    except Exception:
        return ""
    finally:
        _ = locals().get("buffer")


def _blob_from_bytes(data: bytes) -> tuple[_DataBlob, ctypes.Array]:
    buffer = ctypes.create_string_buffer(data)
    blob = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    return blob, buffer
