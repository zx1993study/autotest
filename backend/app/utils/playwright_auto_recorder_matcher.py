from __future__ import annotations

import re
from typing import Any

from app.utils.playwright_auto_recorder_types import ControlInfo


class PlaywrightControlMatcherMixin:
    """Match AI-planned operations to visible Playwright controls."""

    def _find_plan_control(self, controls: list[ControlInfo], step: dict[str, Any], feature: str) -> ControlInfo | None:
        candidates = [
            str(step.get("element_name") or ""),
            str(step.get("name") or ""),
            str(step.get("locator") or ""),
            str(step.get("text") or ""),
            str(step.get("purpose") or ""),
        ]
        candidates = [item.strip().lower() for item in candidates if item and item.strip()]
        simplified_candidates = [self._simplify_text(item) for item in candidates]
        simplified_candidates = [item for item in simplified_candidates if item]

        action = self._normalize_plan_action(step.get("action"))
        match_action = "" if action == "record" else action
        if action in {"click", "record"} and self._candidate_mentions_cancel(candidates, simplified_candidates):
            return self._find_cancel_control(controls)

        control_index = self._plan_control_index(step)
        if control_index is not None and 0 <= control_index < len(controls):
            indexed_control = controls[control_index]
            if self._control_matches_plan_action(indexed_control, match_action) and self._plan_control_matches_candidates(
                indexed_control,
                candidates,
                simplified_candidates,
            ):
                return indexed_control

        for control in controls:
            if not self._control_matches_plan_action(control, match_action):
                continue
            haystack = self._control_haystack(control)
            simplified_haystack = self._simplify_text(haystack)
            if any(candidate and candidate in haystack for candidate in candidates):
                return control
            if any(candidate and candidate in simplified_haystack for candidate in simplified_candidates):
                return control
        if action == "click":
            return self._find_feature_trigger_control(controls, feature)
        return None

    def _control_matches_plan_action(self, control: ControlInfo, action: str) -> bool:
        if action == "click":
            return self._is_clickable(control)
        if action == "fill":
            return self._is_text_input(control) or self._is_select_like_control(control) or control.tag == "select"
        if action in {"select", "multi_select"}:
            return self._is_select_like_control(control) or control.tag == "select"
        if action in {"check", "uncheck"}:
            return control.input_type.lower() in {"checkbox", "radio"}
        return True

    def _plan_control_matches_candidates(
        self,
        control: ControlInfo,
        candidates: list[str],
        simplified_candidates: list[str],
    ) -> bool:
        haystack = self._control_haystack(control)
        simplified_haystack = self._simplify_text(haystack)
        return any(candidate and candidate in haystack for candidate in candidates) or any(
            candidate and candidate in simplified_haystack for candidate in simplified_candidates
        )

    def _plan_control_index(self, step: dict[str, Any]) -> int | None:
        value = step.get("control_index")
        if value in (None, ""):
            value = step.get("controlIndex")
        if value in (None, ""):
            value = step.get("index")
        try:
            index = int(value)
        except (TypeError, ValueError):
            return None
        return index - 1 if index > 0 else None

    def _control_haystack(self, control: ControlInfo) -> str:
        return " ".join(
            [
                control.name,
                control.placeholder,
                control.css,
                control.opener_css,
                control.class_name,
                self._locator_text(control),
                control.role,
                control.tag,
                control.input_type,
            ]
        ).lower()

    def _simplify_text(self, value: str) -> str:
        text = str(value or "").lower()
        text = re.sub(r"[\s:_\-\\/，,。.;；:：'\"“”‘’()（）\\[\\]{}]+", "", text)
        for word in (
            "输入框",
            "文本框",
            "下拉框",
            "选择框",
            "按钮",
            "字段",
            "控件",
            "元素",
            "链接",
            "请",
            "请输入",
            "请选择",
            "button",
            "input",
            "select",
            "field",
            "element",
        ):
            text = text.replace(word, "")
        return text

    def _find_feature_trigger_control(self, controls: list[ControlInfo], feature: str) -> ControlInfo | None:
        labels = self.FEATURE_LABELS.get(feature, ())
        if not labels:
            return None
        best: tuple[int, ControlInfo] | None = None
        for control in controls:
            if not self._is_clickable(control):
                continue
            score = self._feature_trigger_score(control, labels, feature)
            if score <= 0:
                continue
            if best is None or score > best[0]:
                best = (score, control)
        return best[1] if best else None

    def _feature_trigger_score(self, control: ControlInfo, labels: tuple[str, ...], feature: str) -> int:
        name = self._simplify_text(control.name)
        if not name:
            return 0
        score = 0
        for label in labels:
            simplified_label = self._simplify_text(label)
            if not simplified_label:
                continue
            if name == simplified_label:
                score = max(score, 100)
            elif simplified_label in name:
                score = max(score, 60)
        if feature == "add" and ("条件" in control.name or "filter" in control.lower_name):
            score -= 40
        if feature in {"edit", "delete", "detail"} and ("批量" in control.name or "batch" in control.lower_name):
            score -= 20
        return score

    def _find_cancel_control(self, controls: list[ControlInfo]) -> ControlInfo | None:
        return self._find_control(controls, self.CANCEL_LABELS + self.EXTRA_CANCEL_LABELS, buttons_only=True)

    def _candidate_mentions_cancel(self, candidates: list[str], simplified_candidates: list[str]) -> bool:
        labels = [item.lower() for item in self.EXTRA_CANCEL_LABELS]
        simplified_labels = [self._simplify_text(item) for item in labels]
        return any(label and any(label in candidate for candidate in candidates) for label in labels) or any(
            label and any(label in candidate for candidate in simplified_candidates) for label in simplified_labels
        )

    def _step_mentions_cancel(self, step: dict[str, Any]) -> bool:
        candidates = [
            str(step.get("element_name") or ""),
            str(step.get("name") or ""),
            str(step.get("locator") or ""),
            str(step.get("purpose") or ""),
        ]
        candidates = [item.strip().lower() for item in candidates if item and item.strip()]
        simplified_candidates = [self._simplify_text(item) for item in candidates]
        simplified_candidates = [item for item in simplified_candidates if item]
        return self._normalize_plan_action(step.get("action")) == "click" and self._candidate_mentions_cancel(
            candidates,
            simplified_candidates,
        )

    def _is_allowed_plan_step_for_feature(self, step: dict[str, Any], feature: str) -> bool:
        if self._normalize_plan_action(step.get("action")) != "click":
            return True

        candidates = [
            str(step.get("element_name") or ""),
            str(step.get("name") or ""),
            str(step.get("locator") or ""),
            str(step.get("purpose") or ""),
        ]
        simplified_text = self._simplify_text(" ".join(item for item in candidates if item))
        if not simplified_text:
            return True

        for candidate_feature, labels in self.FEATURE_LABELS.items():
            if candidate_feature in {feature, "login"}:
                continue
            if any(self._simplify_text(label) and self._simplify_text(label) in simplified_text for label in labels):
                return False
        return True

    def _normalize_plan_action(self, value: Any) -> str:
        text = str(value or "click").strip().lower()
        aliases = {
            "input": "fill",
            "type": "fill",
            "set_value": "fill",
            "select_option": "select",
            "choose": "select",
            "collect": "record",
            "capture": "record",
            "record_only": "record",
            "tap": "click",
            "press": "click",
        }
        return aliases.get(text, text)

    def _control_context(self, control: ControlInfo, index: int) -> dict[str, Any]:
        return {
            "index": index,
            "name": control.name,
            "tag": control.tag,
            "role": control.role,
            "type": control.input_type,
            "placeholder": control.placeholder,
            "locator": self._locator_text(control),
            "css": control.css,
            "opener_css": control.opener_css,
            "default_action": self._default_action(control, "page"),
            "in_dialog": control.in_dialog,
            "is_select": self._is_select_like_control(control),
        }
