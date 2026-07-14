from __future__ import annotations

from typing import Any

from app.constants.ai_generation import WEB_PAGE_FEATURE_TYPES
from app.repositories.interfaces import ResourceRepository
from app.schemas.ai import WebAiGenerationRequest, WebPageAiGenerationRequest
from app.services.case_draft_service import CaseDraftService
from app.services.resource_service import ResourceService
from app.services.web_page_service import WebPageResourceService
from app.utils.ai_generation_utils import (
    int_or_default,
    is_login_page_identity,
    join_url,
    list_dicts,
    looks_like_api_path,
    normalize_feature_type,
    page_identity_key,
    route_from_url,
    strategy_ids,
)


class AiGenerationResultSaver:
    """Persists AI-generated Web pages, elements and case drafts."""

    def __init__(
        self,
        repository: ResourceRepository,
        page_service: WebPageResourceService,
        element_service: ResourceService,
        draft_service: CaseDraftService,
    ) -> None:
        self.repository = repository
        self.page_service = page_service
        self.element_service = element_service
        self.draft_service = draft_service

    def save_web_pages(
        self,
        payload: WebPageAiGenerationRequest,
        project: dict[str, Any],
        result: dict[str, Any],
        valid_capture_routes: set[str] | None = None,
    ) -> dict[str, Any]:
        existing_rows, _ = self.repository.list("web_pages", project_id=payload.project_id, page=1, page_size=5000)
        existing_by_key = self.page_key_map(existing_rows)
        saved: list[dict[str, Any]] = []
        warnings: list[str] = []
        saved_pages = 0
        updated_pages = 0
        skipped_pages = 0

        result_pages = [page for page in result.get("pages", []) if isinstance(page, dict)]
        recognized_capture_keys = self.recognized_capture_keys(result_pages, valid_capture_routes)

        for page in result_pages:
            if valid_capture_routes is not None and not self.page_matches_capture(page, valid_capture_routes):
                skipped_pages += 1
                warnings.append(f"跳过页面: {page.get('name') or page.get('route') or '未命名'}，未采集到有效截图")
                continue
            normalized = self.normalize_page_payload(project, payload.project_id, page)
            if not normalized:
                skipped_pages += 1
                warnings.append(f"跳过页面: {page.get('name') or page.get('route') or '未命名'}")
                continue

            keys = self.page_keys(normalized)
            existing = next((existing_by_key[key] for key in keys if key in existing_by_key), None)
            if existing and payload.overwrite_existing:
                updated = self.page_service.update(existing["id"], normalized)
                saved.append(updated)
                updated_pages += 1
                for key in self.page_keys(updated):
                    existing_by_key[key] = updated
            elif existing:
                skipped_pages += 1
                saved.append(existing)
            else:
                created = self.page_service.create(normalized)
                saved.append(created)
                saved_pages += 1
                for key in self.page_keys(created):
                    existing_by_key[key] = created

        if valid_capture_routes is not None:
            missing_function_routes = sorted(valid_capture_routes - recognized_capture_keys)
            skipped_pages += len(missing_function_routes)
            for route in missing_function_routes[:50]:
                warnings.append(f"跳过页面: {route}，未识别到可保存功能")

        return {
            "saved_pages": saved_pages,
            "updated_pages": updated_pages,
            "skipped_pages": skipped_pages,
            "pages": saved,
            "warnings": warnings,
        }

    def save_web_generation_result(
        self,
        payload: WebAiGenerationRequest,
        page: dict[str, Any],
        task_id: int,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        warnings: list[str] = []
        saved_elements = 0
        if payload.save_elements:
            for element in result.get("elements", []):
                if self.save_element(payload, page, element):
                    saved_elements += 1
                else:
                    warnings.append(f"跳过元素: {element.get('name') or element.get('locator') or '未命名'}")

        saved_drafts = 0
        if payload.save_case_drafts:
            for case in result.get("cases", []):
                if self.save_case_draft(payload, page, task_id, case):
                    saved_drafts += 1
                else:
                    warnings.append(f"跳过用例: {case.get('name') or '未命名'}")
        return {"saved_elements": saved_elements, "saved_drafts": saved_drafts, "warnings": warnings}

    def valid_capture_route_keys(self, discovery: dict[str, Any]) -> set[str] | None:
        if not discovery or not discovery.get("enabled"):
            return None
        pages = discovery.get("captured_pages") if isinstance(discovery.get("captured_pages"), list) else []
        keys: set[str] = set()
        for page in pages:
            if not isinstance(page, dict):
                continue
            if not page.get("screenshot_url") and not page.get("screenshot_file"):
                continue
            for value in (page.get("route"), page.get("url")):
                key = self.normalize_capture_key(value)
                if key:
                    keys.add(key)
        return keys

    def page_matches_capture(self, page: dict[str, Any], valid_capture_routes: set[str]) -> bool:
        for value in (
            page.get("source_page_route"),
            page.get("source_page_url"),
            page.get("route"),
            page.get("url"),
        ):
            key = self.normalize_capture_key(value)
            if key and key in valid_capture_routes:
                return True
        return False

    def recognized_capture_keys(
        self,
        pages: list[dict[str, Any]],
        valid_capture_routes: set[str] | None,
    ) -> set[str]:
        if valid_capture_routes is None:
            return set()
        keys: set[str] = set()
        for page in pages:
            for value in (
                page.get("source_page_route"),
                page.get("source_page_url"),
                page.get("route"),
                page.get("url"),
            ):
                key = self.normalize_capture_key(value)
                if key and key in valid_capture_routes:
                    keys.add(key)
        return keys

    def normalize_capture_key(self, value: Any) -> str:
        text = str(value or "").strip()
        if not text or text.lower() == "none":
            return ""
        if text.startswith("http://") or text.startswith("https://"):
            text = route_from_url(text)
        text = text.split("#", 1)[0]
        if len(text) > 1:
            text = text.rstrip("/")
        return text.lower()

    def normalize_page_payload(
        self,
        project: dict[str, Any],
        project_id: int,
        page: dict[str, Any],
    ) -> dict[str, Any] | None:
        name = str(page.get("name") or "").strip()
        route = str(page.get("route") or "").strip()
        url = str(page.get("url") or "").strip()
        if not name:
            name = route or url
        if not name:
            return None
        source_route = str(page.get("source_page_route") or "").strip()
        source_url = str(page.get("source_page_url") or "").strip()
        if source_route and looks_like_api_path(route):
            page["ai_suggested_route"] = route
            route = source_route
        if source_url and looks_like_api_path(url):
            page["ai_suggested_url"] = url
            url = source_url
        if not route and url:
            route = route_from_url(url)
        if not url and route:
            base_url = str((project.get("data") or {}).get("base_url") or "").strip()
            url = join_url(base_url, route)
        if source_route and looks_like_api_path(route):
            route = source_route
        if source_url and looks_like_api_path(url):
            url = source_url
        feature_type = normalize_feature_type(page.get("feature_type"))
        if feature_type not in WEB_PAGE_FEATURE_TYPES:
            feature_type = "page"
        if is_login_page_identity(route, url, feature_type):
            return None
        return {
            "name": name[:128],
            "project_id": project_id,
            "description": page.get("description") or "AI生成的页面功能建议",
            "status": "active",
            "data": {
                "route": route,
                "url": url,
                "feature_type": feature_type,
                "module": page.get("module"),
                "priority": page.get("priority") or "P2",
                "source": "ai_generation",
                "ai_suggested_route": page.get("ai_suggested_route"),
                "ai_suggested_url": page.get("ai_suggested_url"),
            },
        }

    def page_key_map(self, pages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for page in pages:
            for key in self.page_keys(page):
                result[key] = page
        return result

    def page_keys(self, page: dict[str, Any]) -> list[str]:
        data = page.get("data") if isinstance(page.get("data"), dict) else {}
        project_id = page.get("project_id")
        route = data.get("route")
        url = data.get("url")
        feature_type = normalize_feature_type(data.get("feature_type"))
        key = page_identity_key(project_id, route, url, feature_type)
        return [key] if key else []

    def save_element(self, payload: WebAiGenerationRequest, page: dict[str, Any], element: dict[str, Any]) -> bool:
        name = str(element.get("name") or "").strip()
        locator = str(element.get("locator") or "").strip()
        if not name or not locator:
            return False
        data = {
            "page_id": payload.page_id,
            "route": page.get("data", {}).get("route") if isinstance(page.get("data"), dict) else "",
            "element_type": str(element.get("element_type") or element.get("type") or "button"),
            "type": str(element.get("element_type") or element.get("type") or "button"),
            "action": str(element.get("action") or "click"),
            "locator_type": str(element.get("locator_type") or "css"),
            "locator": locator,
            "default_value": element.get("default_value"),
            "example": element.get("example"),
            "required": bool(element.get("required")),
            "source": "ai_generation",
        }
        existing = self.find_existing_element(payload.project_id, payload.page_id, name)
        if existing:
            self.element_service.update(existing["id"], {"data": data, "description": element.get("description")})
        else:
            self.element_service.create(
                {
                    "name": name,
                    "project_id": payload.project_id,
                    "status": "active",
                    "description": element.get("description"),
                    "data": data,
                }
            )
        return True

    def save_case_draft(
        self,
        payload: WebAiGenerationRequest,
        page: dict[str, Any],
        task_id: int,
        case: dict[str, Any],
    ) -> bool:
        name = str(case.get("name") or "").strip()
        steps = self.normalize_steps(case.get("steps"))
        if not name or not steps:
            return False
        page_data = page.get("data") if isinstance(page.get("data"), dict) else {}
        case_json = {
            "name": name,
            "case_type": "WEB",
            "category": case.get("category") or "normal",
            "priority": case.get("priority") or "P2",
            "url": page_data.get("url") or "",
            "route": page_data.get("route") or "",
            "feature_type": page_data.get("feature_type") or "page",
            "source": "ai_generation",
            "ai_task_id": task_id,
            "steps": steps,
        }
        self.draft_service.create(
            {
                "name": name,
                "project_id": payload.project_id,
                "source_id": payload.page_id,
                "status": "draft",
                "description": case.get("description") or "AI生成，待人工审核",
                "case_json": case_json,
                "data": case_json,
                "assertions": list_dicts(case.get("assertions")),
                "strategy_ids": strategy_ids(case.get("strategy_ids")) or payload.strategy_ids,
            }
        )
        return True

    def normalize_steps(self, value: Any) -> list[dict[str, Any]]:
        steps = list_dicts(value)
        normalized: list[dict[str, Any]] = []
        for index, step in enumerate(steps):
            action = str(step.get("action") or step.get("交互类型") or "click")
            name = str(step.get("element_name") or step.get("name") or step.get("元素名称") or "").strip()
            if not name:
                continue
            normalized.append(
                {
                    "step_id": int_or_default(step.get("step_id") or step.get("步骤标识"), index + 1),
                    "element_name": name,
                    "value": step.get("value", step.get("元素值")),
                    "action": action,
                    "take_screenshot": bool(step.get("take_screenshot", step.get("是否截图", False))),
                    "skip": bool(step.get("skip", step.get("是否跳过", False))),
                }
            )
        normalized.sort(key=lambda item: int(item["step_id"]))
        if normalized and not any(item.get("take_screenshot") for item in normalized):
            normalized[-1]["take_screenshot"] = True
        return normalized

    def find_existing_element(self, project_id: int, page_id: int, name: str) -> dict[str, Any] | None:
        rows, _ = self.repository.list(
            "web_elements",
            keyword=name,
            project_id=project_id,
            page=1,
            page_size=100,
            data_filters={"page_id": page_id},
        )
        for row in rows:
            if row.get("name") == name:
                return row
        return None
