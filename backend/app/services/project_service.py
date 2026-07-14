from __future__ import annotations

from typing import Any

from app.repositories.interfaces import ResourceRepository


class ProjectService:
    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def list_options(self) -> list[dict[str, Any]]:
        rows, _ = self.repository.list("projects", None, None, 1, 200)
        return [
            {
                "id": item["id"],
                "name": item["name"],
                "base_url": self._project_url(item),
            }
            for item in rows
        ]

    def _project_url(self, item: dict[str, Any]) -> str:
        data = item.get("data") or {}
        value = data.get("base_url") or data.get("project_url") or data.get("url") or ""
        return str(value)
