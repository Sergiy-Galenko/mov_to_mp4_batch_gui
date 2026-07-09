from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


TRIAL_DAYS = 14
LICENSE_KEY_PREFIX = "MC-PRO"
DEFAULT_LICENSE_FEATURES = [
    "ai_blur",
    "batch_automation",
    "cloud_upload",
    "advanced_reports",
    "commercial_export",
    "paid_updates",
]


@dataclass
class LicenseInfo:
    status: str = "unlicensed"
    plan: str = "Free"
    holder: str = ""
    license_id: str = ""
    expires_at: str = ""
    features: List[str] = field(default_factory=list)
    source: str = ""
    message: str = ""
    trial_started_at: float = 0.0
    trial_ends_at: float = 0.0

    @property
    def is_license_active(self) -> bool:
        return self.status == "licensed"

    @property
    def is_trial_active(self) -> bool:
        return self.status == "trial"

    @property
    def pro_enabled(self) -> bool:
        return self.status in {"licensed", "trial"}

    @property
    def commercial_export_allowed(self) -> bool:
        return self.status == "licensed" and "commercial_export" in set(self.features)


class LicenseService:
    """Offline-verifiable licensing and trial state."""

    def __init__(self, secret: Optional[str] = None, now_func=time.time) -> None:
        self.secret = (secret or os.environ.get("MEDIA_CONVERTER_LICENSE_SECRET") or "media-converter-dev-license-secret").encode("utf-8")
        self.now_func = now_func

    def info_from_state(self, state: Dict[str, Any]) -> LicenseInfo:
        payload = state.get("license_payload")
        if isinstance(payload, dict):
            info = self.validate_package(payload, source=str(payload.get("source") or "license"))
            if info.is_license_active:
                return info
        trial_started = float(state.get("trial_started_at") or 0.0)
        trial = self.trial_info(trial_started)
        if trial.is_trial_active:
            return trial
        if isinstance(payload, dict):
            return self.validate_package(payload, source=str(payload.get("source") or "license"))
        return trial if trial.status == "trial_expired" else LicenseInfo(message="No license activated.")

    def trial_info(self, started_at: float) -> LicenseInfo:
        if started_at <= 0:
            return LicenseInfo(status="unlicensed", plan="Free", message="Trial not started.")
        ends_at = started_at + TRIAL_DAYS * 86400
        if self.now_func() <= ends_at:
            return LicenseInfo(
                status="trial",
                plan="Trial",
                features=list(DEFAULT_LICENSE_FEATURES),
                source="trial",
                message=f"Trial active: {self.trial_days_remaining(started_at)} day(s) remaining.",
                trial_started_at=started_at,
                trial_ends_at=ends_at,
            )
        return LicenseInfo(
            status="trial_expired",
            plan="Trial expired",
            source="trial",
            message="Trial expired.",
            trial_started_at=started_at,
            trial_ends_at=ends_at,
        )

    def start_trial(self, state: Dict[str, Any]) -> Dict[str, Any]:
        started = float(state.get("trial_started_at") or 0.0)
        if started > 0:
            return dict(state)
        updated = dict(state)
        updated["trial_started_at"] = self.now_func()
        return updated

    def trial_days_remaining(self, started_at: float) -> int:
        if started_at <= 0:
            return 0
        remaining = int((started_at + TRIAL_DAYS * 86400 - self.now_func() + 86399) // 86400)
        return max(0, remaining)

    def activate_key(self, key: str) -> Dict[str, Any]:
        token = str(key or "").strip()
        if not token.startswith(LICENSE_KEY_PREFIX + "-"):
            raise ValueError("Unsupported license key format.")
        encoded = token[len(LICENSE_KEY_PREFIX) + 1 :].strip()
        try:
            raw = base64.urlsafe_b64decode(self._pad_base64(encoded)).decode("utf-8")
            payload = json.loads(raw)
        except Exception as exc:
            raise ValueError("License key payload is invalid.") from exc
        info = self.validate_package(payload, source="key")
        if not info.is_license_active:
            raise ValueError(info.message or "License key is not active.")
        payload = dict(payload)
        payload["source"] = "key"
        return payload

    def load_offline_file(self, path: Path) -> Dict[str, Any]:
        try:
            payload = json.loads(path.expanduser().read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"Cannot read offline license file: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("Offline license file must contain a JSON object.")
        info = self.validate_package(payload, source="offline")
        if not info.is_license_active:
            raise ValueError(info.message or "Offline license is not active.")
        payload = dict(payload)
        payload["source"] = "offline"
        return payload

    def validate_package(self, payload: Dict[str, Any], *, source: str = "license") -> LicenseInfo:
        if not isinstance(payload, dict):
            return LicenseInfo(status="invalid", source=source, message="License payload is invalid.")
        expected = self._signature(payload)
        provided = str(payload.get("signature") or "")
        if not provided or not hmac.compare_digest(provided, expected):
            return LicenseInfo(status="invalid", source=source, message="License signature is invalid.")
        expires_at = str(payload.get("expires_at") or "").strip()
        if expires_at and self._is_expired(expires_at):
            return LicenseInfo(
                status="expired",
                plan=str(payload.get("plan") or "Expired"),
                holder=str(payload.get("holder") or ""),
                license_id=str(payload.get("license_id") or ""),
                expires_at=expires_at,
                features=self._features(payload.get("features")),
                source=source,
                message="License expired.",
            )
        features = self._features(payload.get("features"))
        return LicenseInfo(
            status="licensed",
            plan=str(payload.get("plan") or "Commercial"),
            holder=str(payload.get("holder") or ""),
            license_id=str(payload.get("license_id") or ""),
            expires_at=expires_at,
            features=features,
            source=source,
            message="Commercial license active.",
        )

    def feature_allowed(self, feature: str, state: Dict[str, Any]) -> bool:
        info = self.info_from_state(state)
        return info.pro_enabled and feature in set(info.features)

    def create_license_package(
        self,
        *,
        holder: str,
        plan: str = "Commercial",
        expires_at: str = "",
        features: Optional[Iterable[str]] = None,
        license_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "version": 1,
            "license_id": license_id or str(uuid.uuid4()),
            "holder": holder,
            "plan": plan,
            "expires_at": expires_at,
            "features": list(features or DEFAULT_LICENSE_FEATURES),
            "issued_at": time.strftime("%Y-%m-%d", time.gmtime(self.now_func())),
        }
        payload["signature"] = self._signature(payload)
        return payload

    def encode_license_key(self, payload: Dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
        return f"{LICENSE_KEY_PREFIX}-{encoded}"

    def _features(self, raw: Any) -> List[str]:
        if not isinstance(raw, list):
            return list(DEFAULT_LICENSE_FEATURES)
        values = [str(item).strip() for item in raw if str(item or "").strip()]
        return values or list(DEFAULT_LICENSE_FEATURES)

    def _signature(self, payload: Dict[str, Any]) -> str:
        signing_payload = {key: value for key, value in payload.items() if key not in {"signature", "source"}}
        raw = json.dumps(signing_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hmac.new(self.secret, raw, hashlib.sha256).hexdigest()

    def _is_expired(self, expires_at: str) -> bool:
        try:
            expiry = time.strptime(expires_at, "%Y-%m-%d")
            expiry_ts = time.mktime(expiry) + 86399
            return self.now_func() > expiry_ts
        except Exception:
            return False

    def _pad_base64(self, value: str) -> bytes:
        text = str(value or "").strip()
        text += "=" * (-len(text) % 4)
        return text.encode("ascii")
