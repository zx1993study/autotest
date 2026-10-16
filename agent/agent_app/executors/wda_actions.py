from __future__ import annotations

import time
from typing import Any


class WdaActions:
    def __init__(self, session: Any) -> None:
        self.session = session

    def run(self, step: dict[str, Any], *, observed_element=None) -> None:
        action = str(step.get("action") or "tap").lower()
        if action in {"wait", "sleep"}:
            raw = float(step["duration_ms"]) / 1000 if step.get("duration_ms") is not None else float(step.get("value") or 1)
            time.sleep(min(60, max(0, raw)))
        elif action in {"swipe", "scroll"}:
            self._swipe(step)
        elif action == "assert_screen_contains":
            expected = str(step.get("value") or step.get("expected") or "")
            if not expected or expected not in self.session.source():
                raise AssertionError("Expected content was not found on screen")
        elif action == "launch_app":
            self.session.app_launch(str(step.get("bundle_id") or step.get("value") or ""))
        elif action == "terminate_app":
            self.session.app_terminate(str(step.get("bundle_id") or step.get("value") or ""))
        elif action == "hide_keyboard":
            self.session.keyboard_dismiss()
        elif action in {"tap", "click"} and self._coordinates(step):
            size = self.session.window_size()
            self.session.click(self._axis(step, "x", size.width), self._axis(step, "y", size.height))
        elif action in {"tap", "click", "input", "fill", "send_keys", "type", "clear", "assert", "assert_text", "text_contains", "select"}:
            self._element_action(action, step, observed_element)
        else:
            raise ValueError(f"Unsupported WDA action: {action}")

    def _element_action(self, action, step, observed_element=None):
        element = observed_element if observed_element is not None else self._selector(step).get(timeout=min(60, float(step.get("timeout_sec") or 10)))
        value = str(step.get("value") if step.get("value") is not None else "")
        if action in {"tap", "click", "select"}:
            element.click()
            if action == "select" and value:
                self.session(text=value).click()
        elif action in {"input", "fill", "send_keys", "type", "clear"}:
            element.clear_text()
            if action != "clear":
                element.set_text(value)
        else:
            info = element.info
            actual = str(info.get("value") or info.get("label") or info.get("name") or "")
            expected = str(step.get("expected") or value)
            if not expected or expected not in actual:
                raise AssertionError("Element text did not match the assertion")

    def _selector(self, step):
        kind = str(step.get("locator_type") or step.get("locator_method") or "text").lower()
        value = str(step.get("locator") or step.get("text") or step.get("content_desc") or step.get("resource_id") or step.get("xpath") or "")
        mapping = {"xpath": "xpath", "ios_predicate": "predicate", "ios_class_chain": "classChain", "accessibility_id": "name", "resource_id": "name", "id": "name", "name": "name", "text": "text", "class_name": "className"}
        if kind not in mapping or not value:
            raise ValueError("Step requires a supported locator or coordinates")
        return self.session(**{mapping[kind]: value})

    def _swipe(self, step):
        size = self.session.window_size()
        direction = str(step.get("direction") or "up")
        defaults = {"up": (.5, .8, .5, .2), "down": (.5, .2, .5, .8), "left": (.8, .5, .2, .5), "right": (.2, .5, .8, .5)}
        values = defaults.get(direction, defaults["up"])
        coordinates = []
        for key, ratio, length in zip(("start_x", "start_y", "end_x", "end_y"), values, (size.width, size.height, size.width, size.height)):
            coordinates.append(self._axis(step, key, length, ratio))
        self.session.swipe(*coordinates, duration=float(step.get("duration_ms") or 500) / 1000)

    @staticmethod
    def _coordinates(step):
        return any(key in step for key in ("x", "y", "x_pct", "y_pct", "tap_x", "tap_y")) and not step.get("locator")

    @staticmethod
    def _axis(step, key, length, default=.5):
        value = step.get(key, step.get(f"tap_{key}"))
        if value is not None:
            return float(value)
        return float(step.get(f"{key}_pct", default)) * length
