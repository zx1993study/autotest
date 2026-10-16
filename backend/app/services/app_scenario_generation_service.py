from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.repositories.interfaces import ResourceRepository
from app.services.ai_generation_service import AiGenerationService


SUPPORTED_ACTIONS = {
    "tap",
    "input",
    "clear",
    "select",
    "assert",
    "assert_text",
    "assert_screen_contains",
    "swipe",
    "back",
    "wait",
    "press_key",
    "hide_keyboard",
    "switch_context",
    "launch_app",
    "terminate_app",
}


class AppScenarioGenerationService:
    """Generate reusable App automation scenario JSON for feature testing."""

    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def generate_from_text(self, payload: dict[str, Any]) -> dict[str, Any]:
        project_id = self._positive_int(payload.get("project_id"), "project_id")
        prompt = str(payload.get("prompt") or "").strip()
        if not prompt:
            raise BusinessRuleError("请输入 App 场景描述")
        project = self._required("projects", project_id, "项目不存在")
        context = self._context(project_id, payload)
        warnings: list[str] = []
        generated = None
        generation_mode = "rule"
        if payload.get("model_id") and not payload.get("dry_run"):
            try:
                generated = self._call_ai(payload, project, context)
                generation_mode = "ai"
            except HTTPException:
                if not payload.get("allow_rule_fallback", True):
                    raise
                warnings.append("AI 模型暂不可用，已使用规则模板生成可编辑草稿")
            except Exception as exc:  # noqa: BLE001 - generation can safely fall back to rule mode.
                if not payload.get("allow_rule_fallback", True):
                    raise
                warnings.append(f"AI 生成失败，已使用规则模板生成可编辑草稿：{exc}")
        if not generated:
            generated = self._rule_based_case(payload, project, context)
            generation_mode = "rule"
        case_json = self._normalize_case_json(generated, payload, prompt)
        validation = self.validate_case_json(case_json)
        warnings.extend(validation["warnings"])
        result: dict[str, Any] = {
            "dry_run": bool(payload.get("dry_run")),
            "generation_mode": generation_mode,
            "case_json": case_json,
            "validation": validation,
            "warnings": warnings,
            "context": context,
        }
        return result

    def generate_from_events(self, payload: dict[str, Any]) -> dict[str, Any]:
        project_id = self._positive_int(payload.get("project_id"), "project_id")
        self._required("projects", project_id, "项目不存在")
        events = [event for event in payload.get("events", []) if isinstance(event, dict)]
        if not events:
            raise BusinessRuleError("录制事件不能为空")
        steps = [step for step in (self._event_to_step(event, index) for index, event in enumerate(events, start=1)) if step]
        case_json = self._normalize_case_json(
            {
                "name": payload.get("name") or "录制生成 App 场景",
                "description": "由设备实时录制事件生成",
                "source_type": "event_trace",
                "steps": steps,
            },
            payload,
            str(payload.get("name") or "录制生成 App 场景"),
        )
        validation = self.validate_case_json(case_json)
        result: dict[str, Any] = {"case_json": case_json, "validation": validation, "warnings": validation["warnings"]}
        return result

    def validate_case_json(self, case_json: dict[str, Any]) -> dict[str, Any]:
        steps = case_json.get("steps") if isinstance(case_json.get("steps"), list) else []
        warnings: list[str] = []
        coordinate_steps = 0
        locator_steps = 0
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                warnings.append(f"第 {index} 步不是对象，执行时会被忽略")
                continue
            action = str(step.get("action") or "").strip().lower()
            if action not in SUPPORTED_ACTIONS:
                warnings.append(f"第 {index} 步动作 {action or '-'} 暂不支持")
            has_locator = bool(step.get("locator") or step.get("text") or step.get("resource_id") or step.get("xpath"))
            has_coordinate = any(step.get(key) not in (None, "") for key in ("x", "y", "x_pct", "y_pct"))
            if has_locator:
                locator_steps += 1
            elif has_coordinate:
                coordinate_steps += 1
            elif action not in {"back", "wait", "hide_keyboard", "launch_app", "terminate_app", "switch_context"}:
                warnings.append(f"第 {index} 步缺少定位器或坐标兜底")
        score = 100
        if steps:
            score -= int((coordinate_steps / len(steps)) * 25)
            score -= min(30, len(warnings) * 8)
        else:
            score = 0
            warnings.append("没有生成可执行步骤")
        assertions = case_json.get("assertions") if isinstance(case_json.get("assertions"), list) else []
        if steps and not assertions:
            warnings.append("缺少结果断言，建议补充页面文本或状态校验")
            score -= 8
        return {
            "step_count": len([step for step in steps if isinstance(step, dict)]),
            "locator_steps": locator_steps,
            "coordinate_steps": coordinate_steps,
            "confidence_score": max(0, min(100, score)),
            "warnings": warnings,
        }

    def _call_ai(self, payload: dict[str, Any], project: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        prompt = {
            "system": (
                "你是移动端自动化测试专家。请只返回 JSON 对象，不要 Markdown。"
                "目标是把用户自然语言转换为 Appium 可执行的 APP 测试场景 DSL。"
                "不要要求安装包，默认基于当前已安装 App 或当前手机屏幕执行。"
                "必须优先采用稳定定位器，只有在没有可靠定位器时才使用坐标兜底。"
            ),
            "user": json.dumps(
                {
                    "project": {"id": project.get("id"), "name": project.get("name")},
                    "user_prompt": payload.get("prompt"),
                    "requirements": {
                        "schema": {
                            "name": "string",
                            "description": "string",
                            "source_type": "natural_language",
                            "steps": [
                                {
                                    "name": "string",
                                    "action": "tap/input/assert_text/swipe/back/wait/launch_app/terminate_app/hide_keyboard",
                                    "locator_type": "text/accessibility_id/resource_id/xpath/ios_predicate/android_uiautomator",
                                    "locator": "string",
                                    "value": "optional string",
                                    "x_pct": "optional number 0-1",
                                    "y_pct": "optional number 0-1",
                                    "take_screenshot": True,
                                }
                            ],
                            "input_info": {
                                "field_key": {
                                    "label": "string",
                                    "type": "text/password/number",
                                    "value": "string",
                                    "required": True,
                                }
                            },
                            "assertions": [{"type": "text_contains", "expected": "string", "step": "string"}],
                            "knowledge_refs": ["knowledge_key or id"],
                            "generation_notes": "string",
                        },
                        "supported_actions": sorted(SUPPORTED_ACTIONS),
                        "prefer_locator_over_coordinates": True,
                        "avoid": [
                            "不要把敏感信息硬编码在步骤名称里",
                            "不要生成依赖安装包上传的步骤",
                            "不要在可以使用文本、accessibility_id、resource_id 时直接使用绝对坐标",
                            "不要忽略 context.knowledge 中的失败经验和定位策略",
                        ],
                        "input_handling": "输入动作可以先给 value，系统会把 value 自动转成可编辑输入信息。",
                    },
                    "context": context,
                },
                ensure_ascii=False,
            ),
        }
        result = AiGenerationService(self.repository)._call_model(self._optional_int(payload.get("model_id")), prompt)
        if isinstance(result.get("case"), dict):
            return result["case"]
        cases = result.get("cases")
        if isinstance(cases, list) and cases and isinstance(cases[0], dict):
            return cases[0]
        return result

    def _rule_based_case(self, payload: dict[str, Any], project: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        prompt = str(payload.get("prompt") or "").strip()
        steps = [step for step in (self._sentence_to_step(sentence, index) for index, sentence in enumerate(self._sentences(prompt), start=1)) if step]
        if not steps:
            steps = [
                {
                    "name": "人工确认操作",
                    "action": "wait",
                    "value": 1,
                    "confidence": "low",
                    "notes": "未能从描述中提取明确动作，请编辑步骤后再执行",
                }
            ]
        return {
            "name": self._scenario_name(prompt),
            "description": prompt,
            "source_type": "natural_language",
            "project_name": project.get("name"),
            "steps": steps,
            "assertions": self._assertions_from_steps(steps),
            "context_summary": {
                "entry_count": len(context.get("entries", [])),
                "feature_count": len(context.get("features", [])),
                "scenario_count": len(context.get("scenarios", [])),
                "knowledge_count": len(context.get("knowledge", [])),
            },
        }

    def _normalize_case_json(self, generated: dict[str, Any], payload: dict[str, Any], prompt: str) -> dict[str, Any]:
        steps = generated.get("steps")
        if not isinstance(steps, list):
            request = generated.get("request") if isinstance(generated.get("request"), dict) else {}
            steps = request.get("steps") if isinstance(request.get("steps"), list) else []
        normalized_steps = [self._normalize_step(step, index) for index, step in enumerate(steps, start=1) if isinstance(step, dict)]
        entry_id = self._optional_int(payload.get("entry_id"))
        feature_id = self._optional_int(payload.get("feature_id"))
        case_json: dict[str, Any] = {
            "case_type": "APP",
            "scenario_version": 1,
            "source_type": generated.get("source_type") or "natural_language",
            "user_prompt": prompt,
            "name": str(generated.get("name") or self._scenario_name(prompt))[:128],
            "description": generated.get("description") or prompt,
            "entry_id": entry_id,
            "feature_id": feature_id,
            "target_platforms": self._string_list(payload.get("target_platforms")) or ["Android", "iOS"],
            "target_device_form_factors": self._string_list(payload.get("target_device_form_factors")) or ["phone", "tablet"],
            "start_from_current_screen": bool(payload.get("start_from_current_screen", True)),
            "record_video": bool(payload.get("record_video", True)),
            "steps": normalized_steps,
            "input_info": generated.get("input_info") if isinstance(generated.get("input_info"), dict) else {},
            "assertions": generated.get("assertions") if isinstance(generated.get("assertions"), list) else self._assertions_from_steps(normalized_steps),
            "knowledge_refs": self._string_list(generated.get("knowledge_refs")),
            "generation_notes": str(generated.get("generation_notes") or "").strip(),
        }
        return {key: value for key, value in case_json.items() if value is not None}

    def _normalize_step(self, step: dict[str, Any], index: int) -> dict[str, Any]:
        action = str(step.get("action") or step.get("interaction") or "tap").strip().lower()
        if action == "click":
            action = "tap"
        if action == "type":
            action = "input"
        if action == "assert":
            action = "assert_text"
        normalized = dict(step)
        normalized["sort_order"] = self._optional_int(step.get("sort_order") or step.get("order")) or index
        normalized["name"] = str(step.get("name") or step.get("step_name") or f"步骤 {index}")
        normalized["action"] = action
        normalized["take_screenshot"] = bool(step.get("take_screenshot", action in {"tap", "input", "assert_text"}))
        if not normalized.get("locator") and normalized.get("text"):
            normalized["locator_type"] = normalized.get("locator_type") or "text"
            normalized["locator"] = normalized.get("text")
        normalized.setdefault("confidence", "medium" if normalized.get("locator") else "low")
        return normalized

    def _sentence_to_step(self, sentence: str, index: int) -> dict[str, Any] | None:
        text = sentence.strip(" ，。；;,.")
        if not text:
            return None
        if re.search(r"返回|后退", text):
            return {"name": text, "action": "back", "sort_order": index, "take_screenshot": True, "confidence": "high"}
        if re.search(r"隐藏键盘|收起键盘", text):
            return {"name": text, "action": "hide_keyboard", "sort_order": index, "take_screenshot": True, "confidence": "high"}
        wait_match = re.search(r"等待\s*(\d+(?:\.\d+)?)\s*(秒|s|毫秒|ms)?", text, re.I)
        if wait_match:
            value = float(wait_match.group(1))
            if wait_match.group(2) in {"毫秒", "ms"}:
                value = value / 1000
            return {"name": text, "action": "wait", "value": value, "sort_order": index, "confidence": "high"}
        input_match = re.search(r"(?:在|向)?(.{0,30}?)(?:输入|填写|填入)(.+)", text)
        if input_match:
            target = self._clean_locator_text(input_match.group(1)) or "输入框"
            value = self._strip_quotes(input_match.group(2))
            return {
                "name": text,
                "action": "input",
                "locator_type": "text",
                "locator": target,
                "value": value,
                "sort_order": index,
                "take_screenshot": True,
                "confidence": "medium",
            }
        assert_match = re.search(r"(?:校验|验证|检查|看到|显示|应显示|应该显示)(.+)", text)
        if assert_match:
            locator = self._clean_locator_text(assert_match.group(1))
            return {
                "name": text,
                "action": "assert_text",
                "locator_type": "text",
                "locator": locator,
                "value": locator,
                "sort_order": index,
                "take_screenshot": True,
                "confidence": "medium",
            }
        if re.search(r"上滑|下滑|左滑|右滑|滑动|滚动", text):
            direction = "up"
            if "下滑" in text:
                direction = "down"
            elif "左滑" in text:
                direction = "left"
            elif "右滑" in text:
                direction = "right"
            return {"name": text, "action": "swipe", "direction": direction, "sort_order": index, "take_screenshot": True, "confidence": "high"}
        tap_match = re.search(r"(?:点击|点按|点|进入|选择|打开)(.+)", text)
        if tap_match:
            locator = self._clean_locator_text(tap_match.group(1))
            action = "select" if "选择" in text else "tap"
            return {
                "name": text,
                "action": action,
                "locator_type": "text",
                "locator": locator,
                "sort_order": index,
                "take_screenshot": True,
                "confidence": "medium",
            }
        return {"name": text, "action": "tap", "locator_type": "text", "locator": text, "sort_order": index, "take_screenshot": True, "confidence": "low"}

    def _event_to_step(self, event: dict[str, Any], index: int) -> dict[str, Any] | None:
        action = str(event.get("action") or event.get("type") or "").strip().lower()
        if action in {"click", "tap", "pointerdown"}:
            return {
                "name": str(event.get("name") or f"点击 {index}"),
                "action": "tap",
                "x_pct": event.get("x_pct"),
                "y_pct": event.get("y_pct"),
                "x": event.get("x"),
                "y": event.get("y"),
                "locator_type": event.get("locator_type"),
                "locator": event.get("locator"),
                "sort_order": index,
                "take_screenshot": True,
                "confidence": "high" if event.get("locator") else "low",
                "evidence": self._event_evidence(event),
            }
        if action in {"input", "type", "send_keys"}:
            return {
                "name": str(event.get("name") or f"输入 {index}"),
                "action": "input",
                "locator_type": event.get("locator_type") or "text",
                "locator": event.get("locator") or event.get("target_text"),
                "value": event.get("value") or event.get("text"),
                "sort_order": index,
                "take_screenshot": True,
                "confidence": "medium",
                "evidence": self._event_evidence(event),
            }
        if action in {"swipe", "scroll"}:
            return {
                "name": str(event.get("name") or f"滑动 {index}"),
                "action": "swipe",
                "direction": event.get("direction") or "up",
                "start_x": event.get("start_x"),
                "start_y": event.get("start_y"),
                "end_x": event.get("end_x"),
                "end_y": event.get("end_y"),
                "sort_order": index,
                "take_screenshot": True,
                "confidence": "high",
                "evidence": self._event_evidence(event),
            }
        if action in {"back", "wait", "hide_keyboard"}:
            return {"name": str(event.get("name") or action), "action": action, "value": event.get("value"), "sort_order": index, "confidence": "high"}
        return None

    def _context(self, project_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "entries": self._compact_rows("app_entries", project_id, ["entry_type", "platform", "bundle_id", "package_name", "activity"], 30),
            "features": self._compact_rows("app_features", project_id, ["platforms", "device_form_factors", "default_entry_id", "default_device_id"], 80),
            "scenarios": self._compact_rows("app_feature_scenarios", project_id, ["feature_id", "source_type", "device_id", "entry_id"], 120),
            "devices": self._compact_rows("app_devices", project_id, ["platform", "device_form_factor", "udid", "wda_url", "connection_status"], 50),
            "knowledge": self._app_knowledge(project_id, payload) if payload.get("include_knowledge", True) else [],
            "selected_entry_id": self._optional_int(payload.get("entry_id")),
            "selected_feature_id": self._optional_int(payload.get("feature_id")),
            "selected_device_id": self._optional_int(payload.get("device_id")),
        }

    def _compact_rows(self, table: str, project_id: int, keys: list[str], limit: int) -> list[dict[str, Any]]:
        rows, _ = self.repository.list(table, project_id=project_id, page=1, page_size=limit)
        result: list[dict[str, Any]] = []
        for row in rows:
            data = row.get("data") if isinstance(row.get("data"), dict) else {}
            compact = {"id": row.get("id"), "name": row.get("name")}
            for key in keys:
                if data.get(key) not in (None, ""):
                    compact[key] = data[key]
            result.append(compact)
        return result

    def _app_knowledge(self, project_id: int, payload: dict[str, Any]) -> list[dict[str, Any]]:
        rows, _ = self.repository.list(
            "project_knowledge",
            project_id=project_id,
            page=1,
            page_size=1000,
            data_filters={"domain": "APP"},
        )
        selected_ids = {item for item in (self._optional_int(value) for value in payload.get("knowledge_ids") or []) if item}
        scored: list[tuple[int, dict[str, Any]]] = []
        for row in rows:
            if selected_ids and row.get("id") not in selected_ids:
                continue
            if str(row.get("status") or "active") not in {"active", "enabled", "draft"}:
                continue
            data = row.get("data") if isinstance(row.get("data"), dict) else {}
            if str(data.get("domain") or "").upper() != "APP":
                continue
            compact = self._compact_knowledge(row, data)
            scored.append((self._knowledge_score(compact, payload), compact))
        scored.sort(key=lambda item: (-item[0], str(item[1].get("priority") or "P3"), int(item[1].get("id") or 0)))
        return [item for score, item in scored if score > 0 or not selected_ids][:20]

    def _compact_knowledge(self, row: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
        keys = (
            "knowledge_key",
            "kind",
            "category",
            "priority",
            "platform",
            "feature_id",
            "device_id",
            "trigger_signature",
            "content",
            "repair_strategy",
            "locator_strategy",
            "template_json",
            "tags",
        )
        compact: dict[str, Any] = {"id": row.get("id"), "name": row.get("name")}
        for key in keys:
            if data.get(key) not in (None, "", []):
                compact[key] = data[key]
        return compact

    def _knowledge_score(self, item: dict[str, Any], payload: dict[str, Any]) -> int:
        score = 1
        feature_id = self._optional_int(payload.get("feature_id"))
        device_id = self._optional_int(payload.get("device_id"))
        if feature_id and self._optional_int(item.get("feature_id")) == feature_id:
            score += 8
        if device_id and self._optional_int(item.get("device_id")) == device_id:
            score += 6
        prompt = str(payload.get("prompt") or "").lower()
        haystack = " ".join(str(item.get(key) or "").lower() for key in ("name", "knowledge_key", "category", "content", "trigger_signature"))
        for token in self._knowledge_tokens(prompt):
            if token and token in haystack:
                score += 2
        priority = str(item.get("priority") or "P3").upper()
        score += {"P0": 5, "P1": 4, "P2": 3, "P3": 1}.get(priority, 1)
        if str(item.get("kind") or "").lower() in {"app_failure_lesson", "failure_lesson", "repair_rule"}:
            score += 2
        return score

    def _knowledge_tokens(self, value: str) -> list[str]:
        chinese = re.findall(r"[\u4e00-\u9fff]{2,}", value)
        words = re.findall(r"[a-z0-9_]{3,}", value)
        return (chinese + words)[:30]

    def _sentences(self, prompt: str) -> list[str]:
        normalized = re.sub(r"\s*(然后|再|并且|且)\s*", "。", prompt)
        return [item.strip() for item in re.split(r"[。；;\n]+", normalized) if item.strip()]

    def _assertions_from_steps(self, steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        assertions = []
        for step in steps:
            if step.get("action") in {"assert", "assert_text", "assert_screen_contains"}:
                assertions.append({"type": "text_contains", "expected": step.get("value") or step.get("locator"), "step": step.get("name")})
        return assertions

    def _scenario_name(self, prompt: str) -> str:
        clean = re.sub(r"\s+", "", prompt)
        return (clean[:28] or "App 场景") + ("..." if len(clean) > 28 else "")

    def _clean_locator_text(self, value: Any) -> str:
        text = self._strip_quotes(str(value or ""))
        text = re.sub(r"^(按钮|页面|菜单|入口|选项|字段|文本|为|到|至|上|中|里|的)+", "", text).strip()
        return text[:80] or "目标元素"

    def _strip_quotes(self, value: Any) -> str:
        return str(value or "").strip().strip(" “”，,。；;：:\"'")

    def _event_evidence(self, event: dict[str, Any]) -> dict[str, Any]:
        keys = ("timestamp_ms", "before_screenshot", "after_screenshot", "page_source_file", "ocr_text", "device_id")
        return {key: event[key] for key in keys if event.get(key) not in (None, "")}

    def _required(self, table: str, item_id: int, message: str) -> dict[str, Any]:
        item = self.repository.get(table, item_id)
        if not item:
            raise ResourceNotFoundError(message)
        return item

    def _positive_int(self, value: Any, name: str) -> int:
        parsed = self._optional_int(value)
        if parsed is None or parsed <= 0:
            raise BusinessRuleError(f"{name} 必须是正整数")
        return parsed

    def _optional_int(self, value: Any) -> int | None:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item or "").strip()]
