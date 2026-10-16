from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def normalize_playwright_cookies(cookies: list[dict[str, Any]], target_url: str) -> list[dict[str, Any]]:
    """Normalize stored cookies for Playwright context import."""

    return [
        normalized
        for cookie in cookies
        if isinstance(cookie, dict)
        for normalized in [_normalize_cookie(cookie, target_url)]
        if normalized
    ]


def _normalize_cookie(cookie: dict[str, Any], target_url: str) -> dict[str, Any] | None:
    name = str(cookie.get("name") or "").strip()
    if not name:
        return None
    value = str(cookie.get("value") or "")
    normalized = {key: item for key, item in cookie.items() if item is not None}
    normalized["name"] = name
    normalized["value"] = value
    if normalized.get("url") or normalized.get("domain"):
        return normalized
    parsed = urlparse(target_url)
    if parsed.scheme and parsed.netloc:
        normalized["url"] = f"{parsed.scheme}://{parsed.netloc}"
    return normalized

