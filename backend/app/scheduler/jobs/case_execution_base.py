from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlparse

from app.repositories.interfaces import ResourceRepository
from web_automation.dynamic_values import prepare_dynamic_execution


class CaseExecutionBase:
    """Shared helpers for scheduler-owned test-case executors."""

    def __init__(self, case_type: str, repository: ResourceRepository) -> None:
        self.case_type = case_type
        self.repository = repository

    def case_data(self, case: dict[str, Any]) -> dict[str, Any]:
        data = case.get("data")
        return data if isinstance(data, dict) else {}

    def prepare_execution(self, case: dict[str, Any], payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        resolved_case, resolved_payload, _ = prepare_dynamic_execution(case, payload)
        return resolved_case, resolved_payload

    def case_assertions(self, case: dict[str, Any]) -> list[dict[str, Any]]:
        assertions = case.get("assertions") or self.case_data(case).get("assertions")
        if not isinstance(assertions, list):
            return []
        return [item for item in assertions if isinstance(item, dict)]

    def project_base_url(self, project_id: Any) -> str:
        if not project_id:
            return ""
        project = self.repository.get("projects", int(project_id))
        data = project.get("data") if project else {}
        value = (data or {}).get("base_url") or (data or {}).get("project_url") or (data or {}).get("url") or ""
        return str(value).strip()

    def join_url(self, base_url: str, path: str, api_base_path: str = "") -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        base = base_url.rstrip("/")
        path_value = "/" + path.lstrip("/")
        prefix = self.clean_path(api_base_path)
        if prefix and path_value != prefix and not path_value.startswith(f"{prefix}/"):
            path_value = f"{prefix}{path_value}"
        base_path = urlparse(base).path.rstrip("/")
        if prefix and base_path == prefix and path_value.startswith(prefix):
            path_value = path_value[len(prefix) :] or "/"
        return f"{base}{path_value}"

    def clean_path(self, value: str) -> str:
        normalized = value.strip().strip("/")
        return f"/{normalized}" if normalized else ""

    def duration_ms(self, started_at: float) -> int:
        return int((time.perf_counter() - started_at) * 1000)

    def to_int(self, value: Any, default: int | None = None) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def is_truthy(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "是", "截图", "跳过"}
