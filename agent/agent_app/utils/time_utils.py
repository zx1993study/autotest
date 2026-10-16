from __future__ import annotations

import time


def duration_ms(started_at: float) -> int:
    """Return elapsed milliseconds for monotonic start time."""

    return int((time.perf_counter() - started_at) * 1000)


def now_millis() -> int:
    """Return current wall-clock milliseconds for filenames."""

    return int(time.time() * 1000)
