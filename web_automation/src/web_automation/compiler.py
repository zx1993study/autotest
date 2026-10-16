from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from web_automation.models import MANIFEST_VERSION, RESULT_VERSION, CompiledCase, ExecutionPlan, RunConfig
from web_automation.dynamic_values import DynamicValueError, prepare_dynamic_execution


class ExecutionPlanCompiler:
    """Compile mutable platform records into an immutable execution plan."""

    def compile(self, payload: dict[str, Any]) -> ExecutionPlan:
        manifest_version = str(payload.get("manifest_version") or MANIFEST_VERSION)
        if manifest_version != MANIFEST_VERSION:
            raise ValueError(
                f"Unsupported manifest version {manifest_version}; runtime supports {MANIFEST_VERSION}"
            )
        execution = payload.get("execution") if isinstance(payload.get("execution"), dict) else {}
        context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
        phone_reservations: set[str] = set()
        cases = tuple(
            self._compile_case(case, context, {**execution, "_dynamic_phone_reservations": phone_reservations})
            for case in payload.get("cases", [])
            if isinstance(case, dict)
        )
        return ExecutionPlan(
            manifest_version=manifest_version,
            result_version=RESULT_VERSION,
            config=RunConfig.from_execution(execution),
            cases=cases,
            ai_model=dict(context.get("ai_model") if isinstance(context.get("ai_model"), dict) else {}),
            metadata=dict(payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}),
        )

    def compile_case(self, case: dict[str, Any], context: dict[str, Any], execution: dict[str, Any] | None = None) -> CompiledCase:
        return self._compile_case(case, context, execution or {})

    def _compile_case(self, case: dict[str, Any], context: dict[str, Any], execution: dict[str, Any]) -> CompiledCase:
        data = dict(case.get('data') or {})
        secure = data.pop('runtime_inputs', {})
        if data.get('secret_inputs') and set(data['secret_inputs']) - secure.keys():
            raise ValueError('Protected inputs were not supplied by the authorized task runtime')
        # Credentials are literals, even if their text resembles a dynamic template.
        data['variables'] = {**(data.get('variables') or {}), **{k:v.replace('{{', r'\{{') for k,v in secure.items()}}
        case = {**case, 'data':data}
        elements = [item for item in context.get("elements", []) if isinstance(item, dict)]
        steps = case.get("steps") if isinstance(case.get("steps"), list) else []
        try:
            resolved_case, _, dynamic = prepare_dynamic_execution(case, execution)
            expanded = [
                dynamic.resolve(self._expand_step(case, step, index, elements), f"$.steps[{index}]")
                for index, step in enumerate(steps)
                if isinstance(step, dict)
            ]
            target_url = dynamic.resolve(self._target_url(resolved_case, context), "$.url")
            resolved_case["_dynamic_values"] = dynamic.snapshot()
            case = resolved_case
        except DynamicValueError as exc:
            case = {**case, "_dynamic_error": str(exc)}
            expanded = []
            target_url = self._target_url(case, context)
        expanded.sort(key=lambda item: (self._int(item.get("sort_order"), 0), self._int(item.get("element_id"), 0)))
        return CompiledCase(
            id=case.get("id"),
            name=str(case.get("name") or case.get("id") or "Web case"),
            project_id=case.get("project_id"),
            source_id=case.get("source_id"),
            target_url=target_url,
            steps=tuple(expanded),
            assertions=tuple(item for item in case.get("assertions", []) if isinstance(item, dict)),
            auth_context=self._auth_context(case, context),
            raw=case,
        )

    def _expand_step(
        self,
        case: dict[str, Any],
        step: dict[str, Any],
        index: int,
        elements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        data = step.get("data") if isinstance(step.get("data"), dict) else {}
        element = self._match_element(case, step, elements)
        element_data = element.get("data") if element and isinstance(element.get("data"), dict) else {}
        merged = {**element_data, **data, **{key: value for key, value in step.items() if key != "data"}}
        if element:
            merged["element_id"] = element.get("id")
        merged["name"] = str(
            step.get("元素名称")
            or step.get("name")
            or (element or {}).get("name")
            or merged.get("name")
            or ""
        )
        merged["action"] = self._step_action(merged)
        merged["value"] = self._step_value(merged)
        merged["skip"] = self._truthy(step.get("是否跳过", merged.get("skip")))
        merged["take_screenshot"] = self._truthy(step.get("是否截图", merged.get("take_screenshot")))
        merged["sort_order"] = self._step_order(step, data, element_data, index)
        return merged

    def _match_element(
        self,
        case: dict[str, Any],
        step: dict[str, Any],
        elements: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        element_id = self._int_or_none(step.get("element_id"))
        if element_id is not None:
            for element in elements:
                if self._int_or_none(element.get("id")) == element_id:
                    return element
        page_id = self._int_or_none(case.get("source_id"))
        name = str(step.get("元素名称") or step.get("name") or "").strip()
        if not name:
            return None
        for element in elements:
            data = element.get("data") if isinstance(element.get("data"), dict) else {}
            if page_id is not None and self._int_or_none(data.get("page_id")) != page_id:
                continue
            candidates = [element.get("name"), data.get("name"), data.get("element_name"), data.get("label")]
            if name in {str(item).strip() for item in candidates if item not in (None, "")}:
                return element
        return None

    def _target_url(self, case: dict[str, Any], context: dict[str, Any]) -> str:
        data = case.get("data") if isinstance(case.get("data"), dict) else {}
        request = data.get("request") if isinstance(data.get("request"), dict) else {}
        for value in (data.get("url"), request.get("url")):
            if value:
                return str(value)
        page = self._record_by_id(context.get("pages"), case.get("source_id"))
        page_data = page.get("data") if isinstance(page.get("data"), dict) else {}
        page_url = str(page_data.get("url") or page_data.get("route") or "").strip()
        if page_url.startswith(("http://", "https://")):
            return page_url
        project = self._record_by_id(context.get("projects"), case.get("project_id"))
        project_data = project.get("data") if isinstance(project.get("data"), dict) else {}
        base_url = str(project_data.get("base_url") or project_data.get("project_url") or project_data.get("url") or "").strip()
        if not page_url:
            return base_url
        if not base_url:
            return page_url
        return urljoin(f"{base_url.rstrip('/')}/", page_url.lstrip("/"))

    def _auth_context(self, case: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        by_case = context.get("auth_context_by_case") if isinstance(context.get("auth_context_by_case"), dict) else {}
        case_context = by_case.get(str(case.get("id")))
        if isinstance(case_context, dict):
            return dict(case_context)
        default_context = context.get("auth_context")
        if isinstance(default_context, dict):
            return dict(default_context)
        cookies = context.get("auth_cookies") if isinstance(context.get("auth_cookies"), list) else []
        return {"cookies": cookies, "storage_state": {"cookies": cookies, "origins": []}} if cookies else {}

    def _record_by_id(self, value: Any, record_id: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            item = value.get(str(record_id)) or value.get(record_id)
            return item if isinstance(item, dict) else {}
        if isinstance(value, list):
            target = self._int_or_none(record_id)
            for item in value:
                if isinstance(item, dict) and self._int_or_none(item.get("id")) == target:
                    return item
        return {}

    def _step_action(self, step: dict[str, Any]) -> str:
        action = str(step.get("交互类型") or step.get("action") or "").lower().strip()
        if action:
            return action
        element_type = str(step.get("element_type") or step.get("type") or "").lower()
        if element_type in {"input", "textarea", "text"}:
            return "fill"
        if element_type in {"select", "dropdown", "tree_select", "multi_select"}:
            return "select"
        if element_type in {"checkbox", "radio"}:
            return "check"
        return "click"

    def _step_value(self, step: dict[str, Any]) -> Any:
        for key in ("元素值", "value", "default_value", "example"):
            if key in step:
                return step[key]
        return None

    def _step_order(
        self,
        step: dict[str, Any],
        data: dict[str, Any],
        element_data: dict[str, Any],
        index: int,
    ) -> int:
        for source in (step, data, element_data):
            for key in ("步骤标识", "sort_order", "order", "index"):
                value = self._int_or_none(source.get(key))
                if value is not None:
                    return value
        return index + 1

    def _truthy(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "是", "截图", "跳过"}

    def _int(self, value: Any, default: int) -> int:
        parsed = self._int_or_none(value)
        return default if parsed is None else parsed

    def _int_or_none(self, value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
