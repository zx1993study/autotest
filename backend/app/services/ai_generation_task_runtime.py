from __future__ import annotations

import time
from typing import Any

from fastapi import HTTPException, status

from app.constants.ai_generation import AI_TASK_RESULT_SUMMARY_FIELDS, AI_TASK_RUNTIME_FIELDS
from app.repositories.interfaces import ResourceRepository
from app.schemas.ai import WebFunctionElementGenerationRequest, WebPageAiGenerationRequest
from app.services.ai_task_detail_file_service import AiTaskDetailFileService
from app.services.resource_service import ResourceService
from app.utils.ai_generation_utils import int_list, int_or_default, optional_int, sanitize_ai_value


class AiGenerationTaskRuntime:
    """Owns AI generation task state transitions and task payload recovery."""

    def __init__(
        self,
        repository: ResourceRepository,
        task_service: ResourceService,
        detail_files: AiTaskDetailFileService,
    ) -> None:
        self.repository = repository
        self.task_service = task_service
        self.detail_files = detail_files

    def create_task(
        self,
        name: str,
        project_id: int,
        task_type: str,
        data: dict[str, Any],
        status_text: str = "running",
    ) -> dict[str, Any]:
        task_data = {"task_type": task_type, **data}
        return self.task_service.create(
            {
                "name": name,
                "project_id": project_id,
                "status": status_text,
                "data": task_data,
            }
        )

    def update_task_status(self, task_id: int, status_text: str, data_patch: dict[str, Any]) -> None:
        current = self.repository.get("ai_generation_tasks", task_id) or {}
        data = dict(current.get("data") or {})
        data.update({"status": status_text, **sanitize_ai_value(data_patch)})
        self.task_service.update(task_id, {"status": status_text, "data": data})

    def reset_for_run(self, task_id: int) -> None:
        current = self.repository.get("ai_generation_tasks", task_id) or {}
        data = self.task_data_without_runtime(current)
        data.update({"status": "running", "started_at": int(time.time())})
        self.task_service.update(task_id, {"status": "running", "data": data})

    def reset_for_queue(self, task_id: int) -> None:
        current = self.repository.get("ai_generation_tasks", task_id) or {}
        data = self.task_data_without_runtime(current)
        data.update({"status": "queued", "queued_at": int(time.time())})
        self.task_service.update(task_id, {"status": "queued", "data": data})

    def finish_task(self, task_id: int, status_text: str, result: dict[str, Any]) -> None:
        current = self.repository.get("ai_generation_tasks", task_id) or {}
        data = dict(current.get("data") or {})
        finished_at = int(time.time())
        started_at = self.safe_timestamp(data.get("started_at"))
        duration_minutes = round((finished_at - started_at) / 60, 2) if started_at else None
        progress_text = "执行完成" if status_text in {"success", "partial_success"} else "执行失败"
        safe_result = sanitize_ai_value(result)
        result_file = self.detail_files.save_result(task_id, safe_result)
        data.update(
            {
                "status": status_text,
                "result": self.task_result_summary(safe_result),
                "result_file": result_file,
                "result_updated_at": finished_at,
                "finished_at": finished_at,
                "progress": progress_text,
            }
        )
        if duration_minutes is not None and duration_minutes >= 0:
            data["duration_minutes"] = duration_minutes
        self.task_service.update(task_id, {"status": status_text, "data": data})

    def task_type(self, task: dict[str, Any]) -> str:
        data = task.get("data") if isinstance(task.get("data"), dict) else {}
        return str(data.get("task_type") or "")

    def web_page_payload_from_task(self, task: dict[str, Any]) -> WebPageAiGenerationRequest:
        data = task.get("data") if isinstance(task.get("data"), dict) else {}
        raw_payload = data.get("payload") if isinstance(data.get("payload"), dict) else data
        project_id = task.get("project_id") or raw_payload.get("project_id")
        if not project_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="任务缺少项目")
        return WebPageAiGenerationRequest(
            project_id=int(project_id),
            model_id=optional_int(raw_payload.get("model_id")),
            prompt_template_id=optional_int(raw_payload.get("prompt_template_id")),
            login_case_id=optional_int(raw_payload.get("login_case_id")),
            user_prompt=raw_payload.get("user_prompt"),
            dry_run=False,
            overwrite_existing=bool(raw_payload.get("overwrite_existing", False)),
            include_existing_pages=bool(raw_payload.get("include_existing_pages", True)),
            include_api_interfaces=bool(raw_payload.get("include_api_interfaces", True)),
            include_knowledge=bool(raw_payload.get("include_knowledge", True)),
            discover_after_login=bool(raw_payload.get("discover_after_login", True)),
            discovery_max_pages=int_or_default(raw_payload.get("discovery_max_pages"), 30),
            discovery_timeout_ms=int_or_default(raw_payload.get("discovery_timeout_ms"), 15000),
            discovery_wait_ms=int_or_default(raw_payload.get("discovery_wait_ms"), 1000),
            discovery_headless=bool(raw_payload.get("discovery_headless", True)),
        )

    def web_function_element_payload_from_task(self, task: dict[str, Any]) -> WebFunctionElementGenerationRequest:
        data = task.get("data") if isinstance(task.get("data"), dict) else {}
        raw_payload = data.get("payload") if isinstance(data.get("payload"), dict) else data
        project_id = task.get("project_id") or raw_payload.get("project_id")
        if not project_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="任务缺少项目")
        return WebFunctionElementGenerationRequest(
            project_id=int(project_id),
            model_id=optional_int(raw_payload.get("model_id")),
            prompt_template_id=optional_int(raw_payload.get("prompt_template_id")),
            login_case_id=optional_int(raw_payload.get("login_case_id")),
            user_prompt=raw_payload.get("user_prompt"),
            scan_scope=str(raw_payload.get("scan_scope") or "single"),
            page_id=optional_int(raw_payload.get("page_id")),
            page_ids=int_list(raw_payload.get("page_ids")),
            operation_timeout_sec=int_or_default(
                raw_payload.get("operation_timeout_sec") or raw_payload.get("recording_timeout_sec"),
                120,
            ),
            headless=True,
            scan_instruction=raw_payload.get("scan_instruction"),
            existing_element_strategy=str(raw_payload.get("existing_element_strategy") or "update"),
        )

    def task_data_without_runtime(self, task: dict[str, Any]) -> dict[str, Any]:
        data = dict(task.get("data") or {})
        for key in AI_TASK_RUNTIME_FIELDS:
            data.pop(key, None)
        return data

    def task_result_summary(self, result: dict[str, Any]) -> dict[str, Any]:
        """Keep list-page result data small while preserving useful counters."""

        summary = {key: result[key] for key in AI_TASK_RESULT_SUMMARY_FIELDS if key in result}
        pages = result.get("pages")
        if isinstance(pages, list):
            summary.setdefault("page_count", len(pages))
        failed_pages = result.get("failed_pages")
        if isinstance(failed_pages, list):
            summary["failed_page_count"] = len(failed_pages)
            summary["failed_pages"] = failed_pages[:10]
        return summary

    @staticmethod
    def safe_timestamp(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
