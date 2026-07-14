from __future__ import annotations

import time
from typing import Any

from app.repositories.interfaces import ResourceRepository
from app.services.auth_file_service import AuthFileService
from app.services.resource_service import ResourceService


TOKEN_KEYS = ("token", "access_token", "accessToken", "value")


class ProjectAuthResourceService(ResourceService):
    def __init__(self, repository: ResourceRepository) -> None:
        super().__init__("project_auth", repository)

    def list(
        self,
        keyword: str | None,
        project_id: int | None,
        page: int,
        page_size: int,
        data_filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        items, total = super().list(keyword, project_id, page, page_size, data_filters)
        return [self._hide_secret(item) for item in items], total

    def get(self, item_id: int) -> dict[str, Any]:
        return self._hide_secret(super().get(item_id))

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._hide_secret(super().create(self._prepare_payload(payload)))

    def update(self, item_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return self._hide_secret(super().update(item_id, self._prepare_payload(payload, item_id)))

    def _prepare_payload(self, payload: dict[str, Any], item_id: int | None = None) -> dict[str, Any]:
        data = payload.get("data")
        if not isinstance(data, dict):
            return payload

        next_data = dict(data)
        token = self._extract_token(next_data)
        if token:
            existing = self.repository.get("project_auth", item_id) if item_id else None
            existing_data = existing.get("data") if isinstance(existing, dict) and isinstance(existing.get("data"), dict) else {}
            filename = str(next_data.get("token_file") or existing_data.get("token_file") or "")
            if not filename:
                filename = self._token_filename(str(payload.get("name") or "auth-token"), item_id)
            next_data["token_file"] = AuthFileService().save_json(
                filename,
                {
                    "type": next_data.get("auth_type") or "bearer",
                    "token": str(token),
                    "project_id": payload.get("project_id"),
                    "auth_name": payload.get("name"),
                    "header_name": next_data.get("header_name") or "Authorization",
                    "saved_at": int(time.time()),
                },
            )

        for key in TOKEN_KEYS:
            next_data.pop(key, None)
        payload = dict(payload)
        payload["data"] = next_data
        return payload

    def _extract_token(self, data: dict[str, Any]) -> str:
        for key in TOKEN_KEYS:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _hide_secret(self, item: dict[str, Any]) -> dict[str, Any]:
        result = dict(item)
        data = result.get("data")
        if not isinstance(data, dict):
            return result
        masked_data = dict(data)
        for key in TOKEN_KEYS:
            masked_data.pop(key, None)
        result["data"] = masked_data
        return result

    def _token_filename(self, name: str, item_id: int | None) -> str:
        stem = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in name.strip())
        stem = stem.strip("._") or "auth-token"
        suffix = item_id or int(time.time())
        return f"{stem}-{suffix}.json"
