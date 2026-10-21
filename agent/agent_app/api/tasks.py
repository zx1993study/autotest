from __future__ import annotations

from typing import Any
import time
from urllib.error import HTTPError, URLError

from agent_app.api.client import AgentApiClient, AgentApiError
from agent_app.config import AgentConfig


class AgentTaskApi:
    """Remote API wrapper for claiming and reporting Agent tasks."""

    def __init__(self, client: AgentApiClient, config: AgentConfig) -> None:
        self.client = client
        self.config = config

    def claim_next(self) -> dict[str, Any] | None:
        return self.client.post(
            "/agent/runtime/tasks/claim",
            {
                "node_key": self.config.node_key,
                "capabilities": list(self.config.capabilities),
            },
        )

    def report(
        self,
        task_id: int,
        status: str,
        result: dict[str, Any],
        error: str | None = None,
        lease_token: str | None = None,
    ) -> dict[str, Any] | None:
        return self.client.post(
            f"/agent/runtime/tasks/{task_id}/report",
            {
                "node_key": self.config.node_key,
                "status": status,
                "result": result,
                "error": error,
                "lease_token": lease_token,
            },
        )

    def renew(self, task_id: int, lease_token: str | None):
        return self.client.post(f"/agent/runtime/tasks/{task_id}/renew", {"node_key": self.config.node_key, "lease_token": lease_token})

    def app_exchange(self,task_id,lease_token,operation,payload):
        if operation not in {'state','observation','action','connection'}:
            raise ValueError('Unsupported mobile exchange')
        return self.client.post(f'/agent/runtime/tasks/{task_id}/app-{operation}',
            {'node_key':self.config.node_key,'lease_token':lease_token,**payload})

    def vision_step(self, task_id, lease_token, data):
        return self.client.post(f"/agent/runtime/tasks/{task_id}/vision/step", {"node_key": self.config.node_key, "lease_token": lease_token, **data})

    def vision_state(self, task_id, lease_token):
        return self.client.post(f"/agent/runtime/tasks/{task_id}/vision/state", {"node_key": self.config.node_key, "lease_token": lease_token})

    def vision_cancel(self, task_id, lease_token):
        return self.client.post(f"/agent/runtime/tasks/{task_id}/vision/cancel", {"node_key": self.config.node_key, "lease_token": lease_token})

    def web_state(self, task_id, lease_token, data=None):
        for attempt in range(3):
            try:
                return self.client.post(f'/agent/runtime/tasks/{task_id}/web-state', {'node_key': self.config.node_key, 'lease_token': lease_token, **(data or {})})
            except (ConnectionError, TimeoutError, AgentApiError) as exc:
                transport_failure = not isinstance(exc, AgentApiError) or (isinstance(exc.__cause__, URLError) and not isinstance(exc.__cause__, HTTPError))
                # Retry only read-only status polling, never a write or a rejected lease.
                if data is not None or not transport_failure or attempt == 2:
                    raise
                time.sleep(0.25 * (attempt + 1))

    def case_inputs(self, task_id, lease_token):
        return self.client.post(f'/agent/runtime/tasks/{task_id}/case-inputs', {'node_key':self.config.node_key, 'lease_token':lease_token})

    def browser_window_exchange(self, task_id, lease_token, window):
        client = AgentApiClient(self.client.base_url, self.config.token, timeout_sec=5)
        return client.post(f"/agent/runtime/tasks/{task_id}/browser-window", {
            "node_key": self.config.node_key, "lease_token": lease_token, "window": window,
        })

    def prepare_artifacts(self, task_id: int, report: dict) -> None:
        for record in report.get("result", {}).get("records", []):
            data = record.get("data") or {}
            path = data.get("video_local_path")
            if not path:
                continue
            artifact = self.client.upload(f"/agent/runtime/tasks/{task_id}/video?node_key={self.config.node_key}", path, self.config.artifacts_dir)
            data.update(artifact)
            data.pop("video_local_path", None)

    def auth_context(self, task_id: int, snapshot_id: str | None = None) -> dict[str, Any]:
        """Consume a task-scoped auth snapshot from the platform."""

        return self.client.post(
            f"/agent/runtime/tasks/{task_id}/auth-context",
            {
                "node_key": self.config.node_key,
                "snapshot_id": snapshot_id,
            },
        )

    def ai_model_context(self, task_id: int, snapshot_id: str | None = None) -> dict[str, Any]:
        """Consume a task-scoped AI model secret snapshot from the platform."""

        return self.client.post(
            f"/agent/runtime/tasks/{task_id}/ai-model-context",
            {
                "node_key": self.config.node_key,
                "snapshot_id": snapshot_id,
            },
        )
