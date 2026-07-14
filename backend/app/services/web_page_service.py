from __future__ import annotations

from typing import Any

from app.repositories.interfaces import ResourceRepository
from app.services.resource_service import ResourceService


class WebPageResourceService(ResourceService):
    def __init__(self, repository: ResourceRepository) -> None:
        super().__init__("web_pages", repository)

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        return super().create(self._with_default_web_auth(payload))

    def update(self, item_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self.repository.get(self.table, item_id)
        return super().update(item_id, self._with_default_web_auth(payload, existing))

    def list_options(self, project_id: int | None = None) -> list[dict[str, Any]]:
        rows, _ = self.repository.list(self.table, project_id=project_id, page=1, page_size=5000)
        result = []
        for row in rows:
            data = self._record_data(row)
            result.append(
                {
                    "id": row["id"],
                    "name": row.get("name"),
                    "route": data.get("route"),
                    "url": data.get("url"),
                    "feature_type": data.get("feature_type"),
                    "project_id": row.get("project_id"),
                }
            )
        return result

    def _with_default_web_auth(
        self,
        payload: dict[str, Any],
        existing: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = dict(payload)
        has_data_payload = "data" in result
        incoming_data = result.get("data")
        incoming_data = dict(incoming_data) if isinstance(incoming_data, dict) else {}

        existing_data = existing.get("data") if isinstance(existing, dict) else {}
        existing_data = existing_data if isinstance(existing_data, dict) else {}

        if existing is not None and not has_data_payload:
            if self._is_login_page(existing_data):
                return result
            if self._has_auth_id(existing_data):
                return result
            default_auth_id = self._default_web_auth_id(self._project_id(result, existing))
            if default_auth_id is None:
                return result
            data = dict(existing_data)
            data["auth_id"] = default_auth_id
            result["data"] = data
            return result

        data = {**existing_data, **incoming_data} if existing is not None else incoming_data
        if self._is_login_page(data):
            data.pop("auth_id", None)
            result["data"] = data
            return result

        if self._has_auth_id(data):
            result["data"] = data
            return result

        if self._has_auth_id(existing_data):
            data["auth_id"] = existing_data["auth_id"]
            result["data"] = data
            return result

        default_auth_id = self._default_web_auth_id(self._project_id(result, existing))
        if default_auth_id is not None:
            data["auth_id"] = default_auth_id
        result["data"] = data
        return result

    def _project_id(self, payload: dict[str, Any], existing: dict[str, Any] | None) -> int | None:
        value = payload.get("project_id")
        if value in (None, "") and isinstance(existing, dict):
            value = existing.get("project_id")
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _default_web_auth_id(self, project_id: int | None) -> int | None:
        if project_id is None:
            return None
        rows, _ = self.repository.list("project_auth", project_id=project_id, page=1, page_size=500)
        web_rows = [
            row
            for row in rows
            if str(self._record_data(row).get("login_case_type") or "").upper() == "WEB"
        ]
        if not web_rows:
            return None
        chosen = next((row for row in web_rows if str(row.get("status") or "") == "active"), web_rows[0])
        try:
            return int(chosen["id"])
        except (KeyError, TypeError, ValueError):
            return None

    def _has_auth_id(self, data: dict[str, Any]) -> bool:
        return data.get("auth_id") not in (None, "")

    def _is_login_page(self, data: dict[str, Any]) -> bool:
        return str(data.get("feature_type") or "").strip().lower() == "login"

    def _record_data(self, row: dict[str, Any]) -> dict[str, Any]:
        data = row.get("data")
        return data if isinstance(data, dict) else {}
