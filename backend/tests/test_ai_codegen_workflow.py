from __future__ import annotations

import unittest

from app.api.v1.web_pages import _codegen_target_url
from app.schemas.ai import WebFunctionElementGenerationRequest
from app.services.ai_generation_service import AiGenerationService
from app.utils.playwright_auto_recorder import ControlInfo, PlaywrightAutoRecorder


SCRIPT_TEXT = """from playwright.sync_api import Page

def test_recorded(page: Page):
    page.goto("https://example.test/users")
    page.get_by_role("button", name="Add").click()
"""


class FakeAutoRecorder:
    def __init__(self) -> None:
        self.started: dict | None = None

    def capture_and_record_with_plan(
        self,
        target_url: str,
        feature_type: str,
        feature_name: str,
        plan_builder,
        cookies: list[dict] | None = None,
        instruction: str | None = None,
        timeout_sec: int = 120,
        headless: bool = True,
    ) -> dict:
        capture = {
            "target_url": target_url,
            "title": "Users",
            "controls": [{"index": 1, "name": "Add", "role": "button", "locator": "button, name=Add"}],
            "warnings": [],
        }
        ai_plan = plan_builder(capture)
        self.started = {
            "url": target_url,
            "feature_type": feature_type,
            "feature_name": feature_name,
            "cookies": cookies or [],
            "instruction": instruction,
            "timeout_sec": timeout_sec,
            "headless": headless,
            "ai_plan": ai_plan,
        }
        return {
            "script_text": SCRIPT_TEXT,
            "operations": [{"name": "Add", "action": "click"}],
            "executed_ai_steps": [{"element_name": "Add", "action": "click", "executed": True, "matched": True}],
            "warnings": [],
            "feature_screenshot": {"screenshot_url": "/api/v1/screenshots/ai_element_add.png"},
            "screenshot_url": "/api/v1/screenshots/ai_element_add.png",
            "screenshot_file": "ai_element_add.png",
            "capture": capture,
            "ai_plan": ai_plan,
        }


class FakeAuthService:
    def web_cookies(self, auth_id: int | None) -> list[dict]:
        return [{"name": "sid", "value": "safe-cookie"}] if auth_id else []


class FakeUiService:
    def __init__(self) -> None:
        self.parse_args: tuple | None = None

    def parse_playwright_script(
        self,
        project_id: int,
        page_id: int,
        script_text: str,
        source_type: str,
        existing_strategy: str,
    ) -> dict:
        self.parse_args = (project_id, page_id, script_text, source_type, existing_strategy)
        return {
            "page_id": page_id,
            "element_count": 1,
            "created_count": 1,
            "updated_count": 0,
            "skipped_count": 0,
            "deduplicated_count": 0,
            "deleted_stale_count": 0,
            "existing_strategy": existing_strategy,
            "elements": [
                {
                    "id": 101,
                    "name": "Add",
                    "data": {
                        "action": "click",
                        "locator_type": "role",
                        "locator": '"button", name="Add"',
                    },
                }
            ],
        }


class FakeRepository:
    def get(self, table: str, item_id: int) -> dict | None:
        if table == "projects" and item_id == 7:
            return {"id": 7, "data": {"base_url": "https://example.test/app"}}
        return None

    def list(
        self,
        table: str,
        keyword: str | None = None,
        project_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        data_filters: dict | None = None,
    ) -> tuple[list[dict], int]:
        if table == "web_elements":
            rows = [
                {
                    "id": 101,
                    "name": "Add",
                    "project_id": project_id,
                    "data": {
                        "page_id": data_filters.get("page_id") if data_filters else 12,
                        "action": "click",
                        "locator_type": "role",
                        "locator": '"button", name="Add"',
                    },
                }
            ]
            return rows, len(rows)
        return [], 0


class AiCodegenWorkflowTest(unittest.TestCase):
    def test_resolves_selected_page_route_against_project_base_url(self) -> None:
        page = {"project_id": 7, "data": {"route": "/users"}}

        target_url = _codegen_target_url(FakeRepository(), page, "/users")

        self.assertEqual(target_url, "https://example.test/app/users")

    def test_records_stops_and_parses_selected_page(self) -> None:
        service = AiGenerationService(FakeRepository())
        recorder = FakeAutoRecorder()
        ui_service = FakeUiService()
        service.auto_recorder = recorder
        service.auth_service = FakeAuthService()
        service.ui_service = ui_service
        service._call_model = lambda model_id, prompt: {
            "operation_steps": [
                {
                    "step_id": 1,
                    "element_name": "Add",
                    "action": "click",
                    "control_index": 1,
                    "purpose": "Open add dialog",
                }
            ],
            "recording_plan": [],
            "element_steps": [],
            "warnings": [],
        }

        payload = WebFunctionElementGenerationRequest(
            project_id=7,
            page_id=12,
            operation_timeout_sec=30,
            headless=False,
            existing_element_strategy="update",
        )
        project = {"id": 7, "data": {"base_url": "https://example.test"}}
        page = {
            "id": 12,
            "name": "Add user",
            "project_id": 7,
            "data": {
                "route": "/users",
                "feature_type": "add",
                "auth_id": 5,
            },
        }

        result = service._record_and_parse_web_page(payload, project, page)

        self.assertEqual(recorder.started["url"], "https://example.test/users")
        self.assertEqual(recorder.started["feature_type"], "add")
        self.assertEqual(recorder.started["cookies"][0]["name"], "sid")
        self.assertTrue(recorder.started["headless"])
        self.assertEqual(ui_service.parse_args[0:2], (7, 12))
        self.assertEqual(ui_service.parse_args[3:], ("ai_auto", "update"))
        self.assertEqual(result["element_count"], 1)
        self.assertEqual(result["automation_session"]["mode"], "ai_auto")
        self.assertTrue(result["automation_session"]["headless"])
        self.assertEqual(result["ai_plan"]["operation_steps"][0]["element_name"], "Add")
        self.assertTrue(result["executed_ai_steps"][0]["executed"])

    def test_query_scan_rejects_unrelated_add_plan_step(self) -> None:
        recorder = PlaywrightAutoRecorder()

        add_step = {"element_name": "新增", "action": "click", "locator": "button, name=新增"}
        query_step = {"element_name": "查询", "action": "click", "locator": "button, name=查询"}
        fill_step = {"element_name": "仓库编码", "action": "fill", "locator": "请选择字段"}

        self.assertFalse(recorder._is_allowed_plan_step_for_feature(add_step, "query"))
        self.assertTrue(recorder._is_allowed_plan_step_for_feature(query_step, "query"))
        self.assertTrue(recorder._is_allowed_plan_step_for_feature(fill_step, "query"))

    def test_plan_control_index_falls_back_when_dynamic_controls_shift(self) -> None:
        recorder = PlaywrightAutoRecorder()
        controls = [
            ControlInfo("button.add-condition", "button", "", "添加条件", "button", "", "", False, True, False),
            ControlInfo("button.add", "button", "", "新增", "button", "", "", False, True, False),
        ]
        step = {
            "element_name": "添加条件按钮",
            "action": "click",
            "control_index": 2,
            "purpose": "采集查询条件扩展入口",
        }

        control = recorder._find_plan_control(controls, step, "query")

        self.assertIsNotNone(control)
        self.assertEqual(control.name, "添加条件")


if __name__ == "__main__":
    unittest.main()
