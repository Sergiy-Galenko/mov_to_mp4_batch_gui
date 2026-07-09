from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass


@dataclass
class PaidUpdateInfo:
    checked: bool = False
    available: bool = False
    current_version: str = ""
    latest_version: str = ""
    download_url: str = ""
    message: str = ""


class PaidUpdateService:
    """Checks a simple JSON update manifest for paid builds."""

    def check(self, manifest_url: str, current_version: str, *, timeout: float = 6.0) -> PaidUpdateInfo:
        url = str(manifest_url or "").strip()
        if not url:
            return PaidUpdateInfo(
                checked=True,
                current_version=current_version,
                message="Paid update manifest URL is not configured.",
            )
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return PaidUpdateInfo(
                checked=True,
                current_version=current_version,
                message=f"Update check failed: {exc}",
            )
        if not isinstance(payload, dict):
            return PaidUpdateInfo(checked=True, current_version=current_version, message="Update manifest is invalid.")
        latest = str(payload.get("version") or "").strip()
        download_url = str(payload.get("download_url") or payload.get("url") or "").strip()
        available = bool(latest) and self._version_tuple(latest) > self._version_tuple(current_version)
        message = f"Update available: {latest}" if available else "Paid build is up to date."
        if available and not download_url:
            message = f"Update available: {latest}, but download URL is missing."
        return PaidUpdateInfo(
            checked=True,
            available=available,
            current_version=current_version,
            latest_version=latest,
            download_url=download_url,
            message=message,
        )

    def _version_tuple(self, version: str) -> tuple[int, ...]:
        parts = []
        for chunk in str(version or "").replace("-", ".").split("."):
            digits = "".join(ch for ch in chunk if ch.isdigit())
            parts.append(int(digits or 0))
        return tuple(parts or [0])
