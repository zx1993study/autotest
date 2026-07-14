from __future__ import annotations

from app.repositories.interfaces import ResourceRepository
from app.services.resource_service import ResourceService


class WebElementService(ResourceService):
    """Manage Web element listing rules that are specific to page assets.

    Generic resources are listed by latest updates first for most management pages.
    Web elements are consumed as executable steps, so their list contract is
    intentionally id-ascending and enriched with the owning page name to keep
    the element page and case-step dialog aligned.
    """

    def __init__(self, repository: ResourceRepository) -> None:
        super().__init__("web_elements", repository)

    def list(
        self,
        keyword: str | None,
        project_id: int | None,
        page: int,
        page_size: int,
        data_filters: dict[str, object] | None = None,
    ) -> tuple[list[dict[str, object]], int]:
        """Return Web elements by element id ascending with page names."""

        rows, total = self.repository.list(self.table, keyword, project_id, page, page_size, data_filters)
        page_names = self._page_names(rows)
        rows = [self._with_page_name(row, page_names) for row in rows]
        return rows, total

    def _page_names(self, rows: list[dict[str, object]]) -> dict[int, str]:
        page_ids = sorted({page_id for row in rows if (page_id := self._page_id(row)) is not None})
        page_names: dict[int, str] = {}
        for page_id in page_ids:
            page = self.repository.get("web_pages", page_id)
            if page:
                page_names[page_id] = str(page.get("name") or "")
        return page_names

    def _with_page_name(self, row: dict[str, object], page_names: dict[int, str]) -> dict[str, object]:
        item = dict(row)
        data = self._data(item)
        page_id = self._page_id(item)
        data["page_name"] = page_names.get(page_id or 0, "")
        item["data"] = data
        return item

    def _data(self, row: dict[str, object]) -> dict[str, object]:
        value = row.get("data")
        if not isinstance(value, dict):
            return {}
        return {str(key): item for key, item in value.items()}

    def _page_id(self, row: dict[str, object]) -> int | None:
        data = self._data(row)
        value = data.get("page_id")
        try:
            page_id = int(value) if value is not None else 0
        except (TypeError, ValueError):
            return None
        return page_id if page_id > 0 else None
