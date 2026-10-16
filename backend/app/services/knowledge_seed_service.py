"""Provision the system-managed test principles used by plan generation."""

from __future__ import annotations

from copy import deepcopy

from app.constants.knowledge_principles import (
    DEFAULT_KNOWLEDGE_ITEMS,
    LEGACY_DEFAULT_KEYS,
)
from app.repositories.interfaces import ResourceRepository


class KnowledgeSeedService:
    """Synchronize built-in principles without changing user-created knowledge."""

    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def seed_defaults(
        self,
        project_id: int,
        overwrite: bool = False,
    ) -> dict[str, int]:
        """Insert or update current principles and retire known legacy defaults."""

        rows, _ = self.repository.list(
            "project_knowledge",
            project_id=project_id,
            page=1,
            page_size=10000,
        )
        existing = {
            key: item
            for item in rows
            if (key := self._knowledge_key(item))
        }
        result = self._sync_current_items(existing, project_id, overwrite)
        result["deleted_count"] = self._delete_legacy_items(existing)
        result["total_count"] = len(DEFAULT_KNOWLEDGE_ITEMS)
        return result

    def _sync_current_items(
        self,
        existing: dict[str, dict[str, object]],
        project_id: int,
        overwrite: bool,
    ) -> dict[str, int]:
        inserted = 0
        updated = 0
        skipped = 0
        for default_item in DEFAULT_KNOWLEDGE_ITEMS:
            payload = deepcopy(default_item)
            payload["project_id"] = project_id
            payload["status"] = "active"
            knowledge_key = self._knowledge_key(payload)
            current = existing.get(knowledge_key)
            if current is None:
                self.repository.create("project_knowledge", payload)
                inserted += 1
            elif overwrite or (
                self._is_system_managed(current)
                and any(current.get(key) != value for key, value in payload.items())
            ):
                self.repository.update(
                    "project_knowledge",
                    int(current["id"]),
                    payload,
                )
                updated += 1
            else:
                skipped += 1
        return {
            "inserted_count": inserted,
            "updated_count": updated,
            "skipped_count": skipped,
        }

    def _delete_legacy_items(
        self,
        existing: dict[str, dict[str, object]],
    ) -> int:
        deleted_count = 0
        for knowledge_key in LEGACY_DEFAULT_KEYS:
            current = existing.get(knowledge_key)
            if current and self.repository.delete(
                "project_knowledge",
                int(current["id"]),
            ):
                deleted_count += 1
        return deleted_count

    def _knowledge_key(self, item: dict[str, object]) -> str:
        data = item.get("data")
        if not isinstance(data, dict):
            return ""
        value = data.get("knowledge_key")
        return str(value).strip() if value is not None else ""

    def _is_system_managed(self, item: dict[str, object]) -> bool:
        data = item.get("data")
        return isinstance(data, dict) and data.get("managed_by") == "system"
