from __future__ import annotations

import ast
import re
from typing import Any


STRING_RE = re.compile(r"""(['"])(?P<value>(?:\\.|(?!\1).)*)\1""")
ROLE_NAME_RE = re.compile(r"""name\s*[:=]\s*(['"])(?P<value>(?:\\.|(?!\1).)*)\1""")
OPTION_SELECTOR = (
    "[role='option'], [role='treeitem'], .el-select-dropdown__item, .el-cascader-node, "
    ".el-tree-node__content, .ant-select-item-option, .ant-select-tree-node, .vxe-select-option"
)


class PlaywrightEngine:
    """Deterministic Playwright step engine used by server and Agent runtimes."""

    def __init__(self, page: Any, default_timeout: int = 5000) -> None:
        self.page = page
        self.default_timeout = default_timeout

    async def execute(self, step: dict[str, Any]) -> None:
        if self._truthy(step.get("skip", step.get("是否跳过"))):
            return
        action = str(step.get("action") or step.get("交互类型") or "click").lower()
        value = step.get("value", step.get("元素值", step.get("default_value")))
        if action == "wait":
            await self.page.wait_for_timeout(int(value or 1000))
            return
        if action == "manual":
            raise ValueError("Manual input requires a headed interactive runtime")
        locator = self.locator(step)
        if self._truthy(step.get("require_unique")):
            locator = self._strict_locator(step)
            await locator.first.wait_for(state="visible", timeout=self.default_timeout)
            count = await locator.count()
            if count != 1:
                raise ValueError(f"Locator matched {count} elements; expected exactly one")
        await self._perform(locator, step, action, value)

    async def execute_selector(self, step: dict[str, Any], selector: str) -> None:
        locator = self._first(self.page.locator(selector))
        action = str(step.get("action") or step.get("交互类型") or "click").lower()
        value = step.get("value", step.get("元素值", step.get("default_value")))
        await self._perform(locator, step, action, value)

    async def _perform(self, locator: Any, step: dict[str, Any], action: str, value: Any) -> None:
        await locator.wait_for(state="visible", timeout=self.default_timeout)
        if action in {"fill", "input", "type"}:
            await self._fill(locator, step, value)
            return
        if action in {"select", "select_option", "multi_select", "multi-select"}:
            await self._select(locator, value, multi=action in {"multi_select", "multi-select"}, strict=self._truthy(step.get("require_unique")))
            return
        if action in {"check", "checkbox"}:
            await locator.check()
            return
        if action == "uncheck":
            await locator.uncheck()
            return
        if action in {"dblclick", "double_click"}:
            await locator.dblclick()
            return
        if action == "hover":
            await locator.hover()
            return
        if action == "assert":
            expected = step.get("expected")
            if expected is not None:
                actual = await locator.inner_text()
                if str(expected) not in actual:
                    raise AssertionError(f"Expected text {expected!r} was not found")
            return
        await locator.click()

    async def _fill(self, locator: Any, step: dict[str, Any], value: Any) -> None:
        text = "" if value is None else str(value)
        if await self._is_select_like(locator, step):
            await self._select(locator, value, multi=False, strict=self._truthy(step.get("require_unique")))
            return
        try:
            await locator.fill(text)
            return
        except Exception as primary_error:  # noqa: BLE001 - generated locators may point at a field container.
            if not hasattr(locator, "locator"):
                raise
            editable = self._first(
                locator.locator(
                    "input:not([type='hidden']):not([readonly]), textarea:not([readonly]), "
                    "[contenteditable='true'], [role='textbox'], [role='spinbutton']"
                )
            )
            try:
                await editable.fill(text)
                return
            except Exception as fallback_error:  # noqa: BLE001
                raise primary_error from fallback_error

    async def _is_select_like(self, locator: Any, step: dict[str, Any]) -> bool:
        element_type = str(step.get("element_type") or step.get("type") or "").lower()
        action = str(step.get("action") or step.get("交互类型") or "").lower()
        if element_type in {"select", "dropdown", "multi_select"} or action in {
            "select",
            "select_option",
            "multi_select",
            "multi-select",
        }:
            return True
        try:
            meta = await locator.evaluate(
                """
                (el) => {
                  const target = el.matches('input, textarea, select') ? el : el.querySelector('input, textarea, select');
                  const source = target || el;
                  return {
                    tag: source.tagName ? source.tagName.toLowerCase() : '',
                    role: source.getAttribute('role') || el.getAttribute('role') || '',
                    placeholder: source.getAttribute('placeholder') || '',
                    className: `${source.className || ''} ${el.className || ''}`,
                    readonly: Boolean(source.readOnly || source.getAttribute('readonly') !== null),
                  };
                }
                """
            )
        except Exception:
            return False
        if not isinstance(meta, dict):
            return False
        if str(meta.get("tag") or "").lower() == "select":
            return True
        role = str(meta.get("role") or "").lower()
        if role in {"combobox", "listbox"}:
            return True
        markers = " ".join(
            str(item or "")
            for item in (
                step.get("name"),
                step.get("locator"),
                meta.get("placeholder"),
                meta.get("className"),
            )
        ).lower()
        return bool(meta.get("readonly")) and any(
            marker in markers
            for marker in ("请选择", "选择", "select", "dropdown", "picker", "cascader")
        )

    async def _select(self, locator: Any, value: Any, *, multi: bool, strict: bool = False) -> None:
        values = [str(item) for item in value] if multi and isinstance(value, list) else [str(value or "")]
        try:
            await locator.select_option(label=values if multi else values[0])
            return
        except Exception:
            pass
        if strict:
            try:
                await locator.select_option(value=values if multi else values[0])
                return
            except Exception:
                pass
        await locator.click()
        for text in values:
            if strict:
                option = self.page.locator(OPTION_SELECTOR).filter(has_text=re.compile(r"^\s*" + re.escape(text) + r"\s*$"))
                if not text or await option.count() != 1:
                    raise ValueError("Option is missing or ambiguous; refusing to select another value")
                await option.click()
                continue
            option = self.page.locator(OPTION_SELECTOR).filter(has_text=text).first if text else self.page.locator(OPTION_SELECTOR).first
            try:
                await option.click()
            except Exception:
                await self.page.locator(OPTION_SELECTOR).first.click()

    def _strict_locator(self, step: dict[str, Any]) -> Any:
        kind, value = step.get("locator_type"), str(step.get("locator") or "")
        page = self.page.frame_locator(step["frame_selector"]) if step.get("frame_selector") else self.page
        if kind == "role":
            role, name = self._role_values(step, value)
            return page.get_by_role(role, name=name, exact=True) if name else page.get_by_role(role)
        if kind == "text":
            return page.get_by_text(value, exact=True)
        if kind == "label":
            return page.get_by_label(value, exact=True)
        if kind == "placeholder":
            return page.get_by_placeholder(value, exact=True)
        if kind == "testid":
            return page.get_by_test_id(value)
        if kind == "xpath":
            return page.locator(value if value.startswith("xpath=") else f"xpath={value}")
        return page.locator(value)

    def locator(self, step: dict[str, Any]) -> Any:
        data = step.get("data") if isinstance(step.get("data"), dict) else {}
        locator_type = self._locator_type(step)
        locator_text = str(step.get("locator") or data.get("locator") or "").strip()
        playwright_locator = self._playwright_locator(step, locator_type, locator_text)
        if playwright_locator is not None:
            return playwright_locator
        selector = str(
            step.get("selector")
            or step.get("css_selector")
            or data.get("selector")
            or data.get("css_selector")
            or ""
        ).strip()
        if selector:
            return self._first(self.page.locator(selector))
        if locator_type == "placeholder" and locator_text:
            return self._first(self.page.get_by_placeholder(locator_text))
        if locator_type == "role":
            role, name = self._role_values(step, locator_text)
            return self._first(self.page.get_by_role(role, name=name) if name else self.page.get_by_role(role))
        if locator_type == "text" and locator_text:
            return self._first(self.page.get_by_text(locator_text, exact=True))
        if locator_type == "label" and locator_text:
            return self._first(self.page.get_by_label(locator_text))
        if locator_type == "testid" and locator_text:
            return self._first(self.page.get_by_test_id(locator_text))
        if locator_type == "xpath" and locator_text:
            return self._first(self.page.locator(locator_text if locator_text.startswith("xpath=") else f"xpath={locator_text}"))
        placeholder = str(step.get("placeholder") or "").strip()
        if placeholder:
            return self._first(self.page.get_by_placeholder(placeholder))
        role = str(step.get("role") or "").strip()
        role_name = str(step.get("role_name") or step.get("name") or "").strip()
        if role:
            return self._first(self.page.get_by_role(role, name=role_name) if role_name else self.page.get_by_role(role))
        if locator_text:
            return self._first(self.page.locator(locator_text))
        text = str(step.get("text") or step.get("name") or step.get("元素名称") or "").strip()
        if text:
            return self._first(self.page.get_by_text(text, exact=True))
        raise ValueError(f"Step has no locator or semantic name: {step}")

    def _playwright_locator(self, step: dict[str, Any], locator_type: str, locator: str) -> Any | None:
        data = step.get("data") if isinstance(step.get("data"), dict) else {}
        raw = str(step.get("playwright_locator") or data.get("playwright_locator") or "").strip()
        if not raw and (
            locator_type == "playwright"
            or locator.startswith("page.get_")
            or locator.startswith("page.getBy")
            or locator.startswith("page.locator(")
        ):
            raw = locator
        if not raw:
            return None
        current = self.page
        for _, method, args in self._locator_calls(self._normalize_playwright_locator(raw)):
            current = self._apply_locator_call(current, method, args)
            if current is None:
                return None
        return self._first(current)

    def _locator_calls(self, value: str) -> list[tuple[int, str, str]]:
        calls: list[tuple[int, str, str]] = []
        methods = ["getByRole", "getByLabel", "getByPlaceholder", "getByText", "getByTestId", "getByTitle", "locator"]
        for method in methods:
            marker = f"{method}("
            search_from = 0
            while True:
                marker_index = value.find(marker, search_from)
                if marker_index < 0:
                    break
                args = self._call_args_at(value, marker_index, method)
                if args is not None:
                    calls.append((marker_index, method, args))
                search_from = marker_index + len(marker)
        return sorted(calls, key=lambda item: item[0])

    def _call_args_at(self, value: str, marker_index: int, method: str) -> str | None:
        start = marker_index + len(method) + 1
        depth = 1
        quote: str | None = None
        escaped = False
        for index in range(start, len(value)):
            char = value[index]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif quote:
                if char == quote:
                    quote = None
            elif char in {"'", '"'}:
                quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return value[start:index].strip()
        return None

    def _apply_locator_call(self, target: Any, method: str, args: str) -> Any | None:
        strings = self._strings(args)
        if method == "getByRole":
            role = strings[0] if strings else "button"
            name = self._role_name(args) or (strings[1] if len(strings) > 1 else None)
            return target.get_by_role(role, name=name) if name else target.get_by_role(role)
        mapping = {
            "getByLabel": "get_by_label",
            "getByPlaceholder": "get_by_placeholder",
            "getByText": "get_by_text",
            "getByTestId": "get_by_test_id",
            "getByTitle": "get_by_title",
            "locator": "locator",
        }
        value = strings[0] if strings else ""
        if not value or method not in mapping:
            return None
        function = getattr(target, mapping[method])
        if method == "getByText":
            return function(value, exact="exact=True" in args or "exact: true" in args)
        return function(value)

    def _role_values(self, step: dict[str, Any], raw: str) -> tuple[str, str | None]:
        data = step.get("data") if isinstance(step.get("data"), dict) else {}
        normalized = self._normalize_playwright_locator(str(step.get("locator_args") or data.get("locator_args") or raw))
        strings = self._strings(normalized)
        role = str(step.get("role") or data.get("role") or (strings[0] if strings else "button"))
        name = str(step.get("role_name") or data.get("role_name") or self._role_name(normalized) or (strings[1] if len(strings) > 1 else ""))
        return role or "button", name or None

    def _locator_type(self, step: dict[str, Any]) -> str:
        data = step.get("data") if isinstance(step.get("data"), dict) else {}
        value = str(step.get("locator_type") or data.get("locator_type") or "css").lower().strip()
        aliases = {
            "get by role": "role", "get_by_role": "role", "getbyrole": "role",
            "get by text": "text", "get_by_text": "text", "getbytext": "text",
            "get by label": "label", "get_by_label": "label", "getbylabel": "label",
            "get by placeholder": "placeholder", "get_by_placeholder": "placeholder", "getbyplaceholder": "placeholder",
            "get by test id": "testid", "get_by_test_id": "testid", "getbytestid": "testid", "test_id": "testid",
        }
        return aliases.get(value, value)

    def _normalize_playwright_locator(self, value: str) -> str:
        replacements = {
            "get_by_role": "getByRole", "get_by_label": "getByLabel",
            "get_by_placeholder": "getByPlaceholder", "get_by_text": "getByText",
            "get_by_test_id": "getByTestId", "get_by_title": "getByTitle",
        }
        for source, target in replacements.items():
            value = value.replace(source, target)
        return value

    def _strings(self, value: str) -> list[str]:
        return [self._unescape(match.group("value")) for match in STRING_RE.finditer(value)]

    def _role_name(self, value: str) -> str | None:
        match = ROLE_NAME_RE.search(value)
        return self._unescape(match.group("value")) if match else None

    def _unescape(self, value: str) -> str:
        try:
            return ast.literal_eval(f'"{value}"')
        except Exception:
            return value

    def _first(self, locator: Any) -> Any:
        return getattr(locator, "first", locator)

    def _truthy(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "是", "跳过"}
