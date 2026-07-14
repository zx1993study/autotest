from __future__ import annotations

import ast
import re
from typing import Any

from app.utils.select_control_resolver import SelectControlResolver


STRING_RE = re.compile(r"""(['"])(?P<value>(?:\\.|(?!\1).)*)\1""")
ROLE_NAME_RE = re.compile(r"""name\s*[:=]\s*(['"])(?P<value>(?:\\.|(?!\1).)*)\1""")


class PlaywrightActionExecutor:
    def __init__(self, page: Any, default_timeout: int = 5000) -> None:
        self.page = page
        self.default_timeout = default_timeout

    async def run_step(self, step: dict[str, Any]) -> None:
        if self._truthy(step.get("skip", step.get("是否跳过"))):
            return
        action = str(step.get("action") or step.get("交互类型") or "").lower()
        value = step.get("value", step.get("元素值", step.get("default_value")))
        if action == "fill":
            await self.fill(step, value)
        elif action in {"select", "select_option"}:
            await self.select(step, value)
        elif action in {"multi_select", "multi-select"}:
            await self.multi_select(step, value)
        elif action == "click":
            await self.click(step)
        elif action in {"dblclick", "double_click"}:
            await self.dblclick(step)
        elif action == "check":
            await self.check(step)
        elif action == "uncheck":
            await self.uncheck(step)
        elif action == "wait":
            await self.page.wait_for_timeout(int(value or 1000))

    async def fill(self, step: dict[str, Any], value: Any) -> None:
        await self._with_fallback(
            step,
            lambda locator: self._fill_or_select(locator, step, value),
        )

    async def click(self, step: dict[str, Any]) -> None:
        await self._with_fallback(step, lambda locator: locator.click())

    async def dblclick(self, step: dict[str, Any]) -> None:
        await self._with_fallback(step, lambda locator: locator.dblclick())

    async def check(self, step: dict[str, Any]) -> None:
        await self._with_fallback(step, lambda locator: locator.check())

    async def uncheck(self, step: dict[str, Any]) -> None:
        await self._with_fallback(step, lambda locator: locator.uncheck())

    async def select(self, step: dict[str, Any], value: Any) -> None:
        await self._select_with_fallback(step, value, multi=False)

    async def multi_select(self, step: dict[str, Any], value: Any) -> None:
        await self._select_with_fallback(step, value, multi=True)

    async def _fill_or_select(self, locator: Any, step: dict[str, Any], value: Any) -> None:
        if await SelectControlResolver.async_is_select_like_locator(locator, step):
            await SelectControlResolver.async_select(
                self.page,
                locator,
                value,
                timeout_ms=self.default_timeout,
                control_name=self._step_name(step),
            )
            return
        await locator.fill("" if value is None else str(value))

    async def _select_from_opener(self, opener: Any, value: Any) -> None:
        await SelectControlResolver.async_select(
            self.page,
            opener,
            value,
            timeout_ms=self.default_timeout,
        )

    async def _select_with_fallback(self, step: dict[str, Any], value: Any, *, multi: bool) -> None:
        primary = self._locator(step)
        try:
            await primary.wait_for(state="visible", timeout=self.default_timeout)
            await self._select_from_locator(primary, step, value, multi=multi)
            return
        except Exception as primary_error:  # noqa: BLE001 - fallback should preserve original failure if no candidate works.
            fallback = self._fallback_from_step(step)
            if fallback is None:
                raise primary_error
            await fallback.wait_for(state="visible", timeout=self.default_timeout)
            await self._select_from_locator(fallback, step, value, multi=multi)

    async def _select_from_locator(self, locator: Any, step: dict[str, Any], value: Any, *, multi: bool) -> None:
        if multi:
            await SelectControlResolver.async_multi_select(
                self.page,
                locator,
                value,
                timeout_ms=self.default_timeout,
                control_name=self._step_name(step),
            )
            return
        await SelectControlResolver.async_select(
            self.page,
            locator,
            value,
            timeout_ms=self.default_timeout,
            control_name=self._step_name(step),
        )

    def _locator(self, step: dict[str, Any]) -> Any:
        locator_type = self._locator_type(step)
        data = step.get("data") if isinstance(step.get("data"), dict) else {}
        locator = str(step.get("locator") or step.get("selector") or data.get("locator") or data.get("selector") or "")
        playwright_locator = self._playwright_locator(step, locator_type, locator)
        if playwright_locator is not None:
            return playwright_locator
        if locator_type == "role":
            role, name = self._role_values_from_step(step, locator)
            return self.page.get_by_role(role, name=name) if name else self.page.get_by_role(role)
        if locator_type == "text":
            return self.page.get_by_text(locator)
        if locator_type == "label":
            return self.page.get_by_label(locator)
        if locator_type == "placeholder":
            return self.page.get_by_placeholder(locator)
        if locator_type == "testid":
            return self.page.get_by_test_id(locator)
        if locator_type == "xpath":
            return self.page.locator(locator if locator.startswith("xpath=") else f"xpath={locator}")
        return self.page.locator(locator)

    async def _with_fallback(self, step: dict[str, Any], operation: Any) -> None:
        primary = self._locator(step)
        try:
            await primary.wait_for(state="visible", timeout=self.default_timeout)
            await operation(primary)
            return
        except Exception as primary_error:  # noqa: BLE001 - fallback should preserve original failure if no candidate works.
            fallback = self._fallback_from_step(step)
            if fallback is None:
                raise primary_error
            await fallback.wait_for(state="visible", timeout=self.default_timeout)
            await operation(fallback)

    def _playwright_locator(self, step: dict[str, Any], locator_type: str, locator: str) -> Any | None:
        data = step.get("data") if isinstance(step.get("data"), dict) else {}
        raw = str(step.get("playwright_locator") or data.get("playwright_locator") or "").strip()
        if not raw and (locator_type == "playwright" or locator.startswith("page.get_") or locator.startswith("page.getBy") or locator.startswith("page.locator(")):
            raw = locator
        if not raw:
            return None

        normalized = self._normalize_playwright_locator(raw)
        if "getByRole" in normalized:
            strings = self._strings(normalized)
            role = str(step.get("role") or (strings[0] if strings else "button"))
            name = self._role_name(normalized) or (strings[1] if len(strings) > 1 else None)
            return self.page.get_by_role(role, name=name) if name else self.page.get_by_role(role)

        method_map = [
            ("getByLabel", self.page.get_by_label),
            ("getByPlaceholder", self.page.get_by_placeholder),
            ("getByText", self.page.get_by_text),
            ("getByTestId", self.page.get_by_test_id),
            ("getByTitle", self.page.get_by_title),
        ]
        for method, factory in method_map:
            if method in normalized:
                value = self._first_string(normalized)
                return factory(value) if value else None

        if ".locator(" in normalized or normalized.startswith("page.locator("):
            value = self._first_string(normalized)
            return self.page.locator(value) if value else None
        return None

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

    def _locator_type(self, step: dict[str, Any]) -> str:
        data = step.get("data") if isinstance(step.get("data"), dict) else {}
        value = str(
            step.get("locator_type") or step.get("locator_method") or data.get("locator_type") or data.get("locator_method") or "css"
        ).lower().strip()
        aliases = {
            "get by role": "role",
            "get_by_role": "role",
            "getbyrole": "role",
            "get by text": "text",
            "get_by_text": "text",
            "getbytext": "text",
            "get by label": "label",
            "get_by_label": "label",
            "getbylabel": "label",
            "get by placeholder": "placeholder",
            "get_by_placeholder": "placeholder",
            "getbyplaceholder": "placeholder",
            "get by test id": "testid",
            "get_by_test_id": "testid",
            "getbytestid": "testid",
            "test_id": "testid",
            "data-testid": "testid",
        }
        return aliases.get(value, value)

    def _option_locator(self, value: str) -> Any:
        return SelectControlResolver._async_option_locator(self.page, value)

    def _all_options(self) -> Any:
        return self.page.locator(SelectControlResolver.OPTION_VISIBLE_SELECTOR)

    def _values(self, value: Any) -> list[str]:
        return SelectControlResolver.values(value)

    def _step_name(self, step: dict[str, Any]) -> str:
        data = step.get("data") if isinstance(step.get("data"), dict) else {}
        return str(
            step.get("name")
            or step.get("element_name")
            or step.get("locator")
            or data.get("name")
            or data.get("element_name")
            or data.get("locator")
            or ""
        )

    async def _is_readonly_select_like(self, locator: Any, step: dict[str, Any]) -> bool:
        return await SelectControlResolver.async_is_select_like_locator(locator, step)

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
        except Exception:  # noqa: BLE001 - keep original locator text when escaping is malformed.
            return value

    def _fallback_from_step(self, step: dict[str, Any]) -> Any | None:
        locator_type = self._locator_type(step)
        data = step.get("data") if isinstance(step.get("data"), dict) else {}
        raw = str(step.get("playwright_locator") or step.get("locator") or data.get("playwright_locator") or data.get("locator") or "").strip()
        if self._should_use_select_fallback(step):
            select_fallback = self._select_fallback_locator(step, raw)
            if select_fallback is not None:
                return select_fallback

        if locator_type == "role":
            role, name = self._role_values_from_step(step, raw)
            return self._fallback_locator(role, name)

        normalized = self._normalize_playwright_locator(raw)
        if "getByRole" not in normalized:
            return None
        strings = self._strings(normalized)
        role = str(step.get("role") or (strings[0] if strings else ""))
        name = self._role_name(normalized) or (strings[1] if len(strings) > 1 else None)
        return self._fallback_locator(role, name)

    def _select_fallback_locator(self, step: dict[str, Any], raw: str) -> Any | None:
        candidates = [item for item in self._step_text_candidates(step, raw) if item]
        if not candidates:
            return None

        result = None
        for name in candidates:
            for locator in self._select_fallback_candidates(name):
                result = locator if result is None else result.or_(locator)
        return result

    def _should_use_select_fallback(self, step: dict[str, Any]) -> bool:
        data = step.get("data") if isinstance(step.get("data"), dict) else {}
        action = str(step.get("action") or data.get("action") or "").lower()
        element_type = str(step.get("element_type") or data.get("element_type") or data.get("type") or "").lower()
        text = " ".join(self._step_text_candidates(step, "")).lower()
        return (
            action in {"select", "select_option", "multi_select", "multi-select"}
            or element_type in {"select", "dropdown", "multi_select"}
            or (action == "fill" and SelectControlResolver.has_select_marker(text))
        )

    def _select_fallback_candidates(self, name: str) -> list[Any]:
        placeholder_values = [name]
        if not name.startswith("请选择"):
            placeholder_values.append(f"请选择{name}")

        candidates: list[Any] = []
        for value in placeholder_values:
            candidates.append(self.page.get_by_placeholder(value))
            candidates.append(self.page.locator(f"input[placeholder*={self._css_string(value)}]"))

        candidates.extend(
            [
                self.page.get_by_label(name),
                self.page.locator(SelectControlResolver.OPENER_SELECTOR).filter(has_text=name),
                self.page.get_by_text(name, exact=True)
                .locator(
                    "xpath=ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' el-form-item ') "
                    "or contains(concat(' ', normalize-space(@class), ' '), ' form-item ')][1]"
                )
                .locator(SelectControlResolver.OPENER_SELECTOR),
            ]
        )
        return candidates

    def _step_text_candidates(self, step: dict[str, Any], raw: str) -> list[str]:
        data = step.get("data") if isinstance(step.get("data"), dict) else {}
        values = [
            step.get("name"),
            step.get("element_name"),
            step.get("locator"),
            step.get("selector"),
            data.get("name"),
            data.get("element_name"),
            data.get("locator"),
            raw,
        ]
        result: list[str] = []
        for value in values:
            text = str(value or "").strip().strip("'\"")
            if not text or text.startswith(("page.", "#", ".", "//", "xpath=")):
                continue
            if text not in result:
                result.append(text)
        return result

    def _css_string(self, value: str) -> str:
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

    def _role_values_from_step(self, step: dict[str, Any], locator: str) -> tuple[str, str | None]:
        data = step.get("data") if isinstance(step.get("data"), dict) else {}
        raw = str(step.get("locator_args") or data.get("locator_args") or locator or "").strip()
        role = str(step.get("role") or data.get("role") or "").strip()
        role_name = str(step.get("role_name") or data.get("role_name") or "").strip()

        normalized = self._normalize_playwright_locator(raw)
        strings = self._strings(normalized)
        parsed_name = self._role_name(normalized)
        looks_like_args = bool(strings) and ("name" in normalized or "," in normalized or raw.startswith(("'", '"')))

        if not role and strings:
            role = strings[0]
        if not role_name:
            role_name = parsed_name or (strings[1] if len(strings) > 1 else "")
        if not role_name and not looks_like_args and raw:
            role_name = raw

        return role or "button", role_name or None

    def _fallback_locator(self, role: str, name: str | None) -> Any | None:
        if not name:
            return None
        candidates = [
            self.page.get_by_placeholder(name),
            self.page.get_by_label(name),
            self.page.get_by_text(name, exact=True),
        ]
        if role in {"textbox", "searchbox"}:
            candidates.append(self.page.locator("input, textarea").filter(has=self.page.get_by_placeholder(name)))
        if role == "button":
            candidates.append(self.page.locator("button, [role='button'], .el-button").filter(has_text=name))
        locator = candidates[0]
        for candidate in candidates[1:]:
            locator = locator.or_(candidate)
        return locator

    def _truthy(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "是", "跳过"}
