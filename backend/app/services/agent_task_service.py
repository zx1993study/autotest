from __future__ import annotations

import base64
import binascii
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from secrets import token_urlsafe
from typing import Any

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.core.storage import storage_path
from app.services.agent_task_lease_service import AgentTaskLeaseService, lease_expiry
from app.enums.business import AgentTaskStatusEnum, AgentTaskTypeEnum
from app.repositories.interfaces import ResourceRepository
from app.schemas.agent import AgentTaskCreateRequest, AgentTaskReportRequest
from app.services.ai_model_service import AiModelResourceService
from app.services.project_auth_service import ProjectAuthService
from app.services.test_case_service import test_case_table
from app.services.ui_testing_service import UiTestingService
from web_automation.models import MANIFEST_VERSION


AGENT_TASK_TABLE = "agent_tasks"
AUTH_SNAPSHOT_TTL_SECONDS = 300
AI_MODEL_SNAPSHOT_TTL_SECONDS = 300
SCREENSHOT_DIR = storage_path("screenshots")
MAX_AGENT_SCREENSHOT_BYTES = 10 * 1024 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class AgentTaskService:
    """Dispatch and update tasks consumed by installed local agents."""

    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def create(self, payload: AgentTaskCreateRequest, initial_data=None) -> dict[str, Any]:
        """Create a pending task for a specific node or any capable node."""

        task_type = payload.task_type.code
        node_key = payload.node_key or ""
        return self.repository.create(
            AGENT_TASK_TABLE,
            {
                "name": self._task_name(task_type, node_key),
                "status": AgentTaskStatusEnum.PENDING.code,
                "data": {
                    **(initial_data or {}),
                    "task_type": task_type,
                    "node_key": node_key,
                    "payload": payload.payload,
                    "created_at": self._now(),
                },
            },
        )

    def create_case_execution_task(
        self,
        case_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Queue a formal test-case execution task for a local agent."""

        normalized_type = case_type.upper()
        cases = self._load_cases(normalized_type, payload)
        if normalized_type == 'WEB' and any(c.get('data', {}).get('secret_inputs') for c in cases):
            engine = (payload.get('config') or {}).get('engine') or payload.get('engine')
            if engine != 'playwright':
                raise BusinessRuleError('密码用例只能使用 Playwright，不能交给 AI 执行器')
        context = self._execution_context(normalized_type, cases, payload)
        if normalized_type == "APP":
            from app.services.app_agent_execution_service import AppAgentExecutionService

            cases, payload, context = AppAgentExecutionService(self.repository).prepare_formal(cases, payload)
        task_payload: dict[str, Any] = {
            "manifest_version": MANIFEST_VERSION,
            "case_type": normalized_type,
            "execution": payload,
            "cases": cases,
            "context": context,
        }
        return self.create(
            AgentTaskCreateRequest(
                task_type=AgentTaskTypeEnum.CASE_EXECUTION,
                node_key=str(payload.get("node_id") or ""),
                payload=task_payload,
            )
        )

    def claim_next(self, node_key: str, capabilities: list[str]) -> dict[str, Any] | None:
        """Assign the next pending task matching this agent."""

        rows, _ = self.repository.list(
            AGENT_TASK_TABLE,
            page=1,
            page_size=100,
            data_filters={"status": AgentTaskStatusEnum.PENDING.code},
        )
        for task in rows:
            data = self._data(task)
            assigned_node = str(data.get("node_key") or "")
            task_type = str(data.get("task_type") or "")
            if assigned_node and assigned_node != node_key:
                continue
            if not self._capable(task_type, capabilities):
                continue
            if not self._engine_capable(data, capabilities):
                continue
            next_data = {
                **data,
                "node_key": assigned_node or node_key,
                "claimed_by": node_key,
                "claimed_at": self._now(),
                "lease_token": token_urlsafe(24),
                "lease_expires_at": lease_expiry(),
            }
            claimed = self.repository.update_if_status(
                AGENT_TASK_TABLE,
                int(task["id"]),
                AgentTaskStatusEnum.PENDING.code,
                {"status": AgentTaskStatusEnum.RUNNING.code, "data": next_data},
            )
            if claimed:
                return claimed
        return None

    def report(self, task_id: int, payload: AgentTaskReportRequest) -> dict[str, Any] | None:
        """Store an agent task result or failure."""

        task = AgentTaskLeaseService(self.repository).owned_task(task_id, payload.node_key, payload.lease_token)
        if payload.status.code not in {"success", "failed", "canceled"}:
            raise BusinessRuleError("Only terminal execution results can be reported")
        if task.get("status") in {"success", "failed", "canceled"}:
            from app.services.web_vision_agent_service import WebVisionAgentService

            WebVisionAgentService(self.repository).finish(task)
            from app.services.app_agent_execution_service import AppAgentExecutionService

            AppAgentExecutionService(self.repository).finish(task)
            from app.services.agent_device_discovery_service import AgentDeviceDiscoveryService

            AgentDeviceDiscoveryService(self.repository).finish(task)
            return task
        result = self._prepare_execution_result(payload.result)
        completion_error = self._validate_web_completion(task, result)
        status = "failed" if completion_error and payload.status.code == "success" else payload.status.code
        self._apply_web_cache_updates(result)
        data = {
            **self._data(task),
            "reported_by": payload.node_key,
            "finished_at": self._now(),
            "result": result,
            "error": payload.error or completion_error or "",
        }
        updated = self.repository.complete_agent_task(task_id, payload.node_key, status, data, [item for item in result.get("records", []) if isinstance(item, dict)])
        if updated:
            from app.services.web_feature_testing_service import WebFeatureTestingService

            WebFeatureTestingService(self.repository).finish(updated)
            from app.services.generation_repair_service import GenerationRepairService

            GenerationRepairService(self.repository).finish(updated)
            from app.services.web_vision_agent_service import WebVisionAgentService

            WebVisionAgentService(self.repository).finish(updated)
            from app.services.app_agent_execution_service import AppAgentExecutionService

            AppAgentExecutionService(self.repository).finish(updated)
            from app.services.agent_device_discovery_service import AgentDeviceDiscoveryService

            AgentDeviceDiscoveryService(self.repository).finish(updated)
        return updated

    def consume_auth_context(
        self,
        task_id: int,
        node_key: str,
        snapshot_id: str | None = None,
    ) -> dict[str, Any]:
        """Return and consume a short-lived auth snapshot for a claimed task."""

        task = self.repository.get(AGENT_TASK_TABLE, task_id)
        if not task:
            raise ResourceNotFoundError("未找到 Agent 任务")
        data = self._data(task)
        if str(data.get("claimed_by") or "") != node_key:
            raise BusinessRuleError("当前节点无权读取该任务的鉴权上下文")
        if str(task.get("status") or "") != AgentTaskStatusEnum.RUNNING.code:
            raise BusinessRuleError("只有执行中的 Agent 任务可以读取鉴权上下文")

        snapshot = self._select_auth_snapshot(data, snapshot_id)
        if not snapshot:
            return {}
        if snapshot.get("used_at"):
            raise BusinessRuleError("鉴权快照已使用，请重新投递任务")
        if self._snapshot_expired(snapshot):
            raise BusinessRuleError("鉴权快照已过期，请重新投递任务")

        auth_id = self._to_int(snapshot.get("auth_id"))
        if auth_id is None:
            return {}
        auth_service = ProjectAuthService(self.repository)
        target_url = str(snapshot.get("target_url") or "")
        auth_context = auth_service.web_auth_context(auth_id, target_url)
        if not auth_context:
            raise BusinessRuleError("未获取到可用鉴权上下文，请刷新鉴权信息")
        self._mark_auth_snapshot_used(task, str(snapshot.get("snapshot_id") or ""))
        return {
            **auth_context,
            "snapshot_id": snapshot.get("snapshot_id"),
            "expires_at": snapshot.get("expires_at"),
        }

    def consume_ai_model_context(
        self,
        task_id: int,
        node_key: str,
        snapshot_id: str | None = None,
    ) -> dict[str, Any]:
        """Consume a model reference; provider credentials remain on the server."""

        task = self.repository.get(AGENT_TASK_TABLE, task_id)
        if not task:
            raise ResourceNotFoundError("未找到 Agent 任务")
        data = self._data(task)
        if str(data.get("claimed_by") or "") != node_key:
            raise BusinessRuleError("当前节点无权读取该任务的 AI 模型上下文")
        if str(task.get("status") or "") != AgentTaskStatusEnum.RUNNING.code:
            raise BusinessRuleError("只有执行中的 Agent 任务可以读取 AI 模型上下文")

        snapshot = self._select_ai_model_snapshot(data, snapshot_id)
        if not snapshot:
            return {}
        if snapshot.get("used_at"):
            raise BusinessRuleError("AI 模型快照已使用，请重新投递任务")
        if self._snapshot_expired(snapshot):
            raise BusinessRuleError("AI 模型快照已过期，请重新投递任务")

        model_id = self._to_int(snapshot.get("model_id"))
        model_service = AiModelResourceService(self.repository)
        model = model_service.active_model(model_id)
        api_key = model_service.api_key(model)
        if not api_key:
            raise BusinessRuleError("AI 模型未配置 API Key，无法使用 AI 执行引擎")
        self._mark_ai_model_snapshot_used(task, str(snapshot.get("snapshot_id") or ""))
        return {**snapshot, "transport": "platform_proxy"}

    def list_tasks(self, page: int = 1, page_size: int = 100) -> tuple[list[dict[str, Any]], int]:
        """Return agent tasks for platform-side troubleshooting."""

        return self.repository.list(AGENT_TASK_TABLE, page=page, page_size=page_size)

    def get_task(self, task_id: int) -> dict[str, Any]:
        task = self.repository.get(AGENT_TASK_TABLE, task_id)
        if not task:
            raise ResourceNotFoundError("Agent task does not exist")
        return task

    def _load_cases(self, case_type: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        case_ids = [int(case_id) for case_id in payload.get("case_ids", []) if case_id]
        if not case_ids:
            raise BusinessRuleError("请选择要执行的用例")

        table = test_case_table(case_type)
        cases: list[dict[str, Any]] = []
        for case_id in case_ids:
            item = self.repository.get(table, case_id)
            if item:
                cases.append(self._normalize_case(case_type, item))
        if not cases:
            raise ResourceNotFoundError("未找到可执行的正式用例")
        return cases

    def _normalize_case(self, case_type: str, case: dict[str, Any]) -> dict[str, Any]:
        data = case.get("data") if isinstance(case.get("data"), dict) else {}
        clean_data = {
            key: value
            for key, value in data.items()
            if key not in {"assertions", "strategies", "strategy", "strategy_ids"}
        }
        clean_data.setdefault("case_type", case_type)
        return {**case, "case_type": case_type, "data": clean_data}

    def _execution_context(
        self,
        case_type: str,
        cases: list[dict[str, Any]],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if case_type != "WEB":
            return {}
        project_ids = {
            int(value)
            for value in [payload.get("project_id"), *(case.get("project_id") for case in cases)]
            if self._to_int(value) is not None
        }
        page_ids = {
            int(case["source_id"])
            for case in cases
            if self._to_int(case.get("source_id")) is not None
        }
        pages = self._records_by_id("web_pages", page_ids)
        projects = self._records_by_id("projects", project_ids)
        elements = self._web_elements(page_ids, project_ids)
        auth_snapshots = self._auth_snapshot_refs(cases, payload, pages, projects)
        context: dict[str, Any] = {
            "pages": pages,
            "projects": projects,
            "elements": elements,
            "auth_snapshot": next(iter(auth_snapshots.values()), {}),
            "auth_snapshots": auth_snapshots,
        }
        ai_model = self._ai_model_snapshot(payload)
        if ai_model:
            context["ai_model"] = ai_model
        return context

    def _ai_model_snapshot(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Attach a model reference, never provider credentials."""

        config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
        engine = str(config.get("engine") or "").strip().lower()
        if engine not in {"stagehand", "hybrid"}:
            return None
        model_service = AiModelResourceService(self.repository)
        model = model_service.active_model(self._to_int(config.get("model_id")))
        data = model.get("data") if isinstance(model.get("data"), dict) else {}
        expires_at = self._now_datetime() + timedelta(seconds=AI_MODEL_SNAPSHOT_TTL_SECONDS)
        return {
            "snapshot_id": f"ai_{token_urlsafe(18)}",
            "model_id": model.get("id"),
            "model_name": data.get("model"),
            "base_url": data.get("base_url"),
            "timeout_sec": data.get("timeout_sec"),
            "expires_at": expires_at.isoformat(timespec="seconds"),
            "ttl_seconds": AI_MODEL_SNAPSHOT_TTL_SECONDS,
            "used_at": "",
        }

    def _auth_snapshot_refs(
        self,
        cases: list[dict[str, Any]],
        payload: dict[str, Any],
        pages: dict[str, dict[str, Any]],
        projects: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        if self._truthy(payload.get("skip_auth")):
            return {}
        expires_at = self._now_datetime() + timedelta(seconds=AUTH_SNAPSHOT_TTL_SECONDS)
        snapshots: dict[str, dict[str, Any]] = {}
        for case in cases:
            case_id = self._to_int(case.get("id"))
            auth_id = self._web_auth_id(case, payload, pages, projects)
            if case_id is None or auth_id is None:
                continue
            snapshots[str(case_id)] = {
                "snapshot_id": f"auth_{token_urlsafe(18)}",
                "auth_id": auth_id,
                "case_id": case_id,
                "target_url": self._target_url(case, pages, projects),
                "expires_at": expires_at.isoformat(timespec="seconds"),
                "ttl_seconds": AUTH_SNAPSHOT_TTL_SECONDS,
                "used_at": "",
            }
        return snapshots

    def _web_auth_id(
        self,
        case: dict[str, Any],
        payload: dict[str, Any],
        pages: dict[str, dict[str, Any]],
        projects: dict[str, dict[str, Any]],
    ) -> int | None:
        if self._to_int(payload.get("auth_id")) is not None:
            return self._to_int(payload.get("auth_id"))
        case_data = self._record_data(case)
        request = case_data.get("request") if isinstance(case_data.get("request"), dict) else {}
        for value in (case_data.get("auth_id"), request.get("auth_id")):
            parsed = self._to_int(value)
            if parsed is not None:
                return parsed
        page = pages.get(str(case.get("source_id")))
        page_data = self._record_data(page)
        parsed = self._to_int(page_data.get("auth_id"))
        if parsed is not None:
            return parsed
        return self._default_web_auth_id(case.get("project_id"), projects)

    def _default_web_auth_id(
        self,
        project_id: Any,
        projects: dict[str, dict[str, Any]],
    ) -> int | None:
        parsed_project_id = self._to_int(project_id)
        if parsed_project_id is None:
            return None
        rows, _ = self.repository.list("project_auth", project_id=parsed_project_id, page=1, page_size=500)
        web_rows = [
            row
            for row in rows
            if str(self._record_data(row).get("login_case_type") or "").upper() == "WEB"
        ]
        chosen = next((row for row in web_rows if str(row.get("status") or "") == "active"), None)
        chosen = chosen or (web_rows[0] if web_rows else None)
        return self._to_int((chosen or {}).get("id"))

    def _target_url(
        self,
        case: dict[str, Any],
        pages: dict[str, dict[str, Any]],
        projects: dict[str, dict[str, Any]],
    ) -> str:
        case_data = self._record_data(case)
        request = case_data.get("request") if isinstance(case_data.get("request"), dict) else {}
        for value in (case_data.get("url"), request.get("url")):
            if value:
                return str(value)
        page = pages.get(str(case.get("source_id")))
        page_data = self._record_data(page)
        page_url = str(page_data.get("url") or "")
        if page_url.startswith(("http://", "https://")):
            return page_url
        base_url = self._project_base_url(case.get("project_id"), projects)
        if base_url and page_url:
            return f"{base_url.rstrip('/')}/{'/'.join(part for part in page_url.split('/') if part)}"
        return base_url

    def _project_base_url(self, project_id: Any, projects: dict[str, dict[str, Any]]) -> str:
        project = projects.get(str(project_id))
        project_data = self._record_data(project)
        return str(project_data.get("base_url") or project_data.get("project_url") or project_data.get("url") or "").strip()

    def _records_by_id(self, table: str, ids: set[int]) -> dict[str, dict[str, Any]]:
        records: dict[str, dict[str, Any]] = {}
        for item_id in ids:
            item = self.repository.get(table, item_id)
            if item:
                records[str(item_id)] = item
        return records

    def _web_elements(self, page_ids: set[int], project_ids: set[int]) -> list[dict[str, Any]]:
        if not page_ids and not project_ids:
            return []
        rows: list[dict[str, Any]] = []
        project_filter_values: set[int | None] = set(project_ids) if project_ids else {None}
        for project_id in project_filter_values:
            items, _ = self.repository.list(
                "web_elements",
                project_id=project_id,
                page_size=10000,
            )
            rows.extend(items)
        if page_ids:
            rows = [
                row
                for row in rows
                if self._to_int((row.get("data") or {}).get("page_id")) in page_ids
            ]
        seen: set[int] = set()
        result: list[dict[str, Any]] = []
        for row in rows:
            row_id = self._to_int(row.get("id"))
            if row_id is not None and row_id in seen:
                continue
            if row_id is not None:
                seen.add(row_id)
            result.append(row)
        return result

    def _apply_web_cache_updates(self, result: dict[str, Any]) -> None:
        records = result.get("records")
        if not isinstance(records, list):
            return
        service = UiTestingService("web_pages", "web_elements", self.repository)
        for record in records:
            data = record.get("data") if isinstance(record, dict) and isinstance(record.get("data"), dict) else {}
            invalidations = data.get("cache_invalidations") if isinstance(data.get("cache_invalidations"), list) else []
            for element_id in invalidations:
                normalized_id = self._to_int(element_id)
                if normalized_id is not None:
                    service.invalidate_ai_cache(normalized_id)
            updates = data.get("cache_updates") if isinstance(data.get("cache_updates"), list) else []
            for update in updates:
                if not isinstance(update, dict):
                    continue
                element_id = self._to_int(update.get("element_id"))
                cache = update.get("cache") if isinstance(update.get("cache"), dict) else None
                if element_id is not None and cache:
                    service.update_ai_cache(element_id, cache)

    def _prepare_execution_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Persist Agent artifact payloads before records are saved.

        Local headed execution runs on a user's machine, while detail pages read
        screenshots from the server. The Agent therefore returns image content
        once, and the platform converts it into the normal screenshot endpoint.
        """

        prepared = deepcopy(result) if isinstance(result, dict) else {}
        records = prepared.get("records")
        if not isinstance(records, list):
            return prepared
        for record in records:
            if isinstance(record, dict):
                self._prepare_record_screenshots(record)
        return prepared

    def _validate_web_completion(self, task: dict[str, Any], result: dict[str, Any]) -> str | None:
        payload = self._data(task).get("payload") or {}
        if self._data(task).get("task_type") != "case_execution" or payload.get("case_type") != "WEB":
            return None
        cases = {c["id"] for c in payload.get("cases", [])}
        if not cases:
            return None
        records = [r for r in result.get("records", []) if isinstance(r, dict)]
        error = None
        if {r.get("data", {}).get("case_id") for r in records} != cases or len(records) != len(cases):
            error = "Agent 回传的用例结果不完整，不能判定执行成功"
        for record in records:
            data = record.get("data") or {}
            if record.get("status") == "success" and (data.get("business_result") != "passed" or not data.get("assertion_count")):
                error = "Agent 未提供通过的业务结果验证，不能将操作完成判定为功能成功"
                record.update(status="failed", description=error)
                record["data"] = {**data, "error": error, "result_label": "业务结果未验证"}
        result.update(total=len(cases), success_count=sum(r.get("status") == "success" for r in records),
                      failed_count=sum(r.get("status") == "failed" for r in records))
        if any(r.get("status") != "success" for r in records):
            error = error or "存在未通过的页面功能用例"
        return error

    def _prepare_record_screenshots(self, record: dict[str, Any]) -> None:
        data = record.get("data")
        if not isinstance(data, dict):
            return
        screenshots = data.get("screenshots")
        if not isinstance(screenshots, list):
            return
        normalized = [item for item in screenshots if isinstance(item, dict)]
        for screenshot in normalized:
            self._store_agent_screenshot(screenshot)
        self._apply_last_screenshot_metadata(data, normalized)

    def _store_agent_screenshot(self, screenshot: dict[str, Any]) -> None:
        encoded = screenshot.pop("screenshot_base64", None) or screenshot.pop("content_base64", None)
        screenshot.pop("local_path", None)
        filename = self._safe_screenshot_filename(screenshot.get("screenshot_file"))
        if encoded:
            try:
                raw = base64.b64decode(str(encoded), validate=True)
                if not raw or len(raw) > MAX_AGENT_SCREENSHOT_BYTES or not raw.startswith(PNG_SIGNATURE):
                    raise ValueError("invalid png screenshot payload")
                SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
                filename = self._available_screenshot_filename(filename)
                (SCREENSHOT_DIR / filename).write_bytes(raw)
            except (binascii.Error, OSError, ValueError) as exc:
                screenshot["screenshot_error"] = f"Agent 截图保存失败：{exc}"
                return
        elif not (SCREENSHOT_DIR / filename).exists():
            return
        screenshot["screenshot_file"] = filename
        screenshot["screenshot_url"] = f"/api/v1/screenshots/{filename}"

    def _safe_screenshot_filename(self, value: Any) -> str:
        filename = Path(str(value or "")).name
        if not filename.lower().endswith(".png"):
            return f"agent_{token_urlsafe(10)}.png"
        return filename

    def _available_screenshot_filename(self, filename: str) -> str:
        path = SCREENSHOT_DIR / filename
        if not path.exists():
            return filename
        stem = path.stem or "agent_screenshot"
        return f"{stem}_{token_urlsafe(6)}.png"

    def _apply_last_screenshot_metadata(
        self,
        data: dict[str, Any],
        screenshots: list[dict[str, Any]],
    ) -> None:
        for screenshot in reversed(screenshots):
            if screenshot.get("screenshot_url"):
                data["screenshot_url"] = screenshot.get("screenshot_url")
                data["screenshot_file"] = screenshot.get("screenshot_file")
                return
        errors = [str(item.get("screenshot_error")) for item in screenshots if item.get("screenshot_error")]
        if errors:
            data["screenshot_error"] = "; ".join(errors)

    def _task_name(self, task_type: str, node_key: str) -> str:
        target = node_key or "任意节点"
        return f"{task_type} - {target}"

    def _data(self, task: dict[str, Any]) -> dict[str, Any]:
        data = task.get("data")
        return data if isinstance(data, dict) else {}

    def _record_data(self, record: dict[str, Any] | None) -> dict[str, Any]:
        data = record.get("data") if isinstance(record, dict) else None
        return data if isinstance(data, dict) else {}

    def _select_auth_snapshot(
        self,
        task_data: dict[str, Any],
        snapshot_id: str | None,
    ) -> dict[str, Any] | None:
        task_payload = task_data.get("payload") if isinstance(task_data.get("payload"), dict) else {}
        context = task_payload.get("context") if isinstance(task_payload.get("context"), dict) else {}
        snapshots = context.get("auth_snapshots") if isinstance(context.get("auth_snapshots"), dict) else {}
        candidates = [item for item in snapshots.values() if isinstance(item, dict)]
        default_snapshot = context.get("auth_snapshot") if isinstance(context.get("auth_snapshot"), dict) else None
        if default_snapshot:
            candidates.append(default_snapshot)
        if snapshot_id:
            return next((item for item in candidates if item.get("snapshot_id") == snapshot_id), None)
        return candidates[0] if candidates else None

    def _mark_auth_snapshot_used(self, task: dict[str, Any], snapshot_id: str) -> None:
        if not snapshot_id:
            return
        task_data = dict(self._data(task))
        task_payload = dict(task_data.get("payload") if isinstance(task_data.get("payload"), dict) else {})
        context = dict(task_payload.get("context") if isinstance(task_payload.get("context"), dict) else {})
        used_at = self._now()

        snapshots = dict(context.get("auth_snapshots") if isinstance(context.get("auth_snapshots"), dict) else {})
        for key, value in list(snapshots.items()):
            if isinstance(value, dict) and value.get("snapshot_id") == snapshot_id:
                snapshots[key] = {**value, "used_at": used_at}
        context["auth_snapshots"] = snapshots

        default_snapshot = context.get("auth_snapshot")
        if isinstance(default_snapshot, dict) and default_snapshot.get("snapshot_id") == snapshot_id:
            context["auth_snapshot"] = {**default_snapshot, "used_at": used_at}

        task_payload["context"] = context
        task_data["payload"] = task_payload
        self.repository.update(AGENT_TASK_TABLE, int(task["id"]), {"data": task_data})

    def _select_ai_model_snapshot(
        self,
        task_data: dict[str, Any],
        snapshot_id: str | None,
    ) -> dict[str, Any] | None:
        task_payload = task_data.get("payload") if isinstance(task_data.get("payload"), dict) else {}
        context = task_payload.get("context") if isinstance(task_payload.get("context"), dict) else {}
        snapshot = context.get("ai_model") if isinstance(context.get("ai_model"), dict) else None
        if not snapshot:
            return None
        if snapshot_id and snapshot.get("snapshot_id") != snapshot_id:
            return None
        return snapshot

    def _mark_ai_model_snapshot_used(self, task: dict[str, Any], snapshot_id: str) -> None:
        if not snapshot_id:
            return
        task_data = dict(self._data(task))
        task_payload = dict(task_data.get("payload") if isinstance(task_data.get("payload"), dict) else {})
        context = dict(task_payload.get("context") if isinstance(task_payload.get("context"), dict) else {})
        snapshot = context.get("ai_model")
        if isinstance(snapshot, dict) and snapshot.get("snapshot_id") == snapshot_id:
            context["ai_model"] = {**snapshot, "used_at": self._now()}
        task_payload["context"] = context
        task_data["payload"] = task_payload
        self.repository.update(AGENT_TASK_TABLE, int(task["id"]), {"data": task_data})

    def _snapshot_expired(self, snapshot: dict[str, Any]) -> bool:
        expires_at = self._parse_datetime(snapshot.get("expires_at"))
        return expires_at is None or expires_at < self._now_datetime()

    def _capable(self, task_type: str, capabilities: list[str]) -> bool:
        if not capabilities:
            return True
        return task_type in capabilities or "*" in capabilities

    def _engine_capable(self, task_data: dict[str, Any], capabilities: list[str]) -> bool:
        if not capabilities or "*" in capabilities:
            return True
        payload = task_data.get("payload") if isinstance(task_data.get("payload"), dict) else {}
        if payload.get('recording'):
            return 'web_recording' in capabilities
        candidates = [payload.get('candidate') or {}] + (payload.get('cases') or [])
        if any(c.get('data', {}).get('secret_inputs') for c in payload.get('cases') or []) and 'web_secret_inputs' not in capabilities:
            return False
        if any(s.get('action') == 'manual' for c in candidates for s in c.get('steps') or []):
            return 'web_recording' in capabilities
        if str(task_data.get("task_type") or "") != AgentTaskTypeEnum.CASE_EXECUTION.code:
            return True
        if str(payload.get("case_type") or "").upper() != "WEB":
            return str(payload.get("case_type") or "").upper() != "APP" or "app_execution" in capabilities
        execution = payload.get("execution") if isinstance(payload.get("execution"), dict) else {}
        config = execution.get("config") if isinstance(execution.get("config"), dict) else {}
        engine = str(config.get("engine") or execution.get("engine") or "").strip().lower()
        if engine not in {"stagehand", "hybrid"}:
            return True
        return "stagehand" in {str(item) for item in capabilities}

    def _to_int(self, value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _parse_datetime(self, value: Any) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    def _truthy(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "是"}

    def _now_datetime(self) -> datetime:
        return datetime.now(timezone.utc)

    def _now(self) -> str:
        return self._now_datetime().isoformat(timespec="seconds")
