from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def event(name: str, **data: Any) -> dict[str, Any]:
    return {
        "event": name,
        "occurred_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        **data,
    }

