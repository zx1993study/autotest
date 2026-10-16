"""Build Web test-case payloads from page and element metadata."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.test_strategy_utils import (
    case_json,
    category_label,
    knowledge_key,
    knowledge_keys,
    strategy_category,
    with_strategy_meta,
)


class WebCaseTemplateBuilder:
    """Apply project knowledge to normalized Web page element steps."""

    def build(
        self,
        case_type: str,
        asset: dict[str, Any],
        elements: list[dict[str, Any]],
        strategy: str,
        strategies: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return a normal flow plus knowledge-derived Web cases."""

        steps = [self._element_step(item) for item in elements]
        normal = case_json(
            case_type,
            f"[正常流程] {asset['name']}",
            "normal",
            {"steps": steps},
            0,
        )
        normal["strategy_ids"] = [
            item["id"]
            for item in strategies
            if strategy_category(item) == "normal"
        ]
        normal["knowledge_keys"] = knowledge_keys(strategies, "normal")
        cases = [normal]
        if strategies:
            for item in strategies:
                category = strategy_category(item)
                if category != "normal":
                    cases.extend(
                        self._strategy_cases(
                            case_type,
                            asset,
                            steps,
                            item,
                            category,
                        )
                    )
            return cases
        if strategy in {"basic", "full"}:
            cases.extend(self._required_fallback_cases(case_type, asset, elements, steps))
        return cases

    def _element_step(self, element: dict[str, Any]) -> dict[str, Any]:
        data = element.get("data", {})
        element_type = str(data.get("element_type") or data.get("type") or "").lower()
        action = data.get("action") or self._action_for_type(element_type)
        return {
            "element_id": element["id"],
            "name": element["name"],
            "action": action,
            "value": self._default_value(element, action),
            "locator": data.get("locator"),
            "locator_type": data.get("locator_type"),
            "locator_method": data.get("locator_method") or data.get("locator_type"),
            "locator_args": data.get("locator_args"),
            "role": data.get("role"),
            "role_name": data.get("role_name"),
            "resource_id": data.get("resource_id"),
            "css": data.get("css"),
            "text": data.get("text"),
            "content_desc": data.get("content_desc"),
            "xpath": data.get("xpath"),
            "platform": data.get("platform"),
            "element_type": data.get("element_type") or data.get("type"),
            "required": bool(data.get("required")),
        }

    def _required_fallback_cases(
        self,
        case_type: str,
        asset: dict[str, Any],
        elements: list[dict[str, Any]],
        steps: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        required = [item for item in elements if item.get("data", {}).get("required")]
        return [
            case_json(
                case_type,
                f"[必填为空] {element['name']}",
                "required_empty",
                {
                    "steps": [
                        self._required_empty_step(step, int(element["id"]))
                        for step in steps
                    ],
                    "focus": element.get("data", {}).get("locator"),
                },
                0,
            )
            for element in required
        ]

    def _strategy_cases(
        self,
        case_type: str,
        asset: dict[str, Any],
        steps: list[dict[str, Any]],
        strategy: dict[str, Any],
        category: str,
    ) -> list[dict[str, Any]]:
        strategy_id = int(strategy["id"])
        key = knowledge_key(strategy)
        if category == "required_empty":
            return self._required_strategy_cases(
                case_type,
                asset,
                steps,
                strategy_id,
                key,
            )
        mutated = deepcopy(steps)
        if category == "boundary":
            for step in mutated:
                if step.get("action") == "fill":
                    step["value"] = f"{step.get('name') or 'boundary'}_" + "x" * 128
        elif category in {"invalid", "security"}:
            fill_step = next(
                (step for step in mutated if step.get("action") == "fill"),
                None,
            )
            if fill_step:
                fill_step["value"] = (
                    "' OR 1=1 --"
                    if category == "security"
                    else "<script>alert(1)</script>"
                )
        elif category == "delete_confirm":
            click_step = next(
                (step for step in mutated if step.get("action") == "click"),
                None,
            )
            if click_step:
                click_step["confirm_action"] = "confirm"
        generated = case_json(
            case_type,
            f"[{category_label(category)}] {asset['name']} - {strategy.get('name')}",
            category,
            {"steps": mutated},
            0,
        )
        return [with_strategy_meta(generated, strategy_id, key)]

    def _required_strategy_cases(
        self,
        case_type: str,
        asset: dict[str, Any],
        steps: list[dict[str, Any]],
        strategy_id: int,
        key: str | None,
    ) -> list[dict[str, Any]]:
        targets = [
            step
            for step in steps
            if step.get("action") == "fill"
            and step.get("required")
            and step.get("element_id")
        ]
        if not targets:
            targets = [
                step
                for step in steps
                if step.get("action") == "fill" and step.get("element_id")
            ]
        result: list[dict[str, Any]] = []
        for target in targets:
            element_id = int(target.get("element_id") or 0)
            generated = case_json(
                case_type,
                f"[必填为空] {asset['name']} - {target.get('name') or element_id}",
                "required_empty",
                {
                    "steps": [
                        self._required_empty_step(step, element_id)
                        for step in steps
                    ],
                    "focus": target.get("locator") or target.get("name"),
                },
                0,
            )
            result.append(with_strategy_meta(generated, strategy_id, key))
        return result

    def _required_empty_step(
        self,
        step: dict[str, Any],
        element_id: int,
    ) -> dict[str, Any]:
        copied = dict(step)
        if copied.get("element_id") == element_id and copied.get("action") == "fill":
            copied["value"] = ""
            copied["empty_target"] = True
        return copied

    def _default_value(self, element: dict[str, Any], action: str) -> Any:
        data = element.get("data", {})
        value = data.get("default_value") or data.get("example")
        if value not in (None, ""):
            return value
        if action != "fill":
            return None
        text = " ".join(
            str(item or "").lower()
            for item in (
                element.get("name"),
                data.get("label"),
                data.get("placeholder"),
                data.get("locator"),
                data.get("role_name"),
            )
        )
        value_rules = (
            (("password", "passwd", "pwd", "密码", "口令"), "123456"),
            (("phone", "mobile", "手机号", "手机"), "13800138000"),
            (("email", "mail", "邮箱"), "test@example.com"),
            (("username", "account", "login", "账号", "账户", "用户名"), "test_user"),
        )
        for markers, default in value_rules:
            if any(marker in text for marker in markers):
                return default
        return "test"

    def _action_for_type(self, element_type: str) -> str:
        if element_type in {"input", "textarea", "text"}:
            return "fill"
        if element_type in {"select", "dropdown"}:
            return "select"
        if element_type == "multi_select":
            return "multi_select"
        if element_type in {"checkbox", "radio"}:
            return "check"
        return "click"
