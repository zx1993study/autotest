from __future__ import annotations

from typing import Any


class SelectControlError(RuntimeError):
    """Raised when a custom select control cannot be opened or matched."""


class SelectControlResolver:
    """Resolve and operate native/custom select controls for Playwright flows.

    The scanner uses Playwright's sync API while case execution uses the async
    API. Keeping selectors, marker words, option matching, and error messages
    here prevents the two paths from slowly drifting apart.
    """

    OPENER_SELECTOR = (
        "select, [role='combobox'], [role='listbox'], [aria-haspopup='listbox'], [aria-haspopup='tree'], "
        ".el-select, .el-cascader, .el-date-editor, .ant-select, .ant-select-selector, .ant-picker, "
        ".vxe-select, .ivu-select, input[readonly][placeholder*='选择'], input[readonly][placeholder*='请选择']"
    )
    OPENER_XPATH = (
        "xpath=ancestor-or-self::*[self::select or @role='combobox' or @role='listbox' or "
        "@aria-haspopup='listbox' or @aria-haspopup='tree' or "
        "contains(concat(' ', normalize-space(@class), ' '), ' el-select ') or "
        "contains(concat(' ', normalize-space(@class), ' '), ' el-cascader ') or "
        "contains(concat(' ', normalize-space(@class), ' '), ' el-date-editor ') or "
        "contains(concat(' ', normalize-space(@class), ' '), ' ant-select ') or "
        "contains(concat(' ', normalize-space(@class), ' '), ' ant-select-selector ') or "
        "contains(concat(' ', normalize-space(@class), ' '), ' ant-picker ') or "
        "contains(concat(' ', normalize-space(@class), ' '), ' vxe-select ') or "
        "contains(concat(' ', normalize-space(@class), ' '), ' ivu-select ')][1]"
    )
    OPTION_SELECTORS = (
        "[role='option']",
        "[role='treeitem']",
        ".el-select-dropdown__item",
        ".el-cascader-node",
        ".el-tree-node",
        ".el-tree-node__content",
        ".el-tree-node__label",
        ".ant-select-item-option",
        ".ant-select-tree-node",
        ".vxe-select-option",
        ".ivu-select-item",
    )
    OPTION_SELECTOR = ", ".join(OPTION_SELECTORS)
    OPTION_VISIBLE_SELECTOR = ", ".join(f"{selector}:visible" for selector in OPTION_SELECTORS)
    TREE_CONTENT_VISIBLE_SELECTOR = ".el-tree-node__content:visible"
    OPTION_CHECKBOX_SELECTOR = ".el-checkbox, .el-checkbox__input, .el-checkbox__inner"
    OPTION_ANCESTOR_XPATH = (
        "xpath=ancestor-or-self::*[@role='option' or @role='treeitem' or "
        "contains(concat(' ', normalize-space(@class), ' '), ' el-select-dropdown__item ') or "
        "contains(concat(' ', normalize-space(@class), ' '), ' el-cascader-node ') or "
        "contains(concat(' ', normalize-space(@class), ' '), ' el-tree-node__content ') or "
        "contains(concat(' ', normalize-space(@class), ' '), ' el-tree-node ') or "
        "contains(concat(' ', normalize-space(@class), ' '), ' ant-select-item-option ') or "
        "contains(concat(' ', normalize-space(@class), ' '), ' ant-select-tree-node ') or "
        "contains(concat(' ', normalize-space(@class), ' '), ' vxe-select-option ') or "
        "contains(concat(' ', normalize-space(@class), ' '), ' ivu-select-item ')][1]"
    )
    SELECT_MARKERS = (
        "请选择",
        "选择",
        "下拉",
        "select",
        "dropdown",
        "combobox",
        "listbox",
        "treeselect",
        "picker",
        "el-select",
        "el-cascader",
        "ant-select",
        "ant-picker",
        "vxe-select",
        "ivu-select",
    )

    @classmethod
    def control_selector(cls) -> str:
        """Return selectors that should be scanned as select openers."""

        return cls.OPENER_SELECTOR

    @classmethod
    def has_select_marker(cls, value: str) -> bool:
        """Return whether text contains a known select-like marker."""

        text = str(value or "").lower()
        return any(marker in text for marker in cls.SELECT_MARKERS)

    @classmethod
    def is_select_like(
        cls,
        *,
        tag: str,
        role: str,
        input_type: str,
        name: str,
        placeholder: str,
        class_name: str,
        readonly: bool,
    ) -> bool:
        """Detect native selects and common component-library select controls."""

        tag_text = str(tag or "").lower()
        role_text = str(role or "").lower()
        if tag_text == "select" or role_text in {"combobox", "listbox"}:
            return True

        text = " ".join(
            [
                str(name or ""),
                str(placeholder or ""),
                str(input_type or ""),
                role_text,
                str(class_name or ""),
            ]
        ).lower()
        if not cls.has_select_marker(text):
            return False

        return readonly or any(
            marker in text
            for marker in (
                "el-select",
                "el-cascader",
                "ant-select",
                "ant-picker",
                "vxe-select",
                "ivu-select",
                "combobox",
                "listbox",
            )
        )

    @classmethod
    def values(cls, value: Any) -> list[str]:
        """Normalize select values from scalar/list/comma-separated input."""

        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [item.strip() for item in str(value).split(",") if item.strip()]

    @classmethod
    def sync_opener_locator(cls, page: Any, css: str, opener_css: str | None = None) -> Any:
        """Locate the clickable opener for sync Playwright scanner flows."""

        return page.locator(opener_css or css).first

    @classmethod
    def sync_select(
        cls,
        page: Any,
        opener: Any,
        value: Any,
        *,
        timeout_ms: int = 5000,
        control_name: str = "",
    ) -> None:
        """Open a select control and click the requested option synchronously."""

        target_values = cls.values(value)
        if cls._sync_is_native_select(opener):
            if not target_values:
                cls._sync_select_first_native(opener, control_name)
                return
            cls._sync_select_native(opener, target_values[0], control_name)
            return

        last_error: SelectControlError | None = None
        for candidate in cls._sync_opener_candidates(opener):
            try:
                if not cls._sync_has_visible_options(page):
                    cls._sync_click_opener(candidate, control_name)
                cls._sync_wait_for_panel(page, timeout_ms)
                if target_values:
                    cls._sync_click_option(page, target_values[0], control_name)
                else:
                    cls._sync_click_first_option(page, control_name)
                return
            except SelectControlError as exc:
                last_error = exc
        raise last_error or SelectControlError(cls._error("无法完成下拉框选择", control_name, target_values[0]))

    @classmethod
    async def async_select(
        cls,
        page: Any,
        opener: Any,
        value: Any,
        *,
        timeout_ms: int = 5000,
        control_name: str = "",
    ) -> None:
        """Open a select control and click the requested option asynchronously."""

        target_values = cls.values(value)
        if await cls._async_is_native_select(opener):
            if not target_values:
                await cls._async_select_first_native(opener, control_name)
                return
            await cls._async_select_native(opener, target_values[0], control_name)
            return

        last_error: SelectControlError | None = None
        for candidate in cls._async_opener_candidates(opener):
            try:
                if not await cls._async_has_visible_options(page):
                    await cls._async_click_opener(candidate, control_name)
                await cls._async_wait_for_panel(page, timeout_ms)
                if target_values:
                    await cls._async_click_option(page, target_values[0], control_name)
                else:
                    await cls._async_click_first_option(page, control_name)
                return
            except SelectControlError as exc:
                last_error = exc
        raise last_error or SelectControlError(cls._error("无法完成下拉框选择", control_name, target_values[0]))

    @classmethod
    async def async_multi_select(
        cls,
        page: Any,
        opener: Any,
        value: Any,
        *,
        timeout_ms: int = 5000,
        control_name: str = "",
    ) -> None:
        """Open a multi-select control and click one or more requested options."""

        target_values = cls.values(value)
        last_error: SelectControlError | None = None
        for opener_candidate in cls._async_opener_candidates(opener):
            try:
                if not await cls._async_has_visible_options(page):
                    await cls._async_click_opener(opener_candidate, control_name)
                await cls._async_wait_for_panel(page, timeout_ms)
                if target_values == ["-1"]:
                    return
                if not target_values:
                    await cls._async_click_first_option(page, control_name)
                    await cls._async_click_opener(opener_candidate, control_name)
                    return
                if target_values == ["-2"]:
                    await cls._async_click_first_option(page, control_name)
                    await cls._async_click_opener(opener_candidate, control_name)
                    return
                if target_values == ["0"]:
                    await cls._async_click_all_options(page, control_name)
                    await cls._async_click_opener(opener_candidate, control_name)
                    return

                for item in target_values:
                    await cls._async_click_option(page, item, control_name)
                await cls._async_click_opener(opener_candidate, control_name)
                return
            except SelectControlError as exc:
                last_error = exc
        if target_values == ["-1"]:
            return
        raise last_error or SelectControlError(cls._error("无法完成多选下拉框选择", control_name))

    @classmethod
    async def async_is_select_like_locator(cls, locator: Any, step: dict[str, Any] | None = None) -> bool:
        """Inspect a locator and determine whether fill should become select."""

        step = step or {}
        data = step.get("data") if isinstance(step.get("data"), dict) else {}
        declared_type = str(step.get("element_type") or data.get("element_type") or data.get("type") or "").lower()
        declared_action = str(step.get("action") or data.get("action") or "").lower()
        if declared_type in {"select", "dropdown", "multi_select"} or declared_action in {"select", "multi_select"}:
            return True

        try:
            meta = await locator.evaluate(cls._locator_meta_script())
        except Exception:  # noqa: BLE001 - missing DOM metadata should keep normal fill behavior.
            return False
        if not isinstance(meta, dict):
            return False
        return cls.is_select_like(
            tag=str(meta.get("tag") or ""),
            role=str(meta.get("role") or ""),
            input_type=str(meta.get("input_type") or ""),
            name=str(meta.get("name") or meta.get("text") or ""),
            placeholder=str(meta.get("placeholder") or ""),
            class_name=f"{meta.get('class_name') or ''} {meta.get('text') or ''}",
            readonly=bool(meta.get("readonly")),
        )

    @classmethod
    def _locator_meta_script(cls) -> str:
        return """
        (el) => {
          const target = el.matches('input, textarea, select') ? el : el.querySelector('input, textarea, select');
          const source = target || el;
          const text = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ');
          return {
            tag: source.tagName ? source.tagName.toLowerCase() : '',
            role: source.getAttribute('role') || el.getAttribute('role') || '',
            input_type: source.getAttribute('type') || source.getAttribute('role') || '',
            text,
            name: source.getAttribute('aria-label') || source.getAttribute('title') || text ||
              source.getAttribute('name') || source.id || '',
            placeholder: source.getAttribute('placeholder') || '',
            class_name: `${source.className || ''} ${el.className || ''} ${
              source.parentElement ? source.parentElement.className || '' : ''
            }`,
            readonly: Boolean(
              source.readOnly ||
              source.getAttribute('readonly') !== null ||
              source.getAttribute('aria-readonly') === 'true'
            ),
          };
        }
        """

    @classmethod
    def _sync_is_native_select(cls, opener: Any) -> bool:
        try:
            return str(opener.evaluate("(el) => el.tagName ? el.tagName.toLowerCase() : ''")) == "select"
        except Exception:  # noqa: BLE001 - custom select path is the safe fallback.
            return False

    @classmethod
    async def _async_is_native_select(cls, opener: Any) -> bool:
        try:
            return str(await opener.evaluate("(el) => el.tagName ? el.tagName.toLowerCase() : ''")) == "select"
        except Exception:  # noqa: BLE001 - custom select path is the safe fallback.
            return False

    @classmethod
    def _sync_select_native(cls, opener: Any, value: str, control_name: str) -> None:
        try:
            opener.select_option(label=value)
            return
        except Exception:
            try:
                opener.select_option(value=value)
                return
            except Exception as exc:
                raise SelectControlError(cls._error("无法选择原生下拉框选项", control_name, value)) from exc

    @classmethod
    def _sync_select_first_native(cls, opener: Any, control_name: str) -> None:
        try:
            opener.select_option(index=0)
            return
        except Exception:
            try:
                opener.select_option(index=1)
                return
            except Exception as exc:
                raise SelectControlError(cls._error("无法选择原生下拉框第一项", control_name)) from exc

    @classmethod
    async def _async_select_native(cls, opener: Any, value: str, control_name: str) -> None:
        try:
            await opener.select_option(label=value)
            return
        except Exception:
            try:
                await opener.select_option(value=value)
                return
            except Exception as exc:
                raise SelectControlError(cls._error("无法选择原生下拉框选项", control_name, value)) from exc

    @classmethod
    async def _async_select_first_native(cls, opener: Any, control_name: str) -> None:
        try:
            await opener.select_option(index=0)
            return
        except Exception:
            try:
                await opener.select_option(index=1)
                return
            except Exception as exc:
                raise SelectControlError(cls._error("无法选择原生下拉框第一项", control_name)) from exc

    @classmethod
    def _sync_click_opener(cls, opener: Any, control_name: str) -> None:
        errors: list[str] = []
        try:
            opener.click()
            return
        except Exception as exc:
            errors.append(str(exc))
        try:
            opener.click(force=True)
            return
        except Exception as exc:
            errors.append(str(exc))
        try:
            opener.evaluate(cls._dom_click_script(), cls.OPENER_SELECTOR)
            return
        except Exception as exc:
            errors.append(str(exc))
            raise SelectControlError(cls._error("无法打开下拉框", control_name, errors=errors)) from exc

    @classmethod
    async def _async_click_opener(cls, opener: Any, control_name: str) -> None:
        errors: list[str] = []
        try:
            await opener.click()
            return
        except Exception as exc:
            errors.append(str(exc))
        try:
            await opener.click(force=True)
            return
        except Exception as exc:
            errors.append(str(exc))
        try:
            await opener.evaluate(cls._dom_click_script(), cls.OPENER_SELECTOR)
            return
        except Exception as exc:
            errors.append(str(exc))
            raise SelectControlError(cls._error("无法打开下拉框", control_name, errors=errors)) from exc

    @classmethod
    def _dom_click_script(cls) -> str:
        return """
        (el, openerSelector) => {
          const target = el.closest(openerSelector) || el;
          const rect = target.getBoundingClientRect();
          const eventInit = {
            bubbles: true,
            cancelable: true,
            composed: true,
            clientX: rect.left + Math.max(1, Math.min(rect.width / 2, rect.width - 1)),
            clientY: rect.top + Math.max(1, Math.min(rect.height / 2, rect.height - 1)),
            view: window
          };
          target.dispatchEvent(new MouseEvent('mousedown', eventInit));
          target.dispatchEvent(new MouseEvent('mouseup', eventInit));
          target.dispatchEvent(new MouseEvent('click', eventInit));
          if (typeof target.click === 'function') {
            target.click();
          }
        }
        """

    @classmethod
    def _sync_opener_candidates(cls, opener: Any) -> list[Any]:
        candidates = [opener]
        try:
            parent = opener.locator(cls.OPENER_XPATH).first
        except Exception:
            return candidates
        return candidates if parent is opener else [opener, parent]

    @classmethod
    def _async_opener_candidates(cls, opener: Any) -> list[Any]:
        candidates = [opener]
        try:
            parent = opener.locator(cls.OPENER_XPATH).first
        except Exception:
            return candidates
        return candidates if parent is opener else [opener, parent]

    @classmethod
    def _sync_wait_for_panel(cls, page: Any, timeout_ms: int) -> None:
        try:
            page.locator(cls.OPTION_VISIBLE_SELECTOR).first.wait_for(state="visible", timeout=timeout_ms)
        except Exception:
            return

    @classmethod
    async def _async_wait_for_panel(cls, page: Any, timeout_ms: int) -> None:
        try:
            await page.locator(cls.OPTION_VISIBLE_SELECTOR).first.wait_for(state="visible", timeout=timeout_ms)
        except Exception:
            return

    @classmethod
    def _sync_has_visible_options(cls, page: Any, timeout_ms: int = 250) -> bool:
        try:
            page.locator(cls.OPTION_VISIBLE_SELECTOR).first.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
            return False

    @classmethod
    async def _async_has_visible_options(cls, page: Any, timeout_ms: int = 250) -> bool:
        try:
            await page.locator(cls.OPTION_VISIBLE_SELECTOR).first.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
            return False

    @classmethod
    def _sync_option_locator(cls, page: Any, value: str) -> Any:
        candidates = cls._sync_option_candidates(page, value)
        if not candidates:
            raise SelectControlError(cls._error("无法查找下拉选项", value=value))
        locator = candidates[0]
        for candidate in candidates[1:]:
            locator = locator.or_(candidate)
        return locator

    @classmethod
    def _async_option_locator(cls, page: Any, value: str) -> Any:
        candidates = cls._async_option_candidates(page, value)
        if not candidates:
            raise SelectControlError(cls._error("无法查找下拉选项", value=value))
        locator = candidates[0]
        for candidate in candidates[1:]:
            locator = locator.or_(candidate)
        return locator

    @classmethod
    def _sync_click_option(cls, page: Any, value: str, control_name: str) -> None:
        errors: list[str] = []
        for option in cls._sync_option_candidates(page, value):
            try:
                if option.count() <= 0:
                    continue
                cls._sync_click_option_locator(option.first)
                return
            except Exception as exc:  # noqa: BLE001 - try the next locator strategy.
                errors.append(str(exc))
                continue
        cls._sync_click_first_option(page, control_name, value, errors)

    @classmethod
    async def _async_click_option(cls, page: Any, value: str, control_name: str) -> None:
        errors: list[str] = []
        for option in cls._async_option_candidates(page, value):
            try:
                if await option.count() <= 0:
                    continue
                await cls._async_click_option_locator(option.first)
                return
            except Exception as exc:  # noqa: BLE001 - try the next locator strategy.
                errors.append(str(exc))
                continue
        await cls._async_click_first_option(page, control_name, value, errors)

    @classmethod
    def _sync_option_candidates(cls, page: Any, value: str) -> list[Any]:
        """Return option locators ordered from clickable containers to text fallback."""

        candidates = []
        try:
            candidates.append(
                page.locator(cls.TREE_CONTENT_VISIBLE_SELECTOR)
                .filter(has_text=value)
                .locator(cls.OPTION_CHECKBOX_SELECTOR)
            )
            candidates.append(page.locator(cls.OPTION_VISIBLE_SELECTOR).filter(has_text=value))
        except Exception:
            pass
        try:
            candidates.append(page.get_by_role("option", name=value))
            candidates.append(page.get_by_role("treeitem", name=value))
        except Exception:
            pass
        try:
            text = page.get_by_text(value, exact=True)
            candidates.append(text.locator(cls.OPTION_ANCESTOR_XPATH))
            candidates.append(text)
        except Exception:
            return candidates
        return candidates

    @classmethod
    def _async_option_candidates(cls, page: Any, value: str) -> list[Any]:
        """Return option locators ordered from clickable containers to text fallback."""

        candidates = []
        try:
            candidates.append(
                page.locator(cls.TREE_CONTENT_VISIBLE_SELECTOR)
                .filter(has_text=value)
                .locator(cls.OPTION_CHECKBOX_SELECTOR)
            )
            candidates.append(page.locator(cls.OPTION_VISIBLE_SELECTOR).filter(has_text=value))
        except Exception:
            pass
        try:
            candidates.append(page.get_by_role("option", name=value))
            candidates.append(page.get_by_role("treeitem", name=value))
        except Exception:
            pass
        try:
            text = page.get_by_text(value, exact=True)
            candidates.append(text.locator(cls.OPTION_ANCESTOR_XPATH))
            candidates.append(text)
        except Exception:
            return candidates
        return candidates

    @classmethod
    def _sync_click_option_locator(cls, option: Any) -> None:
        try:
            option.click()
        except Exception:
            option.click(force=True)

    @classmethod
    async def _async_click_option_locator(cls, option: Any) -> None:
        try:
            await option.click()
        except Exception:
            await option.click(force=True)

    @classmethod
    def _sync_click_first_option(
        cls,
        page: Any,
        control_name: str,
        requested_value: str = "",
        errors: list[str] | None = None,
    ) -> None:
        fallback_errors = list(errors or [])
        for option in cls._sync_first_option_candidates(page):
            try:
                if option.count() <= 0:
                    continue
                cls._sync_click_option_locator(option.first)
                return
            except Exception as exc:  # noqa: BLE001 - keep trying generic option containers.
                fallback_errors.append(str(exc))
        raise SelectControlError(cls._error("未找到任何下拉选项", control_name, requested_value, fallback_errors))

    @classmethod
    async def _async_click_first_option(
        cls,
        page: Any,
        control_name: str,
        requested_value: str = "",
        errors: list[str] | None = None,
    ) -> None:
        fallback_errors = list(errors or [])
        for option in cls._async_first_option_candidates(page):
            try:
                if await option.count() <= 0:
                    continue
                await cls._async_click_option_locator(option.first)
                return
            except Exception as exc:  # noqa: BLE001 - keep trying generic option containers.
                fallback_errors.append(str(exc))
        raise SelectControlError(cls._error("未找到任何下拉选项", control_name, requested_value, fallback_errors))

    @classmethod
    def _sync_first_option_candidates(cls, page: Any) -> list[Any]:
        candidates = []
        try:
            candidates.append(page.locator(cls.TREE_CONTENT_VISIBLE_SELECTOR).locator(cls.OPTION_CHECKBOX_SELECTOR))
            candidates.append(page.locator(cls.TREE_CONTENT_VISIBLE_SELECTOR))
            candidates.append(page.locator(cls.OPTION_VISIBLE_SELECTOR))
        except Exception:
            pass
        return candidates

    @classmethod
    def _async_first_option_candidates(cls, page: Any) -> list[Any]:
        candidates = []
        try:
            candidates.append(page.locator(cls.TREE_CONTENT_VISIBLE_SELECTOR).locator(cls.OPTION_CHECKBOX_SELECTOR))
            candidates.append(page.locator(cls.TREE_CONTENT_VISIBLE_SELECTOR))
            candidates.append(page.locator(cls.OPTION_VISIBLE_SELECTOR))
        except Exception:
            pass
        return candidates

    @classmethod
    async def _async_click_all_options(cls, page: Any, control_name: str) -> None:
        options = page.locator(cls.OPTION_VISIBLE_SELECTOR)
        count = await options.count()
        if count <= 0:
            raise SelectControlError(cls._error("未找到任何下拉选项", control_name))
        for index in range(count):
            await options.nth(index).click()

    @classmethod
    def _error(cls, message: str, control_name: str = "", value: str = "", errors: list[str] | None = None) -> str:
        parts = [message]
        if control_name:
            parts.append(f"控件：{control_name}")
        if value:
            parts.append(f"选项：{value}")
        if errors:
            parts.append(f"最后错误：{errors[-1]}")
        return "；".join(parts)
