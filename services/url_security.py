from __future__ import annotations

import ipaddress
import os
import urllib.parse
from collections.abc import Iterable


class URLSecurityError(ValueError):
    pass


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def env_hosts(name: str) -> set[str]:
    raw = os.environ.get(name, "")
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def validate_https_url(
    url: str,
    *,
    allowed_hosts: Iterable[str] | None = None,
    allow_local: bool = False,
    allow_file: bool = False,
) -> str:
    text = str(url or "").strip()
    parsed = urllib.parse.urlparse(text)
    if allow_file and parsed.scheme == "file":
        if parsed.netloc not in {"", "localhost"}:
            raise URLSecurityError("file URL must be local")
        return text
    if parsed.scheme != "https":
        raise URLSecurityError("URL must use HTTPS")
    if parsed.username or parsed.password:
        raise URLSecurityError("URL credentials are not allowed")
    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise URLSecurityError("URL host is missing")
    if allowed_hosts and not host_matches(hostname, allowed_hosts):
        raise URLSecurityError(f"URL host is not allowed: {hostname}")
    if not allow_local and is_local_or_private_host(hostname):
        raise URLSecurityError("local/private network URLs are not allowed")
    return text


def host_matches(hostname: str, allowed_hosts: Iterable[str]) -> bool:
    host = hostname.strip().lower().rstrip(".")
    for raw_allowed in allowed_hosts:
        allowed = str(raw_allowed or "").strip().lower().rstrip(".")
        if not allowed:
            continue
        if allowed.startswith("*.") and host.endswith(allowed[1:]):
            return True
        if host == allowed:
            return True
    return False


def is_local_or_private_host(hostname: str) -> bool:
    host = hostname.strip().lower().rstrip(".")
    wildcard_ipv4 = ".".join(["0", "0", "0", "0"])
    if host in {"localhost", "0", wildcard_ipv4} or host.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(
        [
            ip.is_loopback,
            ip.is_private,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        ]
    )
