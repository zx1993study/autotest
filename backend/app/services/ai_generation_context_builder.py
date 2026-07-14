from __future__ import annotations

from typing import Any

from app.constants.ai_generation import (
    AI_WEB_PAGE_API_BATCH_SIZE,
    AI_WEB_PAGE_MAX_EXISTING_PAGES,
    AI_WEB_PAGE_MAX_KNOWLEDGE,
)
from app.repositories.interfaces import ResourceRepository
from app.schemas.ai import WebAiGenerationRequest, WebPageAiGenerationRequest
from app.utils.ai_generation_utils import (
    chunks,
    interface_context,
    interface_module_summary,
    is_strategy_for_web,
    knowledge_context,
    page_context,
    project_context,
    resource_context,
    sanitize_ai_value,
    short_text,
)


class AiGenerationContextBuilder:
    """Builds sanitized AI prompt context from project resources."""

    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def project_page_context(
        self,
        project: dict[str, Any],
        payload: WebPageAiGenerationRequest,
        discovery: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        contexts = self.project_page_contexts(project, payload, discovery)
        if contexts:
            return contexts[0]
        return self.project_page_context_from_parts(project, payload, [], [], [], discovery or {}, 1, 1)

    def project_page_contexts(
        self,
        project: dict[str, Any],
        payload: WebPageAiGenerationRequest,
        discovery: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        existing_pages, interfaces, knowledge = self._project_context_sources(payload)
        batches = chunks(interfaces, AI_WEB_PAGE_API_BATCH_SIZE) if interfaces else [[]]
        return [
            self.project_page_context_from_parts(
                project,
                payload,
                existing_pages,
                batch,
                knowledge,
                discovery or {},
                index,
                len(batches),
            )
            for index, batch in enumerate(batches, start=1)
        ]

    def project_page_analysis_contexts(
        self,
        project: dict[str, Any],
        payload: WebPageAiGenerationRequest,
        discovery: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        discovered_pages = self.discovered_pages(discovery or {})
        if not discovered_pages:
            return self.project_page_contexts(project, payload, discovery)

        existing_pages, interfaces, knowledge = self._project_context_sources(payload)
        total = len(discovered_pages)
        return [
            self.single_discovered_page_context(
                project=project,
                payload=payload,
                existing_pages=existing_pages,
                interfaces=interfaces,
                knowledge=knowledge,
                discovery=discovery or {},
                discovered_page=page,
                index=index,
                total=total,
            )
            for index, page in enumerate(discovered_pages, start=1)
        ]

    def single_discovered_page_context(
        self,
        project: dict[str, Any],
        payload: WebPageAiGenerationRequest,
        existing_pages: list[dict[str, Any]],
        interfaces: list[dict[str, Any]],
        knowledge: list[dict[str, Any]],
        discovery: dict[str, Any],
        discovered_page: dict[str, Any],
        index: int,
        total: int,
    ) -> dict[str, Any]:
        page_api_calls = discovered_page.get("api_calls") if isinstance(discovered_page.get("api_calls"), list) else []
        matched_interfaces = self.interfaces_for_page(interfaces, page_api_calls)
        context = {
            "project": project_context(project),
            "generation_batch": {
                "batch_index": index,
                "batch_count": total,
                "api_batch_size": 1,
                "instruction": "本次只分析 current_page，一次只发送一个页面对应的截图和 API 信息。不要生成其他页面功能。",
            },
            "discovery_instruction": (
                "current_page 来自 Playwright 登录后真实采集，包含当前页面截图地址、页面文字、按钮入口和当前页面触发的 API。"
                "请只根据当前页面拆分 page/query/add/edit/delete/detail/import/export 等功能。"
            ),
            "existing_pages": [page_context(item) for item in existing_pages],
            "current_page": self.discovered_page_context(discovered_page),
            "api_interfaces": [interface_context(item) for item in matched_interfaces],
            "api_module_summary": interface_module_summary(matched_interfaces),
            "discovered_web_pages": {
                "enabled": bool(discovery.get("enabled")),
                "base_url": discovery.get("base_url"),
                "start_url": discovery.get("start_url"),
                "auth_loaded": bool(discovery.get("auth_loaded")),
                "login_executed": bool(discovery.get("login_executed")),
                "current_page_index": index,
                "current_page_total": total,
            },
            "knowledge": [knowledge_context(item) for item in knowledge],
        }
        return sanitize_ai_value(context)

    def project_page_context_from_parts(
        self,
        project: dict[str, Any],
        payload: WebPageAiGenerationRequest,
        existing_pages: list[dict[str, Any]],
        interfaces: list[dict[str, Any]],
        knowledge: list[dict[str, Any]],
        discovery: dict[str, Any],
        batch_index: int,
        batch_count: int,
    ) -> dict[str, Any]:
        context = {
            "project": project_context(project),
            "generation_batch": {
                "batch_index": batch_index,
                "batch_count": batch_count,
                "api_batch_size": AI_WEB_PAGE_API_BATCH_SIZE,
                "instruction": "本批次只基于当前 api_interfaces、真实页面采集信息和知识库生成页面功能，最终由平台合并多批结果并去重保存。",
            },
            "discovery_instruction": (
                "discovered_web_pages 来自 Playwright 登录后真实采集：包含路由、截图地址、页面文字、按钮入口和页面 API 调用。"
                "请优先按该信息拆分查询、新增、编辑、删除、详情、导入、导出等页面功能。"
            ),
            "existing_pages": [page_context(item) for item in existing_pages],
            "api_interfaces": [interface_context(item) for item in interfaces],
            "api_module_summary": interface_module_summary(interfaces),
            "discovered_web_pages": self.discovery_context(discovery),
            "knowledge": [knowledge_context(item) for item in knowledge],
        }
        return sanitize_ai_value(context)

    def discovery_context(self, discovery: dict[str, Any]) -> dict[str, Any]:
        if not discovery:
            return {"enabled": False}
        pages = discovery.get("captured_pages") if isinstance(discovery.get("captured_pages"), list) else []
        routes = discovery.get("routes") if isinstance(discovery.get("routes"), list) else []
        return {
            "enabled": bool(discovery.get("enabled")),
            "base_url": discovery.get("base_url"),
            "start_url": discovery.get("start_url"),
            "auth_loaded": bool(discovery.get("auth_loaded")),
            "login_executed": bool(discovery.get("login_executed")),
            "login_failed": bool(discovery.get("login_failed")),
            "login_record_id": discovery.get("login_record_id"),
            "login_auth_id": discovery.get("login_auth_id"),
            "login_final_url": discovery.get("login_final_url"),
            "route_count": discovery.get("route_count"),
            "routes": [item for item in routes if isinstance(item, dict)],
            "error": discovery.get("error"),
            "warnings": discovery.get("warnings") if isinstance(discovery.get("warnings"), list) else [],
            "pages": [self.discovered_page_context(item) for item in pages],
            "api_calls": discovery.get("api_calls") if isinstance(discovery.get("api_calls"), list) else [],
        }

    def discovered_page_context(self, page: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": short_text(page.get("title"), 80),
            "name_hint": short_text(page.get("name_hint"), 80),
            "route": page.get("route"),
            "url": page.get("url"),
            "screenshot_url": page.get("screenshot_url"),
            "screenshot_file": page.get("screenshot_file"),
            "text": short_text(page.get("text"), 1200),
            "visible_actions": page.get("visible_actions") if isinstance(page.get("visible_actions"), list) else [],
            "api_calls": page.get("api_calls") if isinstance(page.get("api_calls"), list) else [],
        }

    def discovered_pages(self, discovery: dict[str, Any]) -> list[dict[str, Any]]:
        pages = discovery.get("captured_pages") if isinstance(discovery.get("captured_pages"), list) else []
        return [item for item in pages if isinstance(item, dict)]

    def interfaces_for_page(
        self,
        interfaces: list[dict[str, Any]],
        api_calls: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not interfaces or not api_calls:
            return []
        paths = {
            str(item.get("path") or "").split("?", 1)[0].rstrip("/")
            for item in api_calls
            if isinstance(item, dict) and item.get("path")
        }
        paths = {path for path in paths if path}
        if not paths:
            return []
        matched: list[dict[str, Any]] = []
        for interface in interfaces:
            data = interface.get("data") if isinstance(interface.get("data"), dict) else {}
            interface_path = str(data.get("path") or "").split("?", 1)[0].rstrip("/")
            if not interface_path:
                continue
            if any(path.endswith(interface_path) or interface_path.endswith(path) for path in paths):
                matched.append(interface)
        return matched[:AI_WEB_PAGE_API_BATCH_SIZE]

    def discovery_result(self, discovery: dict[str, Any]) -> dict[str, Any]:
        context = self.discovery_context(discovery)
        pages = context.get("pages") if isinstance(context.get("pages"), list) else []
        return {
            "enabled": context.get("enabled"),
            "base_url": context.get("base_url"),
            "start_url": context.get("start_url"),
            "auth_loaded": context.get("auth_loaded"),
            "login_executed": context.get("login_executed"),
            "login_record_id": context.get("login_record_id"),
            "login_auth_id": context.get("login_auth_id"),
            "login_final_url": context.get("login_final_url"),
            "route_count": context.get("route_count"),
            "captured_page_count": len(pages),
            "api_call_count": len(context.get("api_calls") or []),
            "routes": context.get("routes") if isinstance(context.get("routes"), list) else [],
            "error": context.get("error"),
            "warnings": context.get("warnings"),
            "pages": [
                {
                    "title": item.get("title"),
                    "route": item.get("route"),
                    "url": item.get("url"),
                    "screenshot_url": item.get("screenshot_url"),
                    "api_call_count": len(item.get("api_calls") or []),
                }
                for item in pages
            ],
        }

    def discovery_warnings(self, discovery: dict[str, Any]) -> list[str]:
        warnings: list[str] = []
        if not discovery or not discovery.get("enabled"):
            return warnings
        if discovery.get("error"):
            warnings.append(f"页面发现失败: {discovery['error']}")
        for item in discovery.get("warnings") or []:
            warnings.append(str(item))
        if not discovery.get("captured_pages") and not discovery.get("error"):
            warnings.append("页面发现未采集到登录后页面，请检查项目地址或 Web 鉴权信息")
        return warnings

    def web_case_context(
        self,
        project: dict[str, Any],
        page: dict[str, Any],
        payload: WebAiGenerationRequest,
    ) -> dict[str, Any]:
        elements: list[dict[str, Any]] = []
        if payload.include_existing_elements:
            rows, _ = self.repository.list(
                "web_elements",
                project_id=payload.project_id,
                page=1,
                page_size=1000,
                data_filters={"page_id": payload.page_id},
            )
            elements = rows

        strategies: list[dict[str, Any]] = []
        if payload.include_strategies:
            rows, _ = self.repository.list("project_knowledge", page=1, page_size=1000)
            strategy_ids = set(payload.strategy_ids)
            strategies = [
                row
                for row in rows
                if is_strategy_for_web(row) and (not strategy_ids or row.get("id") in strategy_ids)
            ]

        context = {
            "project": resource_context(project),
            "page": resource_context(page),
            "existing_elements": [resource_context(item) for item in elements],
            "strategies": [resource_context(item) for item in strategies],
            "dom_snapshot": payload.dom_snapshot or "",
        }
        return sanitize_ai_value(context)

    def _project_context_sources(
        self,
        payload: WebPageAiGenerationRequest,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        existing_pages: list[dict[str, Any]] = []
        if payload.include_existing_pages:
            rows, _ = self.repository.list("web_pages", project_id=payload.project_id, page=1, page_size=2000)
            existing_pages = rows[:AI_WEB_PAGE_MAX_EXISTING_PAGES]

        interfaces: list[dict[str, Any]] = []
        if payload.include_api_interfaces:
            rows, _ = self.repository.list("api_interfaces", project_id=payload.project_id, page=1, page_size=10000)
            interfaces = rows

        knowledge: list[dict[str, Any]] = []
        if payload.include_knowledge:
            rows, _ = self.repository.list("project_knowledge", page=1, page_size=1000)
            knowledge = [row for row in rows if is_strategy_for_web(row)][:AI_WEB_PAGE_MAX_KNOWLEDGE]

        return existing_pages, interfaces, knowledge
