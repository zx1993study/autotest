from __future__ import annotations

import threading
from collections.abc import Callable


def start_daemon_job(name: str, job: Callable[[], None]) -> None:
    """Start a lightweight in-process background job.

    This helper is intentionally small: job modules remain responsible for
    opening their own infrastructure resources and delegating business work to
    service-layer methods.
    """

    thread = threading.Thread(target=job, name=name, daemon=True)
    thread.start()
