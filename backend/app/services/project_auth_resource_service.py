from __future__ import annotations

import time
from typing import Any

from app.repositories.interfaces import ResourceRepository
from app.services.project_auth_token_service import TOKEN_KEYS, ProjectAuthTokenService
from app.services.resource_service import ResourceService
from app.utils.auth_token import normalize_auth_token


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

    def delete(self, item_id: int) -> bool:
        existing = super().get(item_id)
        result = super().delete(item_id)
        ProjectAuthTokenService.remove_unused_file(self.repository, str((existing.get("data") or {}).get("token_file") or ""))
        return result

    def batch_delete(self, ids: list[int]) -> dict[str, int]:
        filenames = {
            str((item.get("data") or {}).get("token_file") or "")
            for item in self.repository.get_many(self.table, ids)
        }
        result = super().batch_delete(ids)
        ProjectAuthTokenService.remove_unused_files(self.repository, filenames)
        return result

    def _save(self, payload: dict[str, Any], item_id: int | None = None) -> dict[str, Any]:
        existing = super().get(item_id) if item_id else {}
        incoming = dict(payload.get("data") or {})
        # Ciphertext and storage flags are server-owned, never editable via generic CRUD.
        for key in ("token_encrypted", "token_saved", "token_storage", "token_storage_label"):
            incoming.pop(key, None)
        data = {**(existing.get("data") or {}), **incoming}
        token = normalize_auth_token(self._extract_token(data), str(data.get("auth_type") or "bearer"))
        for key in TOKEN_KEYS:
            data.pop(key, None)
        if data.get("token_encrypted"):
            data.pop("token_file", None)
        prepared = {**payload, "data": data}
        def operation():
            service = super(ProjectAuthResourceService, self)
            return service.update(item_id, prepared) if item_id else service.create(prepared)
        if not token:
            return self._hide_secret(operation())
        filename = str((existing.get("data") or {}).get("token_file") or "")
        data.pop("token_file", None)
        data.update(token_encrypted=ProjectAuthTokenService().encrypt(token), token_storage="database", token_source="manual", token_updated_at=int(time.time()))
        result = operation()
        # Commit the replacement before removing an obsolete legacy credential file.
        ProjectAuthTokenService.remove_unused_file(self.repository, filename)
        return self._hide_secret(result)

    def _extract_token(self, data: dict[str, Any]) -> str:
        for key in TOKEN_KEYS:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _hide_secret(self, item: dict[str, Any]) -> dict[str, Any]:
        return ProjectAuthTokenService.public_auth(item)
