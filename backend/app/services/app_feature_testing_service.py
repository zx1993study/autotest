from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.repositories.interfaces import ResourceRepository
from app.services.app_agent_execution_service import AppAgentExecutionService
from app.services.app_scenario_generation_service import AppScenarioGenerationService

FEATURE_TABLE = "app_features"
SCENARIO_TABLE = "app_feature_scenarios"
RUN_TABLE = "app_scenario_runs"


class AppFeatureTestingService:
    """Coordinate the feature -> scenario -> evidence App testing workflow."""

    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository
        self.generator = AppScenarioGenerationService(repository)

    def list_features(
        self,
        *,
        project_id: int | None,
        device_id: int | None,
        keyword: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        filters = {"status": status} if status else {}
        if device_id is not None:
            filters["device_id"] = device_id
        rows, total = self.repository.list(
            FEATURE_TABLE, keyword=keyword, project_id=project_id, page=page, page_size=page_size, data_filters=filters,
        )
        summaries = self.repository.app_feature_summaries([int(row["id"]) for row in rows]) if rows else {}
        return [self._enrich_feature(row, summaries[int(row["id"])]) for row in rows], total

    def get_feature(self, feature_id: int) -> dict[str, Any]:
        return self._enrich_feature(self._required(FEATURE_TABLE, feature_id, "App 功能不存在"))

    def create_feature(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = dict(payload)
        data = dict(payload.get("data") or {})
        data.setdefault("platforms", ["Android", "iOS"])
        data.setdefault("device_form_factors", ["phone", "tablet"])
        payload["data"] = data
        payload.setdefault("status", "active")
        return self.repository.create(FEATURE_TABLE, payload)

    def update_feature(self, feature_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        item = self.repository.update(FEATURE_TABLE, feature_id, payload)
        if not item:
            raise ResourceNotFoundError("App 功能不存在")
        return self._enrich_feature(item)

    def delete_feature(self, feature_id: int) -> bool:
        self._required(FEATURE_TABLE, feature_id, "App 功能不存在")
        scenarios, _ = self.repository.list(SCENARIO_TABLE, page=1, page_size=10000, data_filters={"feature_id": feature_id})
        for scenario in scenarios:
            self.repository.delete(SCENARIO_TABLE, int(scenario["id"]))
        if not self.repository.delete(FEATURE_TABLE, feature_id):
            raise ResourceNotFoundError("App 功能不存在")
        return True

    def list_scenarios(
        self,
        feature_id: int,
        *,
        device_id: int | None,
        keyword: str | None,
        status: str | None,
        source_type: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        feature = self._required(FEATURE_TABLE, feature_id, "App 功能不存在")
        data_filters: dict[str, Any] = {"feature_id": feature_id}
        if status:
            data_filters["status"] = status
        if source_type:
            data_filters["source_type"] = source_type
        if device_id is not None:
            data_filters["device_id"] = device_id
        rows, total = self.repository.list(
            SCENARIO_TABLE,
            keyword=keyword,
            project_id=self._optional_int(feature.get("project_id")),
            page=page,
            page_size=page_size,
            data_filters=data_filters,
        )
        return [self._enrich_scenario(row) for row in rows], total

    def create_scenario(self, feature_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        feature = self._required(FEATURE_TABLE, feature_id, "App 功能不存在")
        feature_data = feature.get("data") if isinstance(feature.get("data"), dict) else {}
        data = self._scenario_data(
            feature,
            {
                "source_type": payload.get("source_type") or "manual",
                "device_id": payload.get("device_id") or feature_data.get("default_device_id"),
                "entry_id": payload.get("entry_id") or feature_data.get("default_entry_id"),
                "record_video": payload.get("record_video", True),
                "start_from_current_screen": payload.get("start_from_current_screen", True),
                "operation_steps": payload.get("operation_steps") or [],
                "input_info": payload.get("input_info") or {},
                "variables": payload.get("variables") or {},
                "assertions": payload.get("assertions") or [],
                "generation_meta": payload.get("generation_meta") or {},
                "knowledge_refs": payload.get("knowledge_refs") or [],
                "generation_notes": payload.get("generation_notes"),
            },
        )
        scenario = self.repository.create(
            SCENARIO_TABLE,
            {
                "name": payload.get("name") or "未命名场景",
                "project_id": feature.get("project_id"),
                "description": payload.get("description"),
                "status": payload.get("status") or "active",
                "data": data,
            },
        )
        return self._enrich_scenario(scenario)

    def update_scenario(self, scenario_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        scenario = self._required(SCENARIO_TABLE, scenario_id, "App 场景不存在")
        current_data = scenario.get("data") if isinstance(scenario.get("data"), dict) else {}
        next_data = dict(current_data)
        for key in (
            "device_id",
            "entry_id",
            "record_video",
            "start_from_current_screen",
            "operation_steps",
            "input_info",
            "variables",
            "assertions",
        ):
            if key in payload and payload[key] is not None:
                next_data[key] = payload[key]
        update_payload = {key: value for key, value in payload.items() if key in {"name", "description", "status"} and value is not None}
        update_payload["data"] = next_data
        updated = self.repository.update(SCENARIO_TABLE, scenario_id, update_payload)
        if not updated:
            raise ResourceNotFoundError("App 场景不存在")
        return self._enrich_scenario(updated)

    def get_scenario(self, scenario_id: int) -> dict[str, Any]:
        return self._enrich_scenario(self._required(SCENARIO_TABLE, scenario_id, "App 场景不存在"))

    def update_input_info(self, scenario_id: int, input_info: dict[str, Any]) -> dict[str, Any]:
        scenario = self._required(SCENARIO_TABLE, scenario_id, "App 场景不存在")
        data = dict(scenario.get("data") if isinstance(scenario.get("data"), dict) else {})
        data["input_info"] = input_info
        updated = self.repository.update(SCENARIO_TABLE, scenario_id, {"data": data})
        if not updated:
            raise ResourceNotFoundError("App 场景不存在")
        return self._enrich_scenario(updated)

    def generate_scenario_from_text(self, feature_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        feature = self._required(FEATURE_TABLE, feature_id, "App 功能不存在")
        project_id = self._positive_int(feature.get("project_id"), "功能必须关联项目后才能生成场景")
        feature_data = feature.get("data") if isinstance(feature.get("data"), dict) else {}
        generation_payload = {
            "project_id": project_id,
            "prompt": payload.get("prompt"),
            "model_id": payload.get("model_id"),
            "entry_id": payload.get("entry_id") or feature_data.get("default_entry_id"),
            "feature_id": feature_id,
            "device_id": payload.get("device_id") or feature_data.get("default_device_id"),
            "start_from_current_screen": payload.get("start_from_current_screen", True),
            "record_video": payload.get("record_video", True),
            "include_knowledge": payload.get("include_knowledge", True),
            "knowledge_ids": payload.get("knowledge_ids") or [],
            "save_draft": False,
            "dry_run": payload.get("dry_run", False),
            "allow_rule_fallback": payload.get("allow_rule_fallback", True),
        }
        generated = self.generator.generate_from_text(generation_payload)
        case_json = generated["case_json"]
        scenario_payload = self._scenario_payload_from_case_json(feature, case_json, payload, "natural_language")
        scenario_payload["name"] = payload.get("name") or case_json.get("name") or scenario_payload["name"]
        scenario_payload["generation_meta"] = self._generation_meta(generated, generation_payload)
        scenario_payload["knowledge_refs"] = case_json.get("knowledge_refs") if isinstance(case_json.get("knowledge_refs"), list) else []
        scenario_payload["generation_notes"] = case_json.get("generation_notes")
        if payload.get("dry_run"):
            return {"scenario_preview": scenario_payload, "generation": generated}
        scenario = self.create_scenario(feature_id, scenario_payload)
        return {"scenario": scenario, "generation": generated}

    def generate_scenario_from_recording(self, feature_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        feature = self._required(FEATURE_TABLE, feature_id, "App 功能不存在")
        project_id = self._positive_int(feature.get("project_id"), "功能必须关联项目后才能生成场景")
        events = payload.get("events") if isinstance(payload.get("events"), list) else []
        if events:
            generated = self.generator.generate_from_events(
                {
                    "project_id": project_id,
                    "name": payload.get("name"),
                    "entry_id": payload.get("entry_id"),
                    "events": events,
                    "record_video": payload.get("record_video", True),
                    "start_from_current_screen": payload.get("start_from_current_screen", True),
                    "save_draft": False,
                }
            )
            scenario_payload = self._scenario_payload_from_case_json(feature, generated["case_json"], payload, "recording")
            scenario_payload["name"] = payload.get("name") or scenario_payload["name"]
        else:
            scenario_payload = {
                "name": payload.get("name") or "录制生成场景",
                "description": "已创建录制场景；后续接入设备事件采集后会自动回填操作步骤。",
                "status": "active",
                "source_type": "recording",
                "device_id": payload.get("device_id"),
                "entry_id": payload.get("entry_id"),
                "record_video": payload.get("record_video", True),
                "start_from_current_screen": payload.get("start_from_current_screen", True),
                "operation_steps": [
                    {
                        "sort_order": 1,
                        "name": f"手动完成：{payload.get('name') or '录制操作'}",
                        "action": "wait",
                        "value": 1,
                        "take_screenshot": True,
                        "notes": "当前为录制占位步骤，可在详情页替换为采集到的真实事件。",
                    }
                ],
                "input_info": {},
                "assertions": [],
            }
            generated = {"warnings": ["未收到录制事件，已生成可编辑占位脚本。"]}
        scenario = self.create_scenario(feature_id, scenario_payload)
        return {"scenario": scenario, "generation": generated}

    def run_scenario(self, scenario_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        scenario = self._required(SCENARIO_TABLE, scenario_id, "App 场景不存在")
        data = scenario.get("data") if isinstance(scenario.get("data"), dict) else {}
        device_id = self._optional_int(payload.get("device_id")) or self._optional_int(data.get("device_id"))
        device = self.repository.get("app_devices", device_id) if device_id else None
        input_snapshot = self._merge_input_info(data.get("input_info"), payload.get("input_info"))
        steps = self._steps_for_execution(data.get("operation_steps"), input_snapshot)
        case = {
            "id": scenario_id,
            "name": scenario.get("name"),
            "project_id": scenario.get("project_id"),
            "source_id": data.get("page_id"),
            "description": scenario.get("description"),
            "status": scenario.get("status"),
            "steps": steps,
            "assertions": data.get("assertions") if isinstance(data.get("assertions"), list) else [],
            "data": {
                **data,
                "case_type": "APP",
                "entry_id": data.get("entry_id"),
                "record_video": payload.get("record_video") if payload.get("record_video") is not None else data.get("record_video", True),
                "start_from_current_screen": data.get("start_from_current_screen", True),
                "steps": steps,
                "input_info": input_snapshot,
            },
        }
        config: dict[str, Any] = {
            "device_id": device_id,
            "device": device or {},
            "record_video": payload.get("record_video") if payload.get("record_video") is not None else data.get("record_video", True),
        }
        if isinstance(payload.get("variables"), dict):
            config["variables"] = payload["variables"]
        return AppAgentExecutionService(self.repository).queue(
            scenario, device, case,
            {"project_id": scenario.get("project_id"), "mode": "remote_node", "config": config},
            payload.get("node_id"),
        )

    def list_runs(self, scenario_id: int, page: int = 1, page_size: int = 20) -> tuple[list[dict[str, Any]], int]:
        self._required(SCENARIO_TABLE, scenario_id, "App 场景不存在")
        return self.repository.list(RUN_TABLE, page=page, page_size=page_size, data_filters={"scenario_id": scenario_id})

    def get_run(self, run_id: int) -> dict[str, Any]:
        return self._required(RUN_TABLE, run_id, "App 场景执行记录不存在")

    def _scenario_payload_from_case_json(
        self,
        feature: dict[str, Any],
        case_json: dict[str, Any],
        payload: dict[str, Any],
        source_type: str,
    ) -> dict[str, Any]:
        steps, input_info = self._split_steps_and_input(case_json.get("steps", []))
        if not input_info and isinstance(case_json.get("input_info"), dict):
            input_info = case_json["input_info"]
        return {
            "name": case_json.get("name") or feature.get("name") or "App 场景",
            "description": case_json.get("description") or payload.get("prompt"),
            "status": "active",
            "source_type": source_type,
            "device_id": payload.get("device_id"),
            "entry_id": payload.get("entry_id") or case_json.get("entry_id"),
            "record_video": payload.get("record_video", case_json.get("record_video", True)),
            "start_from_current_screen": payload.get("start_from_current_screen", case_json.get("start_from_current_screen", True)),
            "operation_steps": steps,
            "input_info": input_info,
            "assertions": case_json.get("assertions") if isinstance(case_json.get("assertions"), list) else [],
            "generation_meta": payload.get("generation_meta") if isinstance(payload.get("generation_meta"), dict) else {},
            "knowledge_refs": case_json.get("knowledge_refs") if isinstance(case_json.get("knowledge_refs"), list) else [],
            "generation_notes": case_json.get("generation_notes"),
        }

    def _scenario_data(self, feature: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
        feature_data = feature.get("data") if isinstance(feature.get("data"), dict) else {}
        return {
            "feature_id": feature.get("id"),
            "feature_name": feature.get("name"),
            "source_type": values.get("source_type") or "manual",
            "device_id": self._optional_int(values.get("device_id")),
            "entry_id": self._optional_int(values.get("entry_id")),
            "platforms": feature_data.get("platforms") or ["Android", "iOS"],
            "device_form_factors": feature_data.get("device_form_factors") or ["phone", "tablet"],
            "record_video": bool(values.get("record_video", True)),
            "start_from_current_screen": bool(values.get("start_from_current_screen", True)),
            "operation_steps": values.get("operation_steps") if isinstance(values.get("operation_steps"), list) else [],
            "input_info": values.get("input_info") if isinstance(values.get("input_info"), dict) else {},
            "variables": values.get("variables") if isinstance(values.get("variables"), dict) else {},
            "assertions": values.get("assertions") if isinstance(values.get("assertions"), list) else [],
            "generation_meta": values.get("generation_meta") if isinstance(values.get("generation_meta"), dict) else {},
            "knowledge_refs": values.get("knowledge_refs") if isinstance(values.get("knowledge_refs"), list) else [],
            "generation_notes": values.get("generation_notes"),
        }

    def _generation_meta(self, generated: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        context = generated.get("context") if isinstance(generated.get("context"), dict) else {}
        knowledge = context.get("knowledge") if isinstance(context.get("knowledge"), list) else []
        validation = generated.get("validation") if isinstance(generated.get("validation"), dict) else {}
        warnings = generated.get("warnings") if isinstance(generated.get("warnings"), list) else []
        return {
            "source": "natural_language",
            "mode": generated.get("generation_mode") or "rule",
            "model_id": self._optional_int(payload.get("model_id")),
            "include_knowledge": bool(payload.get("include_knowledge", True)),
            "knowledge_ids": [item.get("id") for item in knowledge if isinstance(item, dict) and item.get("id")],
            "knowledge_keys": [item.get("knowledge_key") for item in knowledge if isinstance(item, dict) and item.get("knowledge_key")],
            "validation": validation,
            "warnings": warnings,
        }

    def _split_steps_and_input(self, raw_steps: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        steps: list[dict[str, Any]] = []
        input_info: dict[str, Any] = {}
        if not isinstance(raw_steps, list):
            return steps, input_info
        for index, raw_step in enumerate(raw_steps, start=1):
            if not isinstance(raw_step, dict):
                continue
            step = dict(raw_step)
            step.setdefault("sort_order", index)
            if str(step.get("action") or "").lower() in {"input", "fill", "send_keys", "type"}:
                key = str(step.get("input_key") or self._input_key(step, index))
                value = "" if step.get("value") is None else str(step.get("value"))
                step["input_key"] = key
                step["value"] = f"${{{key}}}"
                input_info.setdefault(
                    key,
                    {
                        "label": self._input_label(step, index),
                        "type": "password" if self._looks_sensitive(step) else "text",
                        "value": value,
                        "required": True,
                        "masked": self._looks_sensitive(step),
                    },
                )
            steps.append(step)
        return steps, input_info

    def _merge_input_info(self, base: Any, override: Any) -> dict[str, Any]:
        result = deepcopy(base) if isinstance(base, dict) else {}
        if not isinstance(override, dict):
            return result
        for key, value in override.items():
            if isinstance(result.get(key), dict):
                result[key] = {**result[key], "value": value}
            else:
                result[key] = {"label": key, "type": "text", "value": value, "required": False}
        return result

    def _steps_for_execution(self, raw_steps: Any, input_info: dict[str, Any]) -> list[dict[str, Any]]:
        steps = deepcopy(raw_steps) if isinstance(raw_steps, list) else []
        for step in steps:
            if not isinstance(step, dict):
                continue
            input_key = str(step.get("input_key") or "").strip()
            if input_key:
                step["value"] = self._input_value(input_info.get(input_key), step.get("value"))
        return [step for step in steps if isinstance(step, dict)]

    def _input_value(self, item: Any, fallback: Any) -> Any:
        if isinstance(item, dict):
            if item.get("value") not in (None, ""):
                return item.get("value")
            if item.get("default") not in (None, ""):
                return item.get("default")
        return fallback

    def _enrich_feature(self, feature: dict[str, Any], summary=None) -> dict[str, Any]:
        summary = summary if summary is not None else self.repository.app_feature_summaries([int(feature["id"])])[int(feature["id"])]
        scenario_total = summary["scenario_count"]
        data = dict(feature.get("data") if isinstance(feature.get("data"), dict) else {})
        last_run = data.get("last_run") if isinstance(data.get("last_run"), dict) else summary["last_run"]
        enriched = dict(feature)
        enriched["data"] = {**data, "scenario_count": scenario_total, "last_run": last_run}
        enriched["scenario_count"] = scenario_total
        enriched["last_run_status"] = (last_run or {}).get("status")
        enriched["last_run_at"] = (last_run or {}).get("updated_at") or (last_run or {}).get("created_at")
        return enriched

    def _enrich_scenario(self, scenario: dict[str, Any]) -> dict[str, Any]:
        data = dict(scenario.get("data") if isinstance(scenario.get("data"), dict) else {})
        steps = data.get("operation_steps") if isinstance(data.get("operation_steps"), list) else []
        input_info = data.get("input_info") if isinstance(data.get("input_info"), dict) else {}
        enriched = dict(scenario)
        enriched["data"] = data
        enriched["step_count"] = len(steps)
        enriched["input_count"] = len(input_info)
        enriched["source_type"] = data.get("source_type")
        last_run = data.get("last_run") if isinstance(data.get("last_run"), dict) else None
        enriched["last_run_status"] = (last_run or {}).get("status")
        enriched["last_video_url"] = (last_run or {}).get("video_url")
        return enriched

    def _update_last_run(self, scenario: dict[str, Any], run: dict[str, Any]) -> None:
        data = dict(scenario.get("data") if isinstance(scenario.get("data"), dict) else {})
        run_data = run.get("data") if isinstance(run.get("data"), dict) else {}
        data["last_run"] = {
            "id": run.get("id"),
            "status": run.get("status"),
            "created_at": run.get("created_at"),
            "updated_at": run.get("updated_at"),
            "video_url": run_data.get("video_url"),
            "screenshot_url": run_data.get("screenshot_url"),
            "duration_ms": run_data.get("duration_ms"),
            "error": run_data.get("error"),
        }
        self.repository.update(SCENARIO_TABLE, int(scenario["id"]), {"data": data})

    def _update_feature_last_run(self, feature: dict[str, Any], run: dict[str, Any]) -> None:
        data = dict(feature.get("data") if isinstance(feature.get("data"), dict) else {})
        run_data = run.get("data") if isinstance(run.get("data"), dict) else {}
        data["last_run"] = {
            "id": run.get("id"),
            "scenario_id": run_data.get("scenario_id"),
            "status": run.get("status"),
            "created_at": run.get("created_at"),
            "updated_at": run.get("updated_at"),
            "video_url": run_data.get("video_url"),
            "screenshot_url": run_data.get("screenshot_url"),
        }
        self.repository.update(FEATURE_TABLE, int(feature["id"]), {"data": data})

    def _archive_failure_knowledge(
        self,
        scenario: dict[str, Any],
        run: dict[str, Any],
        feature: dict[str, Any] | None,
        device_id: int | None,
    ) -> None:
        try:
            run_data = run.get("data") if isinstance(run.get("data"), dict) else {}
            error = str(run_data.get("error") or run.get("description") or "").strip()
            if not error:
                return
            failed_step = self._failed_step(run_data.get("step_timeline"))
            signature = self._failure_signature(error, failed_step)
            if self._failure_knowledge_exists(self._optional_int(run.get("project_id")), signature):
                return
            scenario_data = scenario.get("data") if isinstance(scenario.get("data"), dict) else {}
            self.repository.create(
                "project_knowledge",
                {
                    "name": self._knowledge_name(scenario.get("name")),
                    "project_id": run.get("project_id"),
                    "description": "App 场景执行失败后自动归档，可作为后续自然语言生成和脚本修复参考。",
                    "status": "active",
                    "data": {
                        "domain": "APP",
                        "kind": "app_failure_lesson",
                        "category": "failure",
                        "priority": "P1",
                        "feature_id": scenario_data.get("feature_id"),
                        "feature_name": scenario_data.get("feature_name") or (feature or {}).get("name"),
                        "scenario_id": scenario.get("id"),
                        "scenario_name": scenario.get("name"),
                        "run_id": run.get("id"),
                        "device_id": device_id,
                        "trigger_signature": signature,
                        "content": self._failure_content(error, failed_step),
                        "repair_strategy": self._failure_repair_strategy(error, failed_step),
                        "template_json": {
                            "failed_step": failed_step,
                            "error": error,
                            "screenshot_url": run_data.get("screenshot_url"),
                            "video_url": run_data.get("video_url"),
                        },
                    },
                },
            )
        except Exception:
            return

    def _failure_knowledge_exists(self, project_id: int | None, signature: str) -> bool:
        if project_id is None:
            return False
        rows, _ = self.repository.list(
            "project_knowledge",
            project_id=project_id,
            page=1,
            page_size=1000,
            data_filters={"domain": "APP", "kind": "app_failure_lesson"},
        )
        for row in rows:
            data = row.get("data") if isinstance(row.get("data"), dict) else {}
            if data.get("trigger_signature") == signature:
                return True
        return False

    def _failed_step(self, timeline: Any) -> dict[str, Any]:
        if not isinstance(timeline, list):
            return {}
        for step in timeline:
            if isinstance(step, dict) and str(step.get("status") or "") == "failed":
                return step
        return {}

    def _failure_signature(self, error: str, failed_step: dict[str, Any]) -> str:
        raw = "|".join(
            str(value or "")
            for value in (
                failed_step.get("action"),
                failed_step.get("name"),
                error,
            )
        ).lower()
        raw = re.sub(r"\d{4,}", "#", raw)
        raw = re.sub(r"\s+", " ", raw).strip()
        return raw[:180] or "unknown_app_failure"

    def _knowledge_name(self, scenario_name: Any) -> str:
        return f"失败经验：{scenario_name or 'App 场景'!s}"[:128]

    def _failure_content(self, error: str, failed_step: dict[str, Any]) -> str:
        if failed_step:
            return f"执行步骤「{failed_step.get('name') or '-'}」失败：{error}"
        return f"执行失败：{error}"

    def _failure_repair_strategy(self, error: str, failed_step: dict[str, Any]) -> str:
        action = str(failed_step.get("action") or "").lower()
        if "not found" in error.lower() or "找不到" in error:
            return "下次生成脚本时优先补充稳定 locator，并在该步骤前增加页面加载等待或弹窗处理。"
        if action == "input":
            return "下次生成脚本时确认输入框定位、键盘状态和输入信息变量，不要把输入值写死在步骤名称中。"
        return "下次生成脚本时复用失败步骤上下文，补充等待、断言或备用定位策略。"

    def _input_key(self, step: dict[str, Any], index: int) -> str:
        raw = str(step.get("locator") or step.get("name") or f"input_{index}").lower()
        raw = re.sub(r"[^a-z0-9_\u4e00-\u9fff]+", "_", raw).strip("_")
        if not raw or re.search(r"[\u4e00-\u9fff]", raw):
            raw = f"input_{index}"
        return raw[:48]

    def _input_label(self, step: dict[str, Any], index: int) -> str:
        return str(step.get("locator") or step.get("name") or f"输入 {index}")[:64]

    def _looks_sensitive(self, step: dict[str, Any]) -> bool:
        text = " ".join(str(step.get(key) or "").lower() for key in ("name", "locator", "input_key", "value"))
        return any(marker in text for marker in ("password", "passwd", "pwd", "密码", "口令"))

    def _required(self, table: str, item_id: int | None, message: str) -> dict[str, Any]:
        if item_id is None:
            raise ResourceNotFoundError(message)
        item = self.repository.get(table, int(item_id))
        if not item:
            raise ResourceNotFoundError(message)
        return item

    def _positive_int(self, value: Any, message: str) -> int:
        parsed = self._optional_int(value)
        if parsed is None or parsed <= 0:
            raise BusinessRuleError(message)
        return parsed

    def _optional_int(self, value: Any) -> int | None:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None
