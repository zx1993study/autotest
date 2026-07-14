from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any

from app.utils.select_control_resolver import SelectControlResolver


ACTION_RE = re.compile(
    r"(?P<target>.+?)\.(?P<action>fill|click|dblclick|selectOption|select_option|check|uncheck)\((?P<args>.*)\)",
    re.IGNORECASE,
)
STRING_RE = re.compile(r"""(['"])(?P<value>(?:\\.|(?!\1).)*)\1""")
ROLE_NAME_RE = re.compile(r"""name\s*[:=]\s*(['"])(?P<value>(?:\\.|(?!\1).)*)\1""")
DATE_RE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}$")


@dataclass
class ScriptAction:
    action: str
    locator: str
    locator_type: str
    name: str
    value: str | None
    raw_locator: str
    meta: dict[str, Any]

    @property
    def key(self) -> str:
        return f"{self.locator_type}:{self.locator}"


class PlaywrightCodegenParser:
    def parse(self, script: str) -> list[dict[str, Any]]:
        actions = self._parse_actions(script)
        return self._merge_actions(actions)

    def _parse_actions(self, script: str) -> list[ScriptAction]:
        actions: list[ScriptAction] = []
        for line in script.splitlines():
            action = self._parse_line(line)
            if action:
                actions.append(action)
        return actions

    def _parse_line(self, line: str) -> ScriptAction | None:
        value = line.strip().rstrip(";")
        if not value or value.startswith("//") or value.startswith("#"):
            return None
        value = re.sub(r"^(await\s+)?", "", value)
        match = ACTION_RE.search(value)
        if not match:
            return None

        target = match.group("target").strip()
        action = self._normalize_action(match.group("action"))
        args = match.group("args")
        locator = self._parse_locator(target)
        default_value = self._first_string(args) if action in {"fill", "select"} else None
        return ScriptAction(
            action=action,
            locator=locator["locator"],
            locator_type=locator["locator_type"],
            name=locator["name"],
            value=default_value,
            raw_locator=target,
            meta=locator["meta"],
        )

    def _merge_actions(self, actions: list[ScriptAction]) -> list[dict[str, Any]]:
        fill_keys = {action.key for action in actions if action.action in {"fill", "select"}}
        used_indexes: set[int] = set()
        result: list[dict[str, Any]] = []

        for index, action in enumerate(actions):
            if index in used_indexes:
                continue
            if action.action == "click" and action.key in fill_keys:
                used_indexes.add(index)
                continue
            if action.action in {"fill", "select"}:
                result.append(self._element(action, "input" if action.action == "fill" else "select", action.action))
                used_indexes.add(index)
                continue
            if action.action in {"check", "uncheck"}:
                result.append(self._element(action, self._checkable_element_type(action), action.action))
                used_indexes.add(index)
                continue
            if action.action == "click" and self._is_checkable_target(action):
                result.append(self._element(action, self._checkable_element_type(action), "check"))
                used_indexes.add(index)
                continue

            dropdown = self._dropdown_from_click(actions, index)
            if dropdown:
                element, consumed = dropdown
                result.append(element)
                used_indexes.update(consumed)
                continue

            result.append(self._element(action, "button", "click"))
            used_indexes.add(index)

        return result

    def _dropdown_from_click(
        self,
        actions: list[ScriptAction],
        index: int,
    ) -> tuple[dict[str, Any], set[int]] | None:
        opener = actions[index]
        if opener.action != "click":
            return None
        if not self._looks_like_dropdown_opener(opener):
            return None

        option_indexes: list[int] = []
        close_index: int | None = None
        cursor = index + 1
        while cursor < len(actions):
            current = actions[cursor]
            if current.action != "click":
                break
            if current.key == opener.key and option_indexes:
                close_index = cursor
                break
            if option_indexes and current.locator_type not in {"text", "role"}:
                break
            option_indexes.append(cursor)
            if len(option_indexes) >= 8:
                break
            cursor += 1

        if not option_indexes:
            return None

        option_values = [self._option_value(actions[item]) for item in option_indexes]
        if self._looks_like_date_picker(opener, option_values):
            first_date = next((item for item in option_values if self._looks_like_date(item)), option_values[0])
            element = self._element(opener, "input", "fill", first_date)
            consumed = {index, option_indexes[0]}
            if close_index is not None:
                consumed.add(close_index)
            return element, consumed

        is_multi = close_index is not None and len(option_indexes) > 1
        element_type = "multi_select" if is_multi else "select"
        action = "multi_select" if is_multi else "select"
        default_value = ",".join(option_values) if is_multi else option_values[0]
        element = self._element(opener, element_type, action, default_value)
        consumed = {index, *option_indexes}
        if close_index is not None:
            consumed.add(close_index)
        return element, consumed

    def _looks_like_dropdown_opener(self, action: ScriptAction) -> bool:
        role = str(action.meta.get("role") or "").lower()
        if role in {"combobox", "listbox"}:
            return True
        text = " ".join(
            str(item or "").lower()
            for item in (
                action.name,
                action.locator,
                action.raw_locator,
                action.meta.get("locator_args"),
                action.meta.get("filter_text"),
            )
        )
        return SelectControlResolver.has_select_marker(text) or any(
            marker in text for marker in ("calendar", "date", "time", "日期", "时间")
        )

    def _element(
        self,
        action: ScriptAction,
        element_type: str,
        default_action: str,
        default_value: str | None = None,
    ) -> dict[str, Any]:
        value = default_value if default_value is not None else action.value
        return {
            "name": action.name or action.locator,
            "element_type": element_type,
            "action": default_action,
            "locator": action.locator,
            "locator_type": action.locator_type,
            "default_value": value,
            "example": value,
            **action.meta,
        }

    def _parse_locator(self, target: str) -> dict[str, Any]:
        normalized = self._normalize_playwright_locator(target)
        meta: dict[str, Any] = {}

        if "getByRole" in normalized:
            strings = self._strings(normalized)
            role = strings[0] if strings else ""
            name = self._role_name(normalized) or (strings[1] if len(strings) > 1 else role)
            locator_args = self._call_args(target, ["get_by_role", "getByRole"]) or self._role_args(role, name)
            meta.update(
                {
                    "role": role,
                    "role_name": name,
                    "locator_method": "role",
                    "locator_args": locator_args,
                }
            )
            return {"locator_type": "role", "locator": locator_args, "name": locator_args, "meta": meta}
        for method, locator_type in [
            ("getByLabel", "label"),
            ("getByPlaceholder", "placeholder"),
            ("getByText", "text"),
            ("getByTestId", "testid"),
            ("getByTitle", "text"),
        ]:
            if method in normalized:
                locator = self._first_string(normalized) or normalized
                return {"locator_type": locator_type, "locator": locator, "name": locator, "meta": meta}
        if ".locator(" in normalized or normalized.startswith("page.locator("):
            locator = self._first_string(normalized) or normalized
            locator_type = "xpath" if locator.startswith("//") or locator.startswith("xpath=") else "css"
            filter_text = self._filter_text(normalized)
            if filter_text:
                meta["filter_text"] = filter_text
            name = filter_text or self._human_name(locator)
            return {"locator_type": locator_type, "locator": locator, "name": name, "meta": meta}

        meta["playwright_locator"] = target
        return {"locator_type": "playwright", "locator": target, "name": self._human_name(target), "meta": meta}

    def _checkable_element_type(self, action: ScriptAction) -> str:
        text = self._checkable_text(action)
        if "radio" in text or "[type=\"radio\"]" in text or "[type='radio']" in text:
            return "radio"
        if "checkbox" in text or "[type=\"checkbox\"]" in text or "[type='checkbox']" in text:
            return "checkbox"
        if action.locator_type == "label" or "locator(\"label\"" in text or "locator('label'" in text:
            if any(marker in text for marker in ("agree", "remember", "select all", "all", "同意", "协议", "记住", "全选")):
                return "checkbox"
            return "radio"
        return "checkbox"

    def _is_checkable_target(self, action: ScriptAction) -> bool:
        text = self._checkable_text(action)
        if action.locator_type == "label" or "locator(\"label\"" in text or "locator('label'" in text:
            return True
        return any(
            marker in text
            for marker in (
                "radio",
                "checkbox",
                "[type=\"radio\"]",
                "[type='radio']",
                "[type=\"checkbox\"]",
                "[type='checkbox']",
            )
        )

    def _checkable_text(self, action: ScriptAction) -> str:
        return " ".join(
            str(item or "").lower()
            for item in (
                action.locator_type,
                action.locator,
                action.name,
                action.raw_locator,
                action.meta.get("role"),
                action.meta.get("locator_args"),
                action.meta.get("filter_text"),
            )
        )

    def _filter_text(self, value: str) -> str | None:
        match = re.search(r"""has_text\s*=\s*(['"])(?P<value>(?:\\.|(?!\1).)*)\1""", value)
        if not match:
            match = re.search(r"""hasText\s*:\s*(['"])(?P<value>(?:\\.|(?!\1).)*)\1""", value)
        if not match:
            return None
        return self._unescape_string(match.group("value"))

    def _normalize_action(self, action: str) -> str:
        if action in {"selectOption", "select_option"}:
            return "select"
        if action.lower() == "dblclick":
            return "dblclick"
        return action.lower()

    def _looks_like_date_picker(self, opener: ScriptAction, values: list[str]) -> bool:
        text = f"{opener.name} {opener.locator}".lower()
        return any(word in text for word in ["date", "time", "calendar", "日期", "时间"]) or any(
            self._looks_like_date(value) for value in values
        )

    def _looks_like_date(self, value: str) -> bool:
        return bool(DATE_RE.search(value.strip()))

    def _human_name(self, value: str) -> str:
        cleaned = value.strip().strip("#.").replace("_", " ").replace("-", " ")
        return cleaned[:80] or "element"

    def _option_value(self, action: ScriptAction) -> str:
        return str(action.meta.get("role_name") or action.name or action.locator)

    def _normalize_playwright_locator(self, value: str) -> str:
        replacements = {
            "get_by_role": "getByRole",
            "get_by_label": "getByLabel",
            "get_by_placeholder": "getByPlaceholder",
            "get_by_text": "getByText",
            "get_by_test_id": "getByTestId",
            "get_by_title": "getByTitle",
        }
        normalized = value
        for source, target in replacements.items():
            normalized = normalized.replace(source, target)
        return normalized

    def _call_args(self, value: str, methods: list[str]) -> str | None:
        for method in methods:
            marker = f"{method}("
            start = value.find(marker)
            if start < 0:
                continue
            start += len(marker)
            depth = 1
            quote: str | None = None
            escaped = False
            for index in range(start, len(value)):
                char = value[index]
                if escaped:
                    escaped = False
                    continue
                if char == "\\":
                    escaped = True
                    continue
                if quote:
                    if char == quote:
                        quote = None
                    continue
                if char in {"'", '"'}:
                    quote = char
                    continue
                if char == "(":
                    depth += 1
                    continue
                if char == ")":
                    depth -= 1
                    if depth == 0:
                        return value[start:index].strip()
        return None

    def _role_args(self, role: str, name: str | None) -> str:
        role_arg = self._quote_arg(role or "button")
        if not name:
            return role_arg
        return f"{role_arg}, name={self._quote_arg(name)}"

    def _quote_arg(self, value: str) -> str:
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

    def _first_string(self, value: str) -> str | None:
        values = self._strings(value)
        return values[0] if values else None

    def _strings(self, value: str) -> list[str]:
        return [self._unescape_string(match.group("value")) for match in STRING_RE.finditer(value)]

    def _role_name(self, value: str) -> str | None:
        match = ROLE_NAME_RE.search(value)
        if not match:
            return None
        return self._unescape_string(match.group("value"))

    def _unescape_string(self, value: str) -> str:
        try:
            return ast.literal_eval(f'"{value}"')
        except Exception:  # noqa: BLE001 - keep original text when escaping is malformed.
            return value
