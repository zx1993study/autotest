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

        element = self.find_element(step)
        if action in {"tap", "click"}:
            element.click()
        elif action in {"input", "fill", "send_keys", "type"}:
            try:
                element.clear()
            except Exception:
                pass
            element.send_keys("" if step.get("value") is None else str(step.get("value")))
        elif action == "clear":
            element.clear()
        elif action == "select":
            element.click()
            value = str(step.get("value") or "")
            if value:
                self._tap_text(value)
        elif action in {"assert", "assert_text", "text_contains"}:
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
        start_x = int(step.get("start_x") or step.get("x1") or 0)
        start_y = int(step.get("start_y") or step.get("y1") or 0)
        end_x = int(step.get("end_x") or step.get("x2") or 0)
        end_y = int(step.get("end_y") or step.get("y2") or 0)
        duration = int(step.get("duration_ms") or step.get("duration") or 500)
        if not any((start_x, start_y, end_x, end_y)):
            size = self.driver.get_window_size()
            width = int(size.get("width", 0))
            height = int(size.get("height", 0))
            start_x = width // 2
            end_x = width // 2
            start_y = int(height * 0.8)
            end_y = int(height * 0.2)
        self.driver.swipe(start_x, start_y, end_x, end_y, duration)

    def _press_key(self, step: dict[str, Any]) -> None:
        keycode = step.get("keycode") or step.get("value")
        if keycode is None:
            raise ValueError("press_key requires keycode or value")
        self.driver.press_keycode(int(keycode))

    def _dedupe(self, locators: list[tuple[str, str]]) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for item in locators:
            if item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result
