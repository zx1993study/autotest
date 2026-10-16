from __future__ import annotations

import json
from urllib.request import Request, urlopen

from app.core.exceptions import BusinessRuleError
from app.services.agent_node_service import AgentNodeService
from app.services.ai_model_service import AiModelResourceService
from app.utils.model_api_request import build_model_body, model_api_url, model_protocol
from app.utils.model_api_response import read_model_response


class AgentModelProxyService:
    """Only the selected model of a running task is accessible to an Agent."""

    def __init__(self, repository):
        self.repository = repository

    def authorize(self, task_id, token):
        task = self.repository.get("agent_tasks", task_id)
        if not task:
            raise BusinessRuleError("Agent task does not exist")
        return AgentNodeService(self.repository).verify_token(str((task.get("data") or {}).get("claimed_by") or ""), token)

    def completion(self, task_id, payload):
        task = self.repository.get("agent_tasks", task_id)
        if not task or task.get("status") != "running":
            raise BusinessRuleError("AI proxy requires a running task")
        context = ((task.get("data") or {}).get("payload") or {}).get("context") or {}
        snapshot = context.get("ai_model") or {}
        if not snapshot.get("model_id") or payload.stream:
            raise BusinessRuleError("This task does not allow the requested model operation")
        service = AiModelResourceService(self.repository)
        model = service.active_model(int(snapshot["model_id"]))
        config = model.get("data") or {}
        key = service.api_key(model)
        base = str(config.get("base_url") or "").rstrip("/")
        if not key:
            raise BusinessRuleError("Model endpoint or credential is not configured")
        body = payload.model_dump()
        body["model"] = config.get("model")
        body["stream"] = False
        protocol = model_protocol(config)
        body = build_model_body(body, protocol, config.get("reasoning_effort"))
        encoded = json.dumps(body).encode("utf-8")
        if len(encoded) > 5 * 1024 * 1024:
            raise BusinessRuleError("Model request exceeds 5 MiB")
        request = Request(model_api_url(base, protocol), data=encoded, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept": "text/event-stream" if protocol == "responses" else "application/json"}, method="POST")
        try:
            timeout = min(120, int(config.get("timeout_sec") or 60))
            with urlopen(request, timeout=timeout) as response:
                return read_model_response(response, protocol, timeout_sec=timeout)
        except Exception as exc:
            raise BusinessRuleError("Model provider request failed; credentials were not sent to the Agent") from exc
