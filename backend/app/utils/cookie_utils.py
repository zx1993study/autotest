from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


COOKIE_FIELDS = {"name", "value", "domain", "path", "expires", "httpOnly", "secure", "sameSite"}


def normalize_playwright_cookie(cookie: dict[str, Any], target_url: str) -> dict[str, Any]:
    normalized = {key: value for key, value in cookie.items() if key in COOKIE_FIELDS}
    normalized["name"] = str(normalized.get("name") or "")
    normalized["value"] = str(normalized.get("value") or "")
    if not normalized.get("path"):
        normalized["path"] = "/"
    if not normalized.get("domain"):
        parsed = urlparse(target_url)
        if parsed.hostname:
            normalized["domain"] = parsed.hostname

    expires = normalized.get("expires")
    try:
        expires_value = float(expires)
    except (TypeError, ValueError):
        expires_value = None
    if expires_value is not None and expires_value <= 0:
        normalized.pop("expires", None)

    return normalized


def normalize_playwright_cookies(cookies: Any, target_url: str) -> list[dict[str, Any]]:
    if not isinstance(cookies, list):
        return []
    return [
        normalized
        for normalized in (
            normalize_playwright_cookie(cookie, target_url)
            for cookie in cookies
            if isinstance(cookie, dict)
        )
        if normalized.get("name")
    ]
