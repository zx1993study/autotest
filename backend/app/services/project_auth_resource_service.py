from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from app.repositories.interfaces import ResourceRepository
from app.services.auth_file_service import AuthFileService
from app.services.resource_service import ResourceService
from app.utils.auth_token import normalize_auth_token

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
        return self._save(payload)

    def update(self, item_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return self._save(payload, item_id)

    def _save(self, payload: dict[str, Any], item_id: int | None = None) -> dict[str, Any]:
        existing = super().get(item_id) if item_id else {}
        data = {**(existing.get("data") or {}), **(payload.get("data") or {})}
        token = normalize_auth_token(self._extract_token(data), str(data.get("auth_type") or "bearer"))
        for key in TOKEN_KEYS:
            data.pop(key, None)
        prepared = {**payload, "data": data}
        def operation():
            service = super(ProjectAuthResourceService, self)
            return service.update(item_id, prepared) if item_id else service.create(prepared)
        if not token:
            return self._hide_secret(operation())
        files = AuthFileService()
        filename = files.safe_filename(str(data.get("token_file") or (existing.get("data") or {}).get("token_file") or self._token_filename(str(payload.get("name") or "auth-token"), item_id)))
        self._check_file_owner(filename, item_id)
        now = int(time.time())
        content = {
            **files.load_json(filename),
            "type": data.get("auth_type") or "bearer",
            "token": token,
            "project_id": payload.get("project_id", existing.get("project_id")),
            "auth_name": payload.get("name", existing.get("name")),
            "header_name": data.get("header_name") or "Authorization",
            "updated_at": now,
            "saved_at": now,
        }
        for key in TOKEN_KEYS[1:]:
            content.pop(key, None)
        data.update(token_file=filename, token_source="manual", token_updated_at=now)
        with files.replace_json(filename, content):
            return self._hide_secret(operation())

    def _check_file_owner(self, filename: str, item_id: int | None) -> None:
        from app.core.exceptions import BusinessRuleError

        files = AuthFileService()
        page = 1
        while True:
            rows, total = self.repository.list("project_auth", page=page, page_size=200)
            for row in rows:
                name = (row.get("data") or {}).get("token_file")
                if row["id"] != item_id and name and files.safe_filename(str(name)) == filename:
                    raise BusinessRuleError("该鉴权文件已被其他配置使用，请填写独立文件名")
            if page * 200 >= total:
                break
            page += 1

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
        suffix = item_id or uuid4().hex
        return f"{stem}-{suffix}.json"
