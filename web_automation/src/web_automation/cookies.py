from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


COOKIE_FIELDS = {"name", "value", "domain", "path", "expires", "httpOnly", "secure", "sameSite", "url"}


def normalize_playwright_cookies(cookies: Any, target_url: str) -> list[dict[str, Any]]:
    if not isinstance(cookies, list):
        return []
    return [
        normalized
        for item in cookies
        if isinstance(item, dict)
        for normalized in [_normalize_cookie(item, target_url)]
        if normalized
    ]


def _normalize_cookie(cookie: dict[str, Any], target_url: str) -> dict[str, Any] | None:
    normalized = {key: value for key, value in cookie.items() if key in COOKIE_FIELDS and value is not None}
    name = str(normalized.get("name") or "").strip()
    if not name:
        return None
    normalized["name"] = name
    normalized["value"] = str(normalized.get("value") or "")
    if not normalized.get("url") and not normalized.get("domain"):
        parsed = urlparse(target_url)
        if parsed.scheme and parsed.netloc:
            normalized["url"] = f"{parsed.scheme}://{parsed.netloc}"
    if normalized.get("domain") and not normalized.get("path"):
        normalized["path"] = "/"
    try:
        if "expires" in normalized and float(normalized["expires"]) <= 0:
            normalized.pop("expires", None)
    except (TypeError, ValueError):
        normalized.pop("expires", None)
    return normalized

