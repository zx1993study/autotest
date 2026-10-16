from __future__ import annotations

import base64
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.scheduler.jobs import app_case_executor as executor_module
from app.scheduler.jobs.app_case_executor import AppCaseExecutor
from app.services.app_scenario_generation_service import AppScenarioGenerationService
from app.utils.appium_executor import AppiumActionExecutor


class FakeResourceRepository:
    def __init__(self) -> None:
        self.created: list[tuple[str, dict[str, object]]] = []
        self.rows: dict[str, list[dict[str, object]]] = {
            "projects": [{"id": 1, "name": "外勤小星", "data": {}}],
            "app_entries": [{"id": 3, "name": "外勤小星 App", "project_id": 1, "data": {"entry_type": "current_app", "platform": "iOS"}}],
            "app_features": [{"id": 5, "name": "考勤", "project_id": 1, "data": {"platforms": ["iOS"], "default_entry_id": 3}}],
            "app_feature_scenarios": [],
            "app_devices": [],
            "project_knowledge": [
                {
                    "id": 9,
                    "name": "打卡成功断言",
                    "project_id": 1,
                    "status": "active",
                    "data": {
                        "domain": "APP",
                        "kind": "business_rule",
                        "knowledge_key": "app.attendance.success_assert",
                        "priority": "P1",
                        "content": "打卡完成后必须校验打卡成功文案。",
                    },
                }
            ],
        }

    def get(self, table: str, item_id: int) -> dict[str, object] | None:
        for row in self.rows.get(table, []):
            if row.get("id") == item_id:
                return row
        return None

    def list(
        self,
        table: str,
        keyword: str | None = None,
        project_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        data_filters: dict[str, object] | None = None,
    ) -> tuple[list[dict[str, object]], int]:
        del keyword, page, page_size, data_filters
        rows = self.rows.get(table, [])
        if project_id is not None:
            rows = [row for row in rows if row.get("project_id") in {project_id, None}]
        return rows, len(rows)

    def create(self, table: str, data: dict[str, object]) -> dict[str, object]:
        row = {"id": 100 + len(self.created), **data}
        self.created.append((table, row))
        return row

    def update(self, table: str, item_id: int, data: dict[str, object]) -> dict[str, object] | None:
        return {"id": item_id, **data}

    def delete(self, table: str, item_id: int) -> bool:
        return False


class AppScenarioGenerationServiceTest(unittest.TestCase):
    def test_generate_from_text_creates_feature_scenario_json(self) -> None:
        repository = FakeResourceRepository()
        service = AppScenarioGenerationService(repository)

        result = service.generate_from_text(
            {
                "project_id": 1,
                "prompt": "进入考勤页面，然后点击打卡，然后校验打卡成功",
                "entry_id": 3,
                "feature_id": 5,
                "record_video": True,
            }
        )

        self.assertEqual([], repository.created)
        self.assertNotIn("draft", result)
        case_json = result["case_json"]
        self.assertEqual("APP", case_json["case_type"])
        self.assertTrue(case_json["record_video"])
        self.assertEqual(3, case_json["entry_id"])
        self.assertEqual(5, case_json["feature_id"])
        self.assertGreaterEqual(len(case_json["steps"]), 3)
        self.assertEqual("tap", case_json["steps"][0]["action"])
        self.assertEqual("assert_text", case_json["steps"][-1]["action"])
        self.assertGreater(result["validation"]["confidence_score"], 0)
        self.assertEqual("rule", result["generation_mode"])
        self.assertEqual(1, len(result["context"]["knowledge"]))

    def test_generate_from_events_keeps_coordinate_fallback(self) -> None:
        service = AppScenarioGenerationService(FakeResourceRepository())

        result = service.generate_from_events(
            {
                "project_id": 1,
                "name": "录制打卡",
                "save_draft": False,
                "events": [
                    {"type": "tap", "x_pct": 0.5, "y_pct": 0.8, "timestamp_ms": 120},
                    {"type": "input", "locator": "备注", "value": "测试"},
                ],
            }
        )

        steps = result["case_json"]["steps"]
        self.assertEqual(0.5, steps[0]["x_pct"])
        self.assertEqual("input", steps[1]["action"])
        self.assertEqual(1, result["validation"]["coordinate_steps"])


class FakeTapDriver:
    def __init__(self) -> None:
        self.taps: list[list[tuple[int, int]]] = []

    def get_window_size(self) -> dict[str, int]:
        return {"width": 1000, "height": 2000}

    def tap(self, points: list[tuple[int, int]]) -> None:
        self.taps.append(points)


class FakeRecordingDriver:
    def __init__(self) -> None:
        self.started = False

    def start_recording_screen(self) -> None:
        self.started = True

    def stop_recording_screen(self) -> str:
        return base64.b64encode(b"mp4-bytes").decode("ascii")


class AppScenarioExecutionSupportTest(unittest.TestCase):
    def test_tap_uses_percent_coordinates_as_fallback(self) -> None:
        driver = FakeTapDriver()
        executor = AppiumActionExecutor(driver)

        executor.run_step({"action": "tap", "x_pct": 0.25, "y_pct": 0.75})

        self.assertEqual([[(250, 1500)]], driver.taps)

    def test_screen_recording_is_saved_to_file(self) -> None:
        executor = AppCaseExecutor(FakeResourceRepository())
        driver = FakeRecordingDriver()

        with TemporaryDirectory() as tmp:
            with patch.object(executor_module, "RECORDING_DIR", Path(tmp)):
                state = executor._start_screen_recording(driver, {"record_video": True})
                result = executor._stop_screen_recording(driver, {"id": 12, "name": "打卡"}, state)

            self.assertTrue(driver.started)
            self.assertTrue(result["video_file"].endswith(".mp4"))
            self.assertEqual(b"mp4-bytes", (Path(tmp) / result["video_file"]).read_bytes())
            self.assertEqual(f"/api/v1/app-recordings/{result['video_file']}", result["video_url"])

    def test_python_script_case_executes_with_input_arguments(self) -> None:
        executor = AppCaseExecutor(FakeResourceRepository())

        with TemporaryDirectory() as tmp:
            script = Path(tmp) / "demo_script.py"
            script.write_text(
                "import argparse\n"
                "parser=argparse.ArgumentParser()\n"
                "parser.add_argument('--wda-url')\n"
                "parser.add_argument('--bundle-id')\n"
                "parser.add_argument('--customer-name')\n"
                "args=parser.parse_args()\n"
                "print(f'{args.bundle_id}|{args.wda_url}|{args.customer_name}')\n",
                encoding="utf-8",
            )
            result = executor.execute(
                {
                    "id": 88,
                    "name": "脚本执行",
                    "project_id": 1,
                    "data": {
                        "execution_mode": "python_script",
                        "script_path": str(script),
                        "script_python": sys.executable,
                        "script_arg_map": {"customer_name": "--customer-name"},
                        "input_info": {"customer_name": {"value": "AutoCustomer"}},
                        "bundle_id": "cn.yios.fieldwork",
                        "wda_url": "http://192.168.50.184:8100",
                    },
                    "steps": [],
                    "assertions": [],
                },
                {"project_id": 1, "mode": "python_script", "config": {}},
            )

        data = result["data"]
        self.assertEqual("success", result["status"])
        self.assertEqual(1, data["step_count"])
        self.assertIn("cn.yios.fieldwork|http://192.168.50.184:8100|AutoCustomer", data["step_timeline"][0]["stdout"])


if __name__ == "__main__":
    unittest.main()
