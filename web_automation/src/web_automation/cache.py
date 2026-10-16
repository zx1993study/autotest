from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def cached_selector(step: dict[str, Any]) -> str:
    cache = step.get("ai_cache") if isinstance(step.get("ai_cache"), dict) else {}
    return str(cache.get("selector") or "").strip()


def cache_update(
    step: dict[str, Any],
    cache: dict[str, Any],
    *,
    target_url: str,
    source: str,
) -> dict[str, Any]:
    previous = step.get("ai_cache") if isinstance(step.get("ai_cache"), dict) else {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    origin_source = str(previous.get("source") or source) if source == "ai_cache" else source
    return {
        **previous,
        **cache,
        "selector": str(cache.get("selector") or previous.get("selector") or ""),
        "source": origin_source,
        "last_execution_source": source,
        "source_url": str(cache.get("source_url") or target_url),
        "success_count": _int(previous.get("success_count"), 0) + 1,
        "failure_count": 0,
        "last_success_at": now,
        "observed_at": str(cache.get("observed_at") or now),
    }


def cache_failure(step: dict[str, Any]) -> dict[str, Any]:
    previous = step.get("ai_cache") if isinstance(step.get("ai_cache"), dict) else {}
    return {
        **previous,
        "failure_count": _int(previous.get("failure_count"), 0) + 1,
        "last_failure_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
