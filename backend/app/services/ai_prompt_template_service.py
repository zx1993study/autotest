from __future__ import annotations

from typing import Any

from app.repositories.interfaces import ResourceRepository


class AiPromptTemplateService:
    """Query AI prompt templates for presentation-specific option lists.

    This service keeps template filtering out of the router while still using
    the repository abstraction shared by the rest of the application.
    """

    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def list_options(self, template_type: str | None = None) -> list[dict[str, Any]]:
        """Return active prompt templates suitable for select controls."""

        items, _ = self.repository.list("ai_prompt_templates", page=1, page_size=1000)
        result: list[dict[str, Any]] = []
        for item in items:
            data = item.get("data") if isinstance(item.get("data"), dict) else {}
            if item.get("status") != "active":
                continue
            if template_type and data.get("template_type") != template_type:
                continue
            result.append({"id": item["id"], "name": item["name"], "template_type": data.get("template_type")})
        return result
