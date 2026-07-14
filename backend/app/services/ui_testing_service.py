from typing import Any

from app.repositories.interfaces import ResourceRepository
from app.services.resource_service import ResourceService
from app.utils.playwright_script_parser import PlaywrightCodegenParser


EXISTING_ELEMENT_UPDATE = "update"
EXISTING_ELEMENT_SKIP = "skip"
EXISTING_ELEMENT_STRATEGIES = {EXISTING_ELEMENT_UPDATE, EXISTING_ELEMENT_SKIP}


class UiTestingService:
    def __init__(self, page_table: str, element_table: str, repository: ResourceRepository) -> None:
        self.page_table = page_table
        self.element_table = element_table
        self.pages = ResourceService(page_table, repository)
        self.elements = ResourceService(element_table, repository)

    def scan_elements(
        self,
        project_id: int,
        page_id: int | None,
        target_url: str | None,
        feature: str | None,
        source: dict[str, Any],
        existing_strategy: str = EXISTING_ELEMENT_UPDATE,
    ) -> dict[str, int]:
        target_page_id = page_id
        if target_page_id is None:
            page = self.pages.create(
                {
                    "name": feature or source.get("title") or "scan page",
                    "project_id": project_id,
                    "description": target_url,
                    "data": {"url": target_url, "feature": feature},
                }
            )
            target_page_id = page["id"]

        elements = source.get("elements") or self._default_elements(feature)
        stats = self._empty_save_stats()
        existing_rows = self._existing_elements(project_id, target_page_id)
        for index, element in enumerate(elements, start=1):
            name = str(element.get("name") or element.get("text") or f"element {index}")
            saved = self._save_element(
                project_id,
                target_page_id,
                name,
                element.get("description"),
                self._element_data(target_page_id, feature, element),
                existing_strategy,
                existing_rows,
            )
            self._merge_save_stats(stats, saved)
        return {"element_count": stats["saved_count"], "page_id": target_page_id, **stats}

    def parse_playwright_script(
        self,
        project_id: int,
        page_id: int,
        script: str,
        source_type: str = "codegen",
        existing_strategy: str = EXISTING_ELEMENT_UPDATE,
    ) -> dict[str, Any]:
        page = self.pages.get(page_id)
        parser = PlaywrightCodegenParser()
        parsed_elements = parser.parse(script)
        saved_elements: list[dict[str, Any]] = []
        skipped_elements: list[dict[str, Any]] = []
        stats = self._empty_save_stats()
        existing_rows = self._existing_elements(project_id, page_id)

        for index, element in enumerate(parsed_elements, start=1):
            data = {
                "page_id": page_id,
                "feature": page.get("name"),
                "element_type": element.get("element_type"),
                "type": element.get("element_type"),
                "action": element.get("action"),
                "locator_type": element.get("locator_type"),
                "locator": element.get("locator"),
                "default_value": element.get("default_value"),
                "example": element.get("example"),
                "playwright_locator": element.get("playwright_locator"),
                "locator_method": element.get("locator_method"),
                "locator_args": element.get("locator_args"),
                "role": element.get("role"),
                "role_name": element.get("role_name"),
                "source": f"playwright_{source_type}",
            }
            name = str(element.get("name") or f"element {index}")
            saved = self._save_element(
                project_id,
                page_id,
                name,
                "parsed from Playwright codegen script",
                data,
                existing_strategy,
                existing_rows,
            )
            self._merge_save_stats(stats, saved)
            if saved:
                saved_elements.append(saved)
            else:
                skipped_elements.append({"name": name, "data": data})

        stats["deleted_stale_count"] = self._delete_stale_generated_elements(
            source_type,
            saved_elements,
            existing_rows,
            existing_strategy,
        )

        return {
            "page_id": page_id,
            "element_count": stats["saved_count"],
            "created_count": stats["created_count"],
            "updated_count": stats["updated_count"],
            "skipped_count": stats["skipped_count"],
            "deduplicated_count": stats["deduplicated_count"],
            "deleted_stale_count": stats["deleted_stale_count"],
            "existing_strategy": self._normalize_existing_strategy(existing_strategy),
            "elements": saved_elements,
            "skipped_elements": skipped_elements,
        }

    def _save_element(
        self,
        project_id: int,
        page_id: int,
        name: str,
        description: str | None,
        data: dict[str, Any],
        existing_strategy: str,
        existing_rows: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        normalized_strategy = self._normalize_existing_strategy(existing_strategy)
        existing = self._find_existing_element(project_id, page_id, name, data, existing_rows)
        if existing and normalized_strategy == EXISTING_ELEMENT_SKIP:
            return None
        if existing:
            merged_data = dict(existing.get("data") or {})
            merged_data.update(data)
            updated = self.elements.update(
                existing["id"],
                {
                    "name": name,
                    "project_id": project_id,
                    "description": description,
                    "data": merged_data,
                },
            )
            updated["_save_action"] = "updated"
            if existing_rows is not None:
                self._replace_existing_element(existing_rows, updated)
            updated["_deduplicated_count"] = self._delete_duplicate_existing_elements(
                project_id,
                page_id,
                updated,
                data,
                existing_rows,
            )
            return updated

        created = self.elements.create(
            {
                "name": name,
                "project_id": project_id,
                "description": description,
                "data": data,
            }
        )
        created["_save_action"] = "created"
        if existing_rows is not None:
            existing_rows.append(created)
        created["_deduplicated_count"] = self._delete_duplicate_existing_elements(
            project_id,
            page_id,
            created,
            data,
            existing_rows,
        )
        return created

    def _find_existing_element(
        self,
        project_id: int,
        page_id: int,
        name: str,
        data: dict[str, Any],
        existing_rows: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        rows = existing_rows if existing_rows is not None else self._existing_elements(project_id, page_id)
        locator = str(data.get("locator") or "").strip()
        locator_type = str(data.get("locator_type") or "").strip()
        normalized_name = str(name or "").strip()
        for row in rows:
            row_data = row.get("data") if isinstance(row.get("data"), dict) else {}
            if normalized_name and str(row.get("name") or "").strip() == normalized_name:
                return row
            if (
                locator
                and locator == str(row_data.get("locator") or "").strip()
                and locator_type == str(row_data.get("locator_type") or "").strip()
            ):
                return row
        return None

    def _existing_elements(self, project_id: int, page_id: int) -> list[dict[str, Any]]:
        rows, _ = self.elements.list(None, project_id, 1, 10000, {"page_id": page_id})
        return rows

    def _replace_existing_element(self, rows: list[dict[str, Any]], item: dict[str, Any]) -> None:
        for index, row in enumerate(rows):
            if row.get("id") == item.get("id"):
                rows[index] = item
                return
        rows.append(item)

    def _delete_duplicate_existing_elements(
        self,
        project_id: int,
        page_id: int,
        saved: dict[str, Any],
        data: dict[str, Any],
        existing_rows: list[dict[str, Any]] | None,
    ) -> int:
        rows = existing_rows if existing_rows is not None else self._existing_elements(project_id, page_id)
        saved_id = saved.get("id")
        name = str(saved.get("name") or "").strip()
        locator = str(data.get("locator") or "").strip()
        locator_type = str(data.get("locator_type") or "").strip()
        deleted_ids: set[int] = set()
        for row in list(rows):
            row_id = row.get("id")
            if row_id == saved_id:
                continue
            row_data = row.get("data") if isinstance(row.get("data"), dict) else {}
            same_name = name and str(row.get("name") or "").strip() == name
            same_locator = (
                locator
                and locator == str(row_data.get("locator") or "").strip()
                and locator_type == str(row_data.get("locator_type") or "").strip()
            )
            if not same_name and not same_locator:
                continue
            if self.elements.delete(int(row_id)):
                deleted_ids.add(int(row_id))
        if deleted_ids and existing_rows is not None:
            existing_rows[:] = [row for row in existing_rows if int(row.get("id") or 0) not in deleted_ids]
        return len(deleted_ids)

    def _delete_stale_generated_elements(
        self,
        source_type: str,
        saved_elements: list[dict[str, Any]],
        existing_rows: list[dict[str, Any]],
        existing_strategy: str,
    ) -> int:
        if source_type != "ai_auto" or self._normalize_existing_strategy(existing_strategy) != EXISTING_ELEMENT_UPDATE:
            return 0
        saved_ids = {int(item["id"]) for item in saved_elements if item.get("id")}
        deleted_ids: set[int] = set()
        for row in list(existing_rows):
            row_id = int(row.get("id") or 0)
            if not row_id or row_id in saved_ids:
                continue
            row_data = row.get("data") if isinstance(row.get("data"), dict) else {}
            if row_data.get("source") != "playwright_ai_auto":
                continue
            if self.elements.delete(row_id):
                deleted_ids.add(row_id)
        if deleted_ids:
            existing_rows[:] = [row for row in existing_rows if int(row.get("id") or 0) not in deleted_ids]
        return len(deleted_ids)

    def _normalize_existing_strategy(self, value: str | None) -> str:
        strategy = str(value or EXISTING_ELEMENT_UPDATE).strip().lower()
        return strategy if strategy in EXISTING_ELEMENT_STRATEGIES else EXISTING_ELEMENT_UPDATE

    def _empty_save_stats(self) -> dict[str, int]:
        return {
            "saved_count": 0,
            "created_count": 0,
            "updated_count": 0,
            "skipped_count": 0,
            "deduplicated_count": 0,
            "deleted_stale_count": 0,
        }

    def _merge_save_stats(self, stats: dict[str, int], saved: dict[str, Any] | None) -> None:
        if not saved:
            stats["skipped_count"] += 1
            return
        stats["saved_count"] += 1
        if saved.get("_save_action") == "updated":
            stats["updated_count"] += 1
        else:
            stats["created_count"] += 1
        stats["deduplicated_count"] += int(saved.get("_deduplicated_count") or 0)

    def _element_data(self, page_id: int, feature: str | None, element: dict[str, Any]) -> dict[str, Any]:
        data = {
            "page_id": page_id,
            "feature": feature,
            "type": element.get("type", "button"),
            "element_type": element.get("element_type") or element.get("type", "button"),
            "action": element.get("action"),
            "required": bool(element.get("required")),
            "example": element.get("example"),
            "default_value": element.get("default_value"),
        }
        if self.element_table in {"app_elements", "miniapp_elements"}:
            data.update(
                {
                    "platform": element.get("platform") or "Android",
                    "locator_type": element.get("locator_type") or self._default_locator_type(element),
                    "locator": element.get("locator")
                    or element.get("resource_id")
                    or element.get("css")
                    or element.get("text")
                    or element.get("content_desc"),
                    "resource_id": element.get("resource_id"),
                    "css": element.get("css"),
                    "text": element.get("text"),
                    "content_desc": element.get("content_desc"),
                    "xpath": element.get("xpath"),
                    "take_screenshot": bool(element.get("take_screenshot")),
                }
            )
        else:
            data.update(
                {
                    "locator": element.get("locator") or element.get("resource_id") or element.get("css") or element.get("text"),
                    "locator_type": element.get("locator_type") or self._default_web_locator_type(element),
                    "playwright_locator": element.get("playwright_locator"),
                    "locator_method": element.get("locator_method"),
                    "locator_args": element.get("locator_args"),
                    "role": element.get("role"),
                    "role_name": element.get("role_name"),
                    "source": element.get("source"),
                    "take_screenshot": bool(element.get("take_screenshot")),
                    "container": element.get("container"),
                }
            )
        return data

    def _default_elements(self, feature: str | None) -> list[dict[str, Any]]:
        feature_text = str(feature or "")
        if self.element_table == "app_elements":
            return self._default_app_elements(feature_text)
        if self.element_table == "miniapp_elements":
            return self._default_miniapp_elements(feature_text)
        return self._default_web_elements(feature_text)

    def _default_locator_type(self, element: dict[str, Any]) -> str:
        if element.get("resource_id"):
            return "resource_id"
        if element.get("css"):
            return "css"
        if element.get("xpath"):
            return "xpath"
        return "text"

    def _default_web_locator_type(self, element: dict[str, Any]) -> str:
        if element.get("playwright_locator"):
            return "playwright"
        if element.get("locator"):
            return str(element.get("locator_type") or "css")
        if element.get("css"):
            return "css"
        if element.get("xpath"):
            return "xpath"
        if element.get("placeholder"):
            return "placeholder"
        if element.get("text"):
            return "text"
        return "css"

    def _default_app_elements(self, feature: str) -> list[dict[str, Any]]:
        if "login" in feature.lower() or "登录" in feature:
            return [
                {"name": "username", "type": "input", "action": "input", "required": True, "locator_type": "text", "text": "用户名"},
                {"name": "password", "type": "input", "action": "input", "required": True, "locator_type": "text", "text": "密码"},
                {"name": "login_button", "type": "button", "action": "tap", "locator_type": "text", "text": "登录", "take_screenshot": True},
            ]
        if "add" in feature.lower() or "新增" in feature:
            return [
                {"name": "add_button", "type": "button", "action": "tap", "locator_type": "text", "text": "新增"},
                {"name": "name", "type": "input", "action": "input", "required": True, "locator_type": "text", "text": "名称"},
                {"name": "confirm_button", "type": "button", "action": "tap", "locator_type": "text", "text": "确定", "take_screenshot": True},
            ]
        return [
            {"name": "search_input", "type": "input", "action": "input", "locator_type": "text", "text": "搜索"},
            {"name": "query_button", "type": "button", "action": "tap", "locator_type": "text", "text": "查询", "take_screenshot": True},
        ]

    def _default_web_elements(self, feature: str) -> list[dict[str, Any]]:
        if "login" in feature.lower() or "登录" in feature:
            return [
                {"name": "username", "type": "input", "action": "fill", "required": True},
                {"name": "password", "type": "input", "action": "fill", "required": True},
                {"name": "login_button", "type": "button", "action": "click"},
            ]
        if "add" in feature.lower() or "新增" in feature:
            return [
                {"name": "add_button", "type": "button", "action": "click"},
                {"name": "name", "type": "input", "action": "fill", "required": True},
                {"name": "confirm_button", "type": "button", "action": "click"},
            ]
        return [
            {"name": "search_input", "type": "input", "action": "fill"},
            {"name": "query_button", "type": "button", "action": "click"},
        ]

    def _default_miniapp_elements(self, feature: str) -> list[dict[str, Any]]:
        if "login" in feature.lower() or "鐧诲綍" in feature:
            return [
                {"name": "username", "type": "input", "action": "input", "required": True, "locator_type": "css", "css": "input[name='username']"},
                {"name": "password", "type": "input", "action": "input", "required": True, "locator_type": "css", "css": "input[type='password']"},
                {"name": "login_button", "type": "button", "action": "tap", "locator_type": "text", "text": "鐧诲綍", "take_screenshot": True},
            ]
        if "add" in feature.lower() or "鏂板" in feature:
            return [
                {"name": "add_button", "type": "button", "action": "tap", "locator_type": "text", "text": "鏂板"},
                {"name": "name", "type": "input", "action": "input", "required": True, "locator_type": "css", "css": "input[name='name']"},
                {"name": "confirm_button", "type": "button", "action": "tap", "locator_type": "text", "text": "纭畾", "take_screenshot": True},
            ]
        return [
            {"name": "search_input", "type": "input", "action": "input", "locator_type": "css", "css": "input[type='search']"},
            {"name": "query_button", "type": "button", "action": "tap", "locator_type": "text", "text": "鏌ヨ", "take_screenshot": True},
        ]
