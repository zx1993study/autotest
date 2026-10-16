from __future__ import annotations

from datetime import datetime, timedelta, timezone
from secrets import compare_digest

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError


LEASE_SECONDS = 120


def lease_expiry() -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=LEASE_SECONDS)).isoformat(timespec="seconds")


class AgentTaskLeaseService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def owned_task(self, task_id: int, node_key: str, lease_token: str | None = None):
        task = self.repository.get("agent_tasks", task_id)
        if not task:
            raise ResourceNotFoundError("Agent task does not exist")
        data = task.get("data") or {}
        if data.get("claimed_by") != node_key:
            raise BusinessRuleError("Task belongs to another node")
        expected = str(data.get("lease_token") or "")
        if expected and not compare_digest(expected, str(lease_token or "")):
            raise BusinessRuleError("Invalid task lease")
        return task

    def renew(self, task_id, payload):
        task = self.owned_task(task_id, payload.node_key, payload.lease_token)
        if task.get("status") != "running":
            raise BusinessRuleError("Only running tasks can renew their lease")
        return self.repository.patch_running_agent_task(task_id, payload.node_key, {"lease_expires_at": lease_expiry()})
