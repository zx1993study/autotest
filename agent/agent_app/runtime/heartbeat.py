from __future__ import annotations

import time

from agent_app.api.nodes import AgentNodeApi


class HeartbeatTicker:
    """Send heartbeat updates at a bounded interval."""

    def __init__(self, api: AgentNodeApi, interval_sec: int) -> None:
        self.api = api
        self.interval_sec = max(5, interval_sec)
        self.last_sent_at = 0.0

    def send_if_due(self, status: str = "online", current_task_id: int | None = None) -> None:
        now = time.monotonic()
        if now - self.last_sent_at < self.interval_sec:
            return
        self.api.heartbeat(status=status, current_task_id=current_task_id)
        self.last_sent_at = now

    def send_now(self, status: str = "online", current_task_id: int | None = None) -> None:
        self.api.heartbeat(status=status, current_task_id=current_task_id)
        self.last_sent_at = time.monotonic()

