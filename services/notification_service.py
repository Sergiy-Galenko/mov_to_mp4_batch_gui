from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class NotificationResult:
    target: str
    ok: bool
    message: str = ""


class NotificationService:
    """HTTP notifications for long batch jobs."""

    def send_batch_done(
        self,
        *,
        title: str,
        message: str,
        summary: Dict[str, Any],
        webhook_url: str = "",
        discord_webhook_url: str = "",
        telegram_bot_token: str = "",
        telegram_chat_id: str = "",
        timeout: float = 5.0,
    ) -> List[NotificationResult]:
        results: List[NotificationResult] = []
        if webhook_url.strip():
            payload = {"title": title, "message": message, "summary": dict(summary)}
            results.append(self._post_json(webhook_url.strip(), payload, "webhook", timeout))
        if discord_webhook_url.strip():
            payload = {
                "content": f"**{title}**\n{message}",
                "embeds": [{"title": title, "description": message, "fields": self._discord_fields(summary)}],
            }
            results.append(self._post_json(discord_webhook_url.strip(), payload, "discord", timeout))
        if telegram_bot_token.strip() and telegram_chat_id.strip():
            text = f"{title}\n{message}"
            results.append(self._send_telegram(telegram_bot_token.strip(), telegram_chat_id.strip(), text, timeout))
        return results

    def _discord_fields(self, summary: Dict[str, Any]) -> List[Dict[str, str]]:
        fields: List[Dict[str, str]] = []
        for key in ("completed", "failed", "skipped", "cancelled", "output_dir"):
            value = summary.get(key)
            if value in (None, ""):
                continue
            fields.append({"name": key, "value": str(value), "inline": key != "output_dir"})
        return fields

    def _send_telegram(self, token: str, chat_id: str, text: str, timeout: float) -> NotificationResult:
        encoded_token = urllib.parse.quote(token, safe=":")
        url = f"https://api.telegram.org/bot{encoded_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text[:4096]}
        return self._post_json(url, payload, "telegram", timeout)

    def _post_json(self, url: str, payload: Dict[str, Any], target: str, timeout: float) -> NotificationResult:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "MediaConverter/1.0"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = int(getattr(response, "status", 200) or 200)
                if 200 <= status < 300:
                    return NotificationResult(target, True, f"HTTP {status}")
                return NotificationResult(target, False, f"HTTP {status}")
        except urllib.error.HTTPError as exc:
            return NotificationResult(target, False, f"HTTP {exc.code}")
        except Exception as exc:
            return NotificationResult(target, False, str(exc))
