from __future__ import annotations

import time
from typing import Any


class AppiumActionExecutor:
    def __init__(self, driver: Any, default_timeout: int = 10, platform: str = "Android") -> None:
        self.driver = driver
        self.default_timeout = default_timeout
        self.platform = platform.lower()

    def run_step(self, step: dict[str, Any]) -> None:
        action = str(step.get("action") or step.get("interaction") or "tap").lower()
        if action in {"wait", "sleep"}:
            self._wait(step)
            return
        if action in {"swipe", "scroll"}:
            self._swipe(step)
            return
        if action in {"back", "navigate_back"}:
            self.driver.back()
            return
        if action in {"press_key", "keycode"}:
            self._press_key(step)
            return
        if action == "hide_keyboard":
            self._hide_keyboard()
            return
        if action == "switch_context":
            self._switch_context(step)
            return
        if action == "launch_app":
            self._launch_app(step)
            return
        if action == "terminate_app":
            self._terminate_app(step)
            return
        if action == "assert_screen_contains":
            self._assert_screen_contains(step)
            return

        if action in {"tap", "click"}:
            try:
                self.find_element(step).click()
            except Exception:
                if not self._has_coordinates(step):
                    raise
                self._tap_coordinates(step)
        elif action in {"input", "fill", "send_keys", "type"}:
            element = self.find_element(step)
            try:
                element.clear()
            except Exception:
                pass
            element.send_keys("" if step.get("value") is None else str(step.get("value")))
        elif action == "clear":
            element = self.find_element(step)
            element.clear()
        elif action == "select":
            element = self.find_element(step)
            element.click()
            value = str(step.get("value") or "")
            if value:
                self._tap_text(value)
        elif action in {"assert", "assert_text", "text_contains"}:
            element = self.find_element(step)
            expected = str(step.get("value") or step.get("expected") or "")
            actual = str(getattr(element, "text", "") or "")
            if expected and expected not in actual:
                raise AssertionError(f"expected text contains {expected!r}, actual {actual!r}")
        else:
            raise ValueError(f"unsupported app action: {action}")

    def find_element(self, step: dict[str, Any]) -> Any:
        from appium.webdriver.common.appiumby import AppiumBy
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        locators = self._locator_candidates(step, AppiumBy)
        last_error: Exception | None = None
        for by, value in locators:
            if not value:
                continue
            try:
                return WebDriverWait(self.driver, self.default_timeout).until(
                    EC.presence_of_element_located((by, value))
                )
            except Exception as exc:
                last_error = exc
        name = step.get("name") or step.get("element_name") or step.get("locator") or step
        raise RuntimeError(f"app element not found: {name}") from last_error

    def _locator_candidates(self, step: dict[str, Any], by: Any) -> list[tuple[str, str]]:
        locator_type = str(step.get("locator_type") or step.get("locator_method") or "").lower()
        locator = str(step.get("locator") or "").strip()
        candidates: list[tuple[str, str]] = []

        if locator_type and locator:
            candidates.extend(self._locator_by_type(locator_type, locator, by))
        candidates.extend(self._locator_by_type("resource_id", str(step.get("resource_id") or ""), by))
        candidates.extend(self._locator_by_type("accessibility_id", str(step.get("content_desc") or ""), by))
        candidates.extend(self._locator_by_type("text", str(step.get("text") or ""), by))
        candidates.extend(self._locator_by_type("xpath", str(step.get("xpath") or ""), by))
        if locator and not locator_type:
            candidates.extend(
                [
                    (by.ID, locator),
                    (by.ACCESSIBILITY_ID, locator),
                    (by.XPATH, locator),
                ]
            )
        return self._dedupe(candidates)

    def _locator_by_type(self, locator_type: str, locator: str, by: Any) -> list[tuple[str, str]]:
        if not locator:
            return []
        normalized = locator_type.lower().replace("-", "_")
        if normalized in {"id", "resource_id"}:
            return [(by.ID, locator)]
        if normalized in {"accessibility_id", "content_desc", "content_description"}:
            return [(by.ACCESSIBILITY_ID, locator)]
        if normalized == "xpath":
            return [(by.XPATH, locator)]
        if normalized == "css":
            return [(by.CSS_SELECTOR, locator)]
        if normalized in {"name", "field_name"}:
            return [(by.NAME, locator)]
        if normalized in {"tag", "tag_name"}:
            return [(by.TAG_NAME, locator)]
        if normalized in {"class", "class_name"}:
            return [(by.CLASS_NAME, locator)]
        if normalized in {"android_uiautomator", "uiautomator"}:
            return [(by.ANDROID_UIAUTOMATOR, locator)]
        if normalized == "ios_predicate":
            return [(by.IOS_PREDICATE, locator)]
        if normalized == "ios_class_chain":
            return [(by.IOS_CLASS_CHAIN, locator)]
        if normalized == "text":
            escaped = locator.replace('"', '\\"')
            if self.platform == "android":
                return [
                    (by.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{escaped}")'),
                    (by.XPATH, f'//*[@text="{locator}"]'),
                ]
            return [
                (by.IOS_PREDICATE, f'name == "{escaped}" OR label == "{escaped}" OR value == "{escaped}"'),
                (by.XPATH, f'//*[@name="{locator}" or @label="{locator}" or @value="{locator}"]'),
            ]
        return []

    def _tap_text(self, text: str) -> None:
        element = self.find_element({"locator_type": "text", "locator": text, "name": text})
        element.click()

    def _wait(self, step: dict[str, Any]) -> None:
        raw = step.get("value") or step.get("duration_ms") or step.get("wait_ms") or 1000
        try:
            value = float(raw)
        except (TypeError, ValueError):
            value = 1000
        seconds = value / 1000 if value > 20 else value
        time.sleep(max(seconds, 0))

    def _swipe(self, step: dict[str, Any]) -> None:
        start_x = self._coordinate_value(step, "start_x", "x1", "start_x_pct", "x1_pct")
        start_y = self._coordinate_value(step, "start_y", "y1", "start_y_pct", "y1_pct")
        end_x = self._coordinate_value(step, "end_x", "x2", "end_x_pct", "x2_pct")
        end_y = self._coordinate_value(step, "end_y", "y2", "end_y_pct", "y2_pct")
        duration = int(step.get("duration_ms") or step.get("duration") or 500)
        if not any((start_x, start_y, end_x, end_y)):
            size = self.driver.get_window_size()
            width = int(size.get("width", 0))
            height = int(size.get("height", 0))
            direction = str(step.get("direction") or "up").lower()
            if direction == "down":
                start_x, end_x = width // 2, width // 2
                start_y, end_y = int(height * 0.25), int(height * 0.78)
            elif direction == "left":
                start_x, end_x = int(width * 0.82), int(width * 0.18)
                start_y, end_y = height // 2, height // 2
            elif direction == "right":
                start_x, end_x = int(width * 0.18), int(width * 0.82)
                start_y, end_y = height // 2, height // 2
            else:
                start_x, end_x = width // 2, width // 2
                start_y, end_y = int(height * 0.8), int(height * 0.2)
        self.driver.swipe(start_x, start_y, end_x, end_y, duration)

    def _press_key(self, step: dict[str, Any]) -> None:
        keycode = step.get("keycode") or step.get("value")
        if keycode is None:
            raise ValueError("press_key requires keycode or value")
        self.driver.press_keycode(int(keycode))

    def _tap_coordinates(self, step: dict[str, Any]) -> None:
        x = self._coordinate_value(step, "x", "tap_x", "x_pct", "tap_x_pct")
        y = self._coordinate_value(step, "y", "tap_y", "y_pct", "tap_y_pct")
        if x <= 0 and y <= 0:
            raise ValueError("tap requires locator or coordinates")
        if hasattr(self.driver, "tap"):
            self.driver.tap([(x, y)])
            return
        self.driver.execute_script("mobile: tap", {"x": x, "y": y})

    def _coordinate_value(self, step: dict[str, Any], absolute_key: str, alias_key: str, percent_key: str, percent_alias_key: str) -> int:
        absolute = step.get(absolute_key)
        if absolute in (None, ""):
            absolute = step.get(alias_key)
        if absolute not in (None, ""):
            try:
                return int(float(absolute))
            except (TypeError, ValueError):
                return 0
        percent = step.get(percent_key)
        if percent in (None, ""):
            percent = step.get(percent_alias_key)
        if percent in (None, ""):
            return 0
        try:
            ratio = float(percent)
        except (TypeError, ValueError):
            return 0
        size = self.driver.get_window_size()
        axis = "width" if "x" in absolute_key else "height"
        return int(float(size.get(axis, 0)) * max(0.0, min(1.0, ratio)))

    def _has_coordinates(self, step: dict[str, Any]) -> bool:
        return any(step.get(key) not in (None, "") for key in ("x", "y", "tap_x", "tap_y", "x_pct", "y_pct", "tap_x_pct", "tap_y_pct"))

    def _hide_keyboard(self) -> None:
        try:
            self.driver.hide_keyboard()
        except Exception:
            pass

    def _switch_context(self, step: dict[str, Any]) -> None:
        target = str(step.get("context") or step.get("value") or "").strip()
        keyword = str(step.get("context_keyword") or "").strip().lower()
        contexts = [str(item) for item in (getattr(self.driver, "contexts", []) or [])]
        if not target and keyword:
            target = next((item for item in contexts if keyword in item.lower()), "")
        if not target:
            target = next((item for item in contexts if item.upper().startswith("WEBVIEW")), "")
        if not target:
            raise RuntimeError(f"context not found, available contexts: {contexts}")
        self.driver.switch_to.context(target)

    def _launch_app(self, step: dict[str, Any]) -> None:
        app_id = str(step.get("bundle_id") or step.get("package_name") or step.get("app_id") or step.get("value") or "").strip()
        if app_id and hasattr(self.driver, "activate_app"):
            self.driver.activate_app(app_id)
            return
        if hasattr(self.driver, "launch_app"):
            self.driver.launch_app()
            return
        raise ValueError("launch_app requires bundle_id/package_name/app_id when driver has no launch_app")

    def _terminate_app(self, step: dict[str, Any]) -> None:
        app_id = str(step.get("bundle_id") or step.get("package_name") or step.get("app_id") or step.get("value") or "").strip()
        if not app_id:
            raise ValueError("terminate_app requires bundle_id/package_name/app_id")
        self.driver.terminate_app(app_id)

    def _assert_screen_contains(self, step: dict[str, Any]) -> None:
        expected = str(step.get("value") or step.get("expected") or step.get("locator") or "").strip()
        if not expected:
            raise ValueError("assert_screen_contains requires value or expected")
        source = str(getattr(self.driver, "page_source", "") or "")
        if expected not in source:
            raise AssertionError(f"expected screen contains {expected!r}")

    def _dedupe(self, locators: list[tuple[str, str]]) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for item in locators:
            if item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result
