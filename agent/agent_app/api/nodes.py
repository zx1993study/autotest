from __future__ import annotations

from typing import Any

from agent_app.api.client import AgentApiClient
from agent_app.config import AgentConfig


class AgentNodeApi:
    """Remote API wrapper for Agent node registration and heartbeat."""

    def __init__(self, client: AgentApiClient, config: AgentConfig) -> None:
        self.client = client
        self.config = config

    def register(self) -> dict[str, Any]:
        return self.client.post(
            "/agent/runtime/register",
            {
                "node_key": self.config.node_key,
                "name": self.config.node_name,
                "version": self.config.version,
                "capabilities": list(self.config.capabilities),
                "system": self.config.system_info,
            },
        )

    def heartbeat(self, status: str = "online", current_task_id: int | None = None) -> dict[str, Any]:
        return self.client.post(
            f"/agent/runtime/nodes/{self.config.node_key}/heartbeat",
            {
                "status": status,
                "version": self.config.version,
                "capabilities": list(self.config.capabilities),
                "current_task_id": current_task_id,
                "system": self.config.system_info,
            },
        )
