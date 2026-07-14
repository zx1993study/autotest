from __future__ import annotations

import time
from typing import Any

from app.utils.cookie_utils import normalize_playwright_cookie
from app.utils.playwright_auto_recorder_types import CONTROL_SELECTOR, DIALOG_SELECTOR, ControlInfo
from app.utils.select_control_resolver import SelectControlResolver


class PlaywrightStepGeneratorMixin:
    """Generate codegen-like Playwright steps from controls and safe actions."""

    def _append_control_steps(
        self,
        page: Any,
        feature: str,
        controls: list[ControlInfo],
        script_lines: list[str],
        operations: list[dict[str, Any]],
        element_steps: list[dict[str, Any]] | None = None,
    ) -> None:
        seen: set[str] = set()
        planned_steps = [item for item in element_steps or [] if isinstance(item, dict)]
        if planned_steps:
            self._append_planned_element_steps(page, feature, controls, planned_steps, script_lines, operations, seen)
            return

        for control in controls:
            action = self._default_action(control, feature)
            if not action:
                continue
            value = self._sample_value(control)
            line = self._script_line(control, action, value)
            if not line or line in seen:
                continue
            seen.add(line)
            if not self._append_script_line(script_lines, line):
                continue
            operations.append(
                {
                    "name": control.name,
                    "action": action,
                    "value": value,
                    "locator": self._locator_text(control),
                    "in_dialog": control.in_dialog,
                    "generated_only": True,
                }
            )
            self._apply_safe_control_action(page, control, action, value, operations)

    def _append_planned_element_steps(
        self,
        page: Any,
        feature: str,
        controls: list[ControlInfo],
        element_steps: list[dict[str, Any]],
        script_lines: list[str],
        operations: list[dict[str, Any]],
        seen: set[str],
    ) -> None:
        for step in element_steps:
            control = self._find_plan_control(controls, step, feature)
            if not control:
                continue
            action = self._record_action_for_element_step(control, step, feature)
            if not action:
                continue
            value = str(step.get("default_value") or step.get("value") or step.get("example") or "")
            if action in {"fill", "select_option"} and not value:
                value = self._sample_value(control)
            line = self._script_line(control, action, value)
            if not line or line in seen:
                continue
            seen.add(line)
            if not self._append_script_line(script_lines, line):
                continue
            operations.append(
                {
                    "name": step.get("element_name") or step.get("name") or control.name,
                    "action": action,
                    "value": value,
                    "locator": self._locator_text(control),
                    "in_dialog": control.in_dialog,
                    "planned_element": True,
                }
            )
            if action != "click":
                self._apply_safe_control_action(page, control, action, value, operations)

    def _record_action_for_element_step(self, control: ControlInfo, step: dict[str, Any], feature: str) -> str | None:
        action = self._normalize_plan_action(step.get("action"))
        if action in {"select", "multi_select"}:
            return "select_option"
        if action in {"fill", "check", "click"}:
            return action
        return self._record_action_for_control(control, feature)

    def _append_script_line(self, script_lines: list[str], line: str | None) -> bool:
        if not line:
            return False
        formatted = f"    {line}"
        if formatted in script_lines:
            return False
        script_lines.append(formatted)
        return True

    def _click_control(
        self,
        page: Any,
        control: ControlInfo,
        script_lines: list[str],
        operations: list[dict[str, Any]],
        reason: str,
        record_script: bool = True,
    ) -> bool:
        line = self._script_line(control, "click", None)
        if line and record_script:
            self._append_script_line(script_lines, line)
        try:
            page.locator(control.css).first.click()
            operations.append(
                {
                    "name": control.name,
                    "action": "click",
                    "locator": self._locator_text(control),
                    "reason": reason,
                    "in_dialog": control.in_dialog,
                }
            )
            return True
        except Exception as exc:  # noqa: BLE001 - failed UI actions should not abort parsing.
            operations.append(
                {
                    "name": control.name,
                    "action": "click",
                    "locator": self._locator_text(control),
                    "reason": reason,
                    "error": str(exc),
                }
            )
            return False

    def _record_action_for_control(self, control: ControlInfo, feature: str) -> str | None:
        action = self._default_action(control, feature)
        if action:
            return action
        if self._is_text_input(control):
            return "fill"
        if control.tag == "select":
            return "select_option"
        if control.input_type.lower() in {"checkbox", "radio"}:
            return "check"
        if self._is_clickable(control):
            return "click"
        return None

    def _apply_safe_control_action(
        self,
        page: Any,
        control: ControlInfo,
        action: str,
        value: str | None,
        operations: list[dict[str, Any]],
    ) -> bool:
        if action not in {"fill", "select_option", "check"}:
            return False
        try:
            if action == "fill":
                locator = page.locator(control.css).first
                locator.fill(value or "")
            elif action == "select_option":
                locator = SelectControlResolver.sync_opener_locator(page, control.css, control.opener_css)
                SelectControlResolver.sync_select(
                    page,
                    locator,
                    value,
                    control_name=control.name,
                )
            elif action == "check":
                locator = page.locator(control.css).first
                locator.check()
            operations.append(
                {
                    "name": control.name,
                    "action": action,
                    "value": value,
                    "locator": self._locator_text(control),
                    "in_dialog": control.in_dialog,
                    "executed": True,
                }
            )
            return True
        except Exception as exc:  # noqa: BLE001 - keep scanning even when one control cannot be operated.
            operations.append(
                {
                    "name": control.name,
                    "action": action,
                    "value": value,
                    "locator": self._locator_text(control),
                    "error": str(exc),
                    "executed": False,
                }
            )
            return False

    def _visible_controls(self, page: Any) -> list[ControlInfo]:
        rows = page.evaluate(
            """
            ({ controlSelector, dialogSelector, selectOpenerSelector }) => {
              const isVisible = (el) => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style && style.visibility !== 'hidden' && style.display !== 'none'
                  && rect.width > 0 && rect.height > 0;
              };
              const cssPath = (el) => {
                if (el.id) return `#${CSS.escape(el.id)}`;
                const parts = [];
                let current = el;
                while (current && current.nodeType === Node.ELEMENT_NODE && parts.length < 5) {
                  const tag = current.tagName.toLowerCase();
                  const parent = current.parentElement;
                  if (!parent) {
                    parts.unshift(tag);
                    break;
                  }
                  const siblings = Array.from(parent.children).filter(item => item.tagName === current.tagName);
                  const index = siblings.indexOf(current) + 1;
                  parts.unshift(siblings.length > 1 ? `${tag}:nth-of-type(${index})` : tag);
                  current = parent;
                }
                return parts.join(' > ');
              };
              return Array.from(document.querySelectorAll(controlSelector)).map((el) => {
                const tag = el.tagName.toLowerCase();
                const opener = el.closest(selectOpenerSelector) || el;
                const target = el.matches('input, textarea, select') ? el : el.querySelector('input, textarea, select') || el;
                const role = target.getAttribute('role') || el.getAttribute('role') || '';
                const text = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ');
                const label = target.getAttribute('aria-label') || el.getAttribute('aria-label') ||
                  target.getAttribute('title') || el.getAttribute('title') || '';
                const placeholder = target.getAttribute('placeholder') || '';
                const name = (label || placeholder || text || target.getAttribute('name') || target.id || tag).trim();
                return {
                  css: cssPath(el),
                  tag,
                  role,
                  name,
                  input_type: target.getAttribute('type') || role || '',
                  placeholder,
                  value: target.value || '',
                  disabled: Boolean(target.disabled || el.disabled || el.getAttribute('aria-disabled') === 'true'),
                  visible: isVisible(el),
                  in_dialog: Boolean(el.closest(dialogSelector)),
                  readonly: Boolean(
                    target.readOnly ||
                    target.getAttribute('readonly') !== null ||
                    target.getAttribute('aria-readonly') === 'true'
                  ),
                  class_name: `${target.className || ''} ${el.className || ''} ${opener.className || ''}`,
                  opener_css: cssPath(opener),
                };
              }).filter(item => item.visible && !item.disabled && item.name);
            }
            """,
            {
                "controlSelector": CONTROL_SELECTOR,
                "dialogSelector": DIALOG_SELECTOR,
                "selectOpenerSelector": SelectControlResolver.control_selector(),
            },
        )
        return self._deduplicate_controls([ControlInfo(**row) for row in rows if isinstance(row, dict)])

    def _deduplicate_controls(self, controls: list[ControlInfo]) -> list[ControlInfo]:
        """Collapse duplicate inner-input and outer-container select matches."""

        result: list[ControlInfo] = []
        seen: set[str] = set()
        for control in controls:
            key = control.opener_css if self._is_select_like_control(control) and control.opener_css else control.css
            if key in seen:
                continue
            seen.add(key)
            result.append(control)
        return result

    def _prefer_dialog_controls(self, controls: list[ControlInfo]) -> list[ControlInfo]:
        dialog_controls = [item for item in controls if item.in_dialog]
        return dialog_controls or controls

    def _find_control(
        self,
        controls: list[ControlInfo],
        labels: tuple[str, ...],
        buttons_only: bool = False,
    ) -> ControlInfo | None:
        lowered = [label.lower() for label in labels]
        for control in controls:
            if buttons_only and not self._is_clickable(control):
                continue
            if any(label and label in control.lower_name for label in lowered):
                return control
        return None

    def _default_action(self, control: ControlInfo, feature: str) -> str | None:
        if self._is_select_like_control(control) or control.tag == "select":
            return "select_option"
        if self._is_text_input(control):
            return "fill"
        if control.input_type.lower() in {"checkbox", "radio"}:
            return "check"
        if self._is_clickable(control):
            if feature in {"add", "edit", "delete", "import"} and self._looks_like_cancel(control):
                return None
            if feature in {"add", "edit", "import"} and self._looks_like_submit(control):
                return None
            if feature == "delete" and (self._looks_like_submit(control) or self._looks_like_destructive(control)):
                return None
            if feature == "query" and self._looks_like_query(control):
                return None
            return "click"
        return None

    def _script_line(self, control: ControlInfo, action: str, value: str | None) -> str | None:
        locator = self._playwright_locator(control)
        if action in {"fill", "select_option"}:
            return f"{locator}.{action}({value!r})"
        if action == "check":
            return f"{locator}.check()"
        if action == "click":
            return f"{locator}.click()"
        return None

    def _playwright_locator(self, control: ControlInfo) -> str:
        input_type = control.input_type.lower()
        if self._is_select_like_control(control) and control.role.lower() in {"combobox", "listbox"} and control.name:
            return f"page.get_by_role({control.role.lower()!r}, name={control.name!r})"
        if input_type in {"checkbox", "radio"} and control.name:
            return f"page.get_by_role({input_type!r}, name={control.name!r})"
        if self._is_clickable(control) and control.name:
            role = "link" if control.tag == "a" or control.role == "link" else "button"
            return f"page.get_by_role({role!r}, name={control.name!r})"
        if control.placeholder:
            return f"page.get_by_placeholder({control.placeholder!r})"
        return f"page.locator({control.css!r})"

    def _locator_text(self, control: ControlInfo) -> str:
        input_type = control.input_type.lower()
        if input_type in {"checkbox", "radio"} and control.name:
            return f"{input_type}, name={control.name}"
        if self._is_clickable(control) and control.name:
            role = "link" if control.tag == "a" or control.role == "link" else "button"
            return f"{role}, name={control.name}"
        if control.placeholder:
            return control.placeholder
        return control.css

    def _sample_value(self, control: ControlInfo) -> str:
        existing = str(control.value or "").strip()
        if existing:
            return existing
        text = f"{control.name} {control.placeholder} {control.input_type}".lower()
        if "date" in text or "日期" in text:
            return "2026-07-09"
        if "phone" in text or "mobile" in text or "手机号" in text or "电话" in text:
            return "13800138000"
        if "email" in text or "邮箱" in text:
            return "test@example.com"
        if "password" in text or "密码" in text:
            return "Aa123456"
        if "number" in text or "金额" in text or "数量" in text:
            return "1"
        return "测试数据"

    def _normalize_cookie(self, cookie: dict[str, Any], target_url: str) -> dict[str, Any]:
        return normalize_playwright_cookie(cookie, target_url)

    def _short_wait(self, page: Any, deadline: float | None = None) -> None:
        if deadline is not None and time.time() >= deadline:
            return
        try:
            page.wait_for_timeout(500)
        except Exception:
            return

    def _normalize_feature_type(self, value: str) -> str:
        text = str(value or "page").strip().lower()
        aliases = {"search": "query", "create": "add", "update": "edit", "remove": "delete", "view": "detail"}
        return aliases.get(text, text)

    def _is_text_input(self, control: ControlInfo) -> bool:
        if self._is_select_like_control(control):
            return False
        input_type = control.input_type.lower()
        return control.tag in {"textarea"} or (
            control.tag == "input" and input_type not in {"button", "submit", "reset", "checkbox", "radio", "file"}
        ) or control.role == "textbox"

    def _is_select_like_control(self, control: ControlInfo) -> bool:
        return SelectControlResolver.is_select_like(
            tag=control.tag,
            role=control.role,
            input_type=control.input_type,
            name=control.name,
            placeholder=control.placeholder,
            class_name=control.class_name,
            readonly=control.readonly,
        )

    def _is_clickable(self, control: ControlInfo) -> bool:
        input_type = control.input_type.lower()
        return (
            control.tag in {"button", "a"}
            or control.role in {"button", "link"}
            or (control.tag == "input" and input_type in {"button", "submit", "reset"})
        )

    def _looks_like_submit(self, control: ControlInfo) -> bool:
        name = re.sub(r"\s+", "", control.name or "")
        return bool(self.SUBMIT_RE.search(name))

    def _looks_like_destructive(self, control: ControlInfo) -> bool:
        name = re.sub(r"\s+", "", control.name or "")
        return bool(self.DESTRUCTIVE_RE.search(name))

    def _looks_like_query(self, control: ControlInfo) -> bool:
        name = self._simplify_text(control.name)
        labels = [self._simplify_text(item) for item in self.FEATURE_LABELS["query"]]
        return any(label and label in name for label in labels)

    def _looks_like_cancel(self, control: ControlInfo) -> bool:
        name = self._simplify_text(control.name)
        labels = [self._simplify_text(item) for item in self.EXTRA_CANCEL_LABELS]
        return any(label and label in name for label in labels)

    def _find_submit_control(self, controls: list[ControlInfo]) -> ControlInfo | None:
        return self._find_control(controls, self.SUBMIT_LABELS, buttons_only=True)

    def _find_query_control(self, controls: list[ControlInfo]) -> ControlInfo | None:
        return self._find_control(controls, self.FEATURE_LABELS["query"], buttons_only=True) or self._find_submit_control(controls)
