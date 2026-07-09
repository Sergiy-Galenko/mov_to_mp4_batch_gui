from __future__ import annotations

import hashlib
import hmac
import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass

from services.url_security import env_flag, env_hosts, validate_https_url


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

    def __init__(
        self,
        *,
        allowed_hosts: set[str] | None = None,
        manifest_secret: str | None = None,
        allow_file_urls: bool = False,
    ) -> None:
        self.allowed_hosts = allowed_hosts or env_hosts("MEDIA_CONVERTER_UPDATE_HOSTS")
        self.manifest_secret = str(manifest_secret or os.environ.get("MEDIA_CONVERTER_UPDATE_MANIFEST_SECRET") or "")
        self.allow_file_urls = allow_file_urls

    def check(self, manifest_url: str, current_version: str, *, timeout: float = 6.0) -> PaidUpdateInfo:
        url = str(manifest_url or "").strip()
        if not url:
            return PaidUpdateInfo(
                checked=True,
                current_version=current_version,
                message="Paid update manifest URL is not configured.",
            )
        try:
            validated_url = validate_https_url(
                url,
                allowed_hosts=self.allowed_hosts or None,
                allow_local=env_flag("MEDIA_CONVERTER_ALLOW_LOCAL_UPDATES"),
                allow_file=self.allow_file_urls,
            )
        except Exception as exc:
            return PaidUpdateInfo(
                checked=True,
                current_version=current_version,
                message=f"Update check blocked: {exc}",
            )
        if not self.manifest_secret:
            return PaidUpdateInfo(
                checked=True,
                current_version=current_version,
                message="Update manifest signing secret is not configured.",
            )
        try:
            with urllib.request.urlopen(validated_url, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return PaidUpdateInfo(
                checked=True,
                current_version=current_version,
                message=f"Update check failed: {exc}",
            )
        if not isinstance(payload, dict):
            return PaidUpdateInfo(checked=True, current_version=current_version, message="Update manifest is invalid.")
        if not self._verify_manifest_signature(payload):
            return PaidUpdateInfo(checked=True, current_version=current_version, message="Update manifest signature is invalid.")
        latest = str(payload.get("version") or "").strip()
        download_url = str(payload.get("download_url") or payload.get("url") or "").strip()
        if download_url:
            manifest_host = urllib.parse.urlparse(validated_url).hostname
            download_hosts = self.allowed_hosts or ({manifest_host} if manifest_host else None)
            try:
                download_url = validate_https_url(
                    download_url,
                    allowed_hosts=download_hosts,
                    allow_local=env_flag("MEDIA_CONVERTER_ALLOW_LOCAL_UPDATES"),
                )
            except Exception as exc:
                return PaidUpdateInfo(
                    checked=True,
                    current_version=current_version,
                    latest_version=latest,
                    message=f"Update download URL is blocked: {exc}",
                )
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

    def _verify_manifest_signature(self, payload: dict) -> bool:
        provided = str(payload.get("manifest_signature") or payload.get("signature") or "")
        if not provided:
            return False
        expected = self.sign_manifest(payload, self.manifest_secret)
        return hmac.compare_digest(provided, expected)

    @staticmethod
    def sign_manifest(payload: dict, secret: str) -> str:
        signing_payload = {key: value for key, value in payload.items() if key not in {"manifest_signature", "signature"}}
        raw = json.dumps(signing_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hmac.new(str(secret).encode("utf-8"), raw, hashlib.sha256).hexdigest()
