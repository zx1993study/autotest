from __future__ import annotations

from datetime import datetime, timezone
from secrets import token_urlsafe
from typing import Any

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.enums.business import AgentNodeStatusEnum
from app.repositories.interfaces import ResourceRepository
from app.schemas.agent import AgentHeartbeatRequest, AgentRegisterRequest, AgentTokenProvisionRequest
from app.utils.security_utils import hash_password, verify_password


AGENT_NODE_TABLE = "agent_nodes"
AGENT_TOKEN_HASH_KEY = "agent_token_hash"
AGENT_TOKEN_PREFIX = "agt_"


class AgentNodeService:
    """Manage installed local execution agent nodes."""

    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def register(self, payload: AgentRegisterRequest) -> dict[str, Any]:
        """Create or update an agent node by stable node key."""

        now = self._now()
        data = {
            "node_key": payload.node_key,
            "agent_status": AgentNodeStatusEnum.ONLINE.code,
            "version": payload.version or "",
            "capabilities": payload.capabilities,
            "system": payload.system,
            "last_seen_at": now,
        }
        existing = self.get_by_key(payload.node_key)
        if existing:
            updated = self.repository.update(
                AGENT_NODE_TABLE,
                int(existing["id"]),
                {
                    "name": payload.name,
                    "status": "active",
                    "data": {**self._data(existing), **data},
                },
            ) or existing
            return self._sanitize_node(updated)
        created = self.repository.create(
            AGENT_NODE_TABLE,
            {
                "name": payload.name,
                "status": "active",
                "data": data,
            },
        )
        return self._sanitize_node(created)

    def provision_token(self, payload: AgentTokenProvisionRequest) -> dict[str, Any]:
        """Create or rotate a node token before the local Agent starts.

        The platform stores only a salted hash. The plaintext value is returned
        once so operators can paste it into the local Agent config or installer.
        """

        token = self._new_agent_token()
        now = self._now()
        existing = self.get_by_key(payload.node_key)
        existing_data = self._data(existing) if existing else {}
        data = {
            "node_key": payload.node_key,
            "agent_status": existing_data.get("agent_status") or AgentNodeStatusEnum.OFFLINE.code,
            "version": payload.version or "",
            "capabilities": payload.capabilities,
            "system": payload.system,
            "token_issued_at": now,
            "token_last4": token[-4:],
            AGENT_TOKEN_HASH_KEY: hash_password(token),
        }
        if existing:
            node = self.repository.update(
                AGENT_NODE_TABLE,
                int(existing["id"]),
                {
                    "name": payload.name,
                    "status": "active",
                    "data": {**self._data(existing), **data},
                },
            ) or existing
        else:
            node = self.repository.create(
                AGENT_NODE_TABLE,
                {
                    "name": payload.name,
                    "status": "active",
                    "data": data,
                },
            )
        return {"node": self._sanitize_node(node), "agent_token": token}

    def reset_token(self, node_id: int) -> dict[str, Any]:
        """Rotate a node token and return the new plaintext token once."""

        node = self.repository.get(AGENT_NODE_TABLE, node_id)
        if not node:
            raise ResourceNotFoundError("未找到执行节点")
        token = self._new_agent_token()
        data = {
            **self._data(node),
            "token_issued_at": self._now(),
            "token_last4": token[-4:],
            AGENT_TOKEN_HASH_KEY: hash_password(token),
        }
        updated = self.repository.update(AGENT_NODE_TABLE, node_id, {"data": data}) or node
        return {"node": self._sanitize_node(updated), "agent_token": token}

    def verify_token(self, node_key: str, token: str) -> dict[str, Any]:
        """Return the node when the supplied Agent token is valid."""

        if not token:
            raise BusinessRuleError("请提供 Agent 专用 Token")
        node = self.get_by_key(node_key)
        if not node:
            raise BusinessRuleError("未找到执行节点，请先在平台生成 Agent Token")
        token_hash = str(self._data(node).get(AGENT_TOKEN_HASH_KEY) or "")
        if not token_hash or not verify_password(token, token_hash):
            raise BusinessRuleError("Agent Token 无效，请在平台重新生成")
        return self._sanitize_node(node)

    def heartbeat(self, node_key: str, payload: AgentHeartbeatRequest) -> dict[str, Any]:
        """Refresh runtime metadata for an existing agent node."""

        node = self.get_by_key(node_key)
        if not node:
            register_payload = AgentRegisterRequest(
                node_key=node_key,
                name=node_key,
                version=payload.version,
                capabilities=payload.capabilities or [],
                system=payload.system or {},
            )
            node = self.register(register_payload)
        data = {
            **self._data(node),
            "agent_status": payload.status.code,
            "last_seen_at": self._now(),
            "current_task_id": payload.current_task_id,
        }
        if payload.version is not None:
            data["version"] = payload.version
        if payload.capabilities is not None:
            data["capabilities"] = payload.capabilities
        if payload.system is not None:
            data["system"] = payload.system
        updated = self.repository.update(
            AGENT_NODE_TABLE,
            int(node["id"]),
            {"data": data, "status": "active"},
        ) or node
        return self._sanitize_node(updated)

    def list_nodes(self, page: int = 1, page_size: int = 100) -> tuple[list[dict[str, Any]], int]:
        """Return registered agent nodes for management pages."""

        rows, total = self.repository.list(AGENT_NODE_TABLE, page=page, page_size=page_size)
        return [self._sanitize_node(row) for row in rows], total

    def set_default_local_headed(self, node_id: int) -> dict[str, Any]:
        """Mark one node as the default target for local headed Web execution."""

        target = self.repository.get(AGENT_NODE_TABLE, node_id)
        if not target:
            raise ResourceNotFoundError("未找到执行节点")
        rows, _ = self.repository.list(AGENT_NODE_TABLE, page=1, page_size=10000)
        result = target
        for row in rows:
            data = {**self._data(row), "default_local_headed": int(row["id"]) == node_id}
            updated = self.repository.update(AGENT_NODE_TABLE, int(row["id"]), {"data": data})
            if int(row["id"]) == node_id:
                result = updated or row
        return self._sanitize_node(result)

    def get_by_key(self, node_key: str) -> dict[str, Any] | None:
        """Find a node by its stable local installation key."""

        rows, _ = self.repository.list(
            AGENT_NODE_TABLE,
            page=1,
            page_size=1,
            data_filters={"node_key": node_key},
        )
        return rows[0] if rows else None

    def _data(self, node: dict[str, Any]) -> dict[str, Any]:
        data = node.get("data")
        return data if isinstance(data, dict) else {}

    def _sanitize_node(self, node: dict[str, Any]) -> dict[str, Any]:
        sanitized = {**node}
        data = {**self._data(node)}
        data.pop(AGENT_TOKEN_HASH_KEY, None)
        data["has_agent_token"] = bool(self._data(node).get(AGENT_TOKEN_HASH_KEY))
        sanitized["data"] = data
        return sanitized

    def _new_agent_token(self) -> str:
        return f"{AGENT_TOKEN_PREFIX}{token_urlsafe(32)}"

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def list_options(self):
        rows, _ = self.list_nodes(1, 10000)
        return [{"id": row["id"], "name": row.get("name"), "data": {"node_key": (row.get("data") or {}).get("node_key")}} for row in rows if row.get("status") == "active"]

