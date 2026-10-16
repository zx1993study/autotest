from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from app.schemas.ai import WebVisionDiscoveryRequest
from app.services import web_vision_discovery_service as discovery_module
from app.services.web_vision_discovery_service import WebVisionDiscoveryService
from app.utils.vision_llm_client import VisionLlmClient, VisionModelError


class InMemoryRepository:
    def __init__(self) -> None:
        self.rows: dict[str, list[dict[str, Any]]] = {
            "web_pages": [
                {
                    "id": 10,
                    "name": "客户管理",
                    "project_id": 1,
                    "status": "active",
                    "data": {"url": "https://example.test/customer"},
                }
            ],
            "web_elements": [],
            "projects": [{"id": 1, "name": "demo", "status": "active", "data": {"base_url": "https://example.test"}}],
            "ai_prompt_templates": [],
            "ai_generation_tasks": [],
            "system_dictionaries": [],
        }
        self.next_id = 1000

    def list(self, table: str, keyword=None, project_id=None, page=1, page_size=20, data_filters=None):
        rows = [dict(row) for row in self.rows.get(table, [])]
        if project_id is not None:
            rows = [row for row in rows if row.get("project_id") == project_id]
        for key, value in (data_filters or {}).items():
            rows = [row for row in rows if (row.get("data") or {}).get(key) == value]
        start = (page - 1) * page_size
        return rows[start : start + page_size], len(rows)

    def get(self, table: str, item_id: int):
        return next((row for row in self.rows.get(table, []) if row.get("id") == item_id), None)

    def create(self, table: str, data: dict[str, Any]):
        self.next_id += 1
        row = {"id": self.next_id, "status": data.get("status", "active"), **data}
        self.rows.setdefault(table, []).append(row)
        return row

    def create_many(self, table: str, rows: list[dict[str, Any]]):
        return [self.create(table, row) for row in rows]

    def update(self, table: str, item_id: int, data: dict[str, Any]):
        row = self.get(table, item_id)
        if row is None:
            return None
        row.update(data)
        if "data" in data and row.get("data") is not data["data"]:
            merged = dict(row.get("data") or {})
            merged.update(data.get("data") or {})
            row["data"] = merged
        return row

    def delete(self, table: str, item_id: int) -> bool:
        rows = self.rows.get(table, [])
        before = len(rows)
        self.rows[table] = [row for row in rows if row.get("id") != item_id]
        return len(self.rows[table]) != before

    def update_many(self, table, rows):
        return [self.update(table, item_id, data) for item_id, data in rows]

    def batch_delete(self, table: str, ids: list[int]) -> int:
        return sum(1 for item_id in ids if self.delete(table, item_id))

    def delete_by_project(self, table: str, project_id: int) -> int:
        return 0


class FakePage:
    def __init__(self) -> None:
        self.keyboard = self
        self.context = self
        self.url = "https://example.test/customer"

    def set_default_timeout(self, value: int) -> None:
        pass

    async def wait_for_timeout(self, value: int) -> None:
        pass

    async def press(self, key: str) -> None:
        pass

    def get_by_text(self, text: str, exact: bool = False):
        async def count():
            return 1
        return SimpleNamespace(count=count, click=self.click)

    @property
    def first(self) -> "FakePage":
        return self

    async def click(self, timeout: int | None = None) -> None:
        pass

    def locator(self, selector: str) -> "FakePage":
        return self

    async def count(self) -> int:
        return 0


class FakeStagehandSession:
    instances: list["FakeStagehandSession"] = []

    def __init__(self, *, headless: bool = True, viewport: dict | None = None) -> None:
        self.page = FakePage()
        self.goto_url = ""
        self.screenshot_modes: list[bool] = []
        FakeStagehandSession.instances.append(self)

    async def __aenter__(self) -> "FakeStagehandSession":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    async def goto(self, url: str, timeout_ms: int) -> None:
        self.goto_url = url
        self.page.url = url

    async def screenshot(self, path: str, *, full_page: bool = True) -> None:
        self.screenshot_modes.append(full_page)
        Path(path).write_bytes(b"fake-png-bytes")

    async def act(self, instruction: str) -> None:
        pass

    async def act_with_observe_cache(self, instruction: str):
        raise AssertionError("文本定位成功时不应回退到 Stagehand")


class FakeVisionClient:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = list(responses)
        self.calls = 0
        self.image_counts: list[int] = []

    def complete_json(self, system_prompt: str, user_prompt: str, images: list[bytes], **kwargs: Any) -> Any:
        self.calls += 1
        self.image_counts.append(len(images))
        return self.responses.pop(0)


class DiscoveryFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryRepository()
        self.service = WebVisionDiscoveryService(self.repository)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        FakeStagehandSession.instances = []
        self.client = FakeVisionClient(
            [
                {"features": [{"feature": "新增", "entry_hint": "新增", "risk": "safe"}], "warnings": []},
                {
                    "features": [
                        {
                            "feature_id": "feature_1",
                            "feature": "新增",
                            "elements": [
                                {
                                    "name": "客户名称",
                                    "element_type": "input",
                                    "action": "fill",
                                    "description": "弹窗第一行输入框",
                                    "required": True,
                                    "default_value": "测试客户",
                                }
                            ],
                        }
                    ]
                },
            ]
        )
        self.service._vision_client = lambda *args, **kwargs: self.client

    def run_discovery(self, **overrides: Any) -> dict[str, Any]:
        payload = WebVisionDiscoveryRequest(project_id=1, page_id=10, **overrides)
        with (
            patch.object(discovery_module, "DiscoveryBrowserSession", FakeStagehandSession),
            patch.object(discovery_module, "DISCOVERY_SCREENSHOT_DIR", Path(self.tmp_dir.name)),
        ):
            return self.service.discover(payload)

    def test_should_discover_features_and_save_elements(self) -> None:
        result = self.run_discovery()
        self.assertEqual(["新增"], result["features"])
        self.assertEqual(2, result["saved_elements"])

        elements = self.repository.rows["web_elements"]
        names = {row["name"] for row in elements}
        self.assertIn("新增", names)
        self.assertIn("客户名称", names)
        entry = next(row for row in elements if row["name"] == "新增")
        self.assertEqual("text", entry["data"]["locator_type"])
        field = next(row for row in elements if row["name"] == "客户名称")
        self.assertEqual("vision_discovery", field["data"]["source"])
        self.assertEqual("新增", field["data"]["feature"])

        page = self.repository.get("web_pages", 10)
        self.assertEqual("新增", page["data"]["features"][0]["feature"])
        self.assertEqual("https://example.test/customer", FakeStagehandSession.instances[0].goto_url)
        self.assertEqual(2, self.client.calls)
        self.assertEqual([1, 1], self.client.image_counts)
        self.assertEqual(2, result["vision_batches"])
        self.assertEqual([True, False], FakeStagehandSession.instances[0].screenshot_modes)

    def test_dry_run_should_not_persist_anything(self) -> None:
        result = self.run_discovery(dry_run=True)
        self.assertEqual(2, result["saved_elements"])
        self.assertEqual([], self.repository.rows["web_elements"])
        self.assertNotIn("features", self.repository.get("web_pages", 10)["data"])

    def test_login_target_captures_form_without_auth_or_submit(self):
        self.repository.get('web_pages', 10)['data']['url'] = 'https://example.test/login'
        with patch.object(self.service, '_load_auth') as auth, patch.object(self.service, '_open_feature_entry') as click:
            result = self.run_discovery(dry_run=True)
        auth.assert_not_called()
        click.assert_not_called()
        self.assertEqual(result['features'], ['登录'])
        self.assertIsNone(self.client.timeout_sec)

    def test_redirect_stops_before_model(self):
        async def redirected(session, url, timeout_ms):
            session.page.url = 'https://example.test/home'

        with patch.object(FakeStagehandSession, 'goto', redirected), self.assertRaises(RuntimeError):
            self.run_discovery(dry_run=True)
        self.assertEqual(self.client.calls, 0)

    def test_should_skip_destructive_features_by_default(self) -> None:
        self.client.responses[0] = {
            "features": [
                {"feature": "删除", "entry_hint": "删除", "risk": "destructive"},
                {"feature": "查询", "entry_hint": "查询", "risk": "safe"},
            ]
        }
        result = self.run_discovery()
        self.assertEqual(["查询"], result["features"])

    def test_should_only_call_vision_once_when_no_feature_is_found(self) -> None:
        self.client.responses[0] = {"features": [], "warnings": ["页面功能折叠在更多菜单中"]}

        result = self.run_discovery(dry_run=True)

        self.assertEqual([], result["features"])
        self.assertEqual(1, result["vision_batches"])
        self.assertEqual(1, self.client.calls)
        self.assertEqual([1], self.client.image_counts)
        self.assertIn("页面功能折叠在更多菜单中", result["warnings"])

    def test_should_cap_features_by_max_functions(self) -> None:
        self.client.responses[0] = {
            "features": [
                {"feature": "新增", "entry_hint": "新增", "risk": "safe"},
                {"feature": "编辑", "entry_hint": "编辑", "risk": "safe"},
                {"feature": "导出", "entry_hint": "导出", "risk": "safe"},
            ]
        }
        result = self.run_discovery(max_functions=2)
        self.assertEqual(["新增", "编辑"], result["features"])

    def test_should_extract_multiple_features_in_one_vision_batch(self) -> None:
        self.client.responses[0] = {
            "features": [
                {"feature": "新增", "entry_hint": "新增", "risk": "safe"},
                {"feature": "编辑", "entry_hint": "编辑", "risk": "safe"},
            ]
        }
        self.client.responses[1] = {
            "features": [
                {"feature_id": "feature_1", "feature": "新增", "elements": []},
                {"feature_id": "feature_2", "feature": "编辑", "elements": []},
            ]
        }

        result = self.run_discovery(dry_run=True)

        self.assertEqual(["新增", "编辑"], result["features"])
        self.assertEqual(2, self.client.calls)
        self.assertEqual([1, 2], self.client.image_counts)
        self.assertEqual(2, result["vision_batches"])
        self.assertEqual(2, result["saved_elements"])
        self.assertEqual([True, False, False], FakeStagehandSession.instances[0].screenshot_modes)

    def test_should_accept_legacy_single_feature_element_response(self) -> None:
        self.client.responses[1] = {
            "elements": [
                {
                    "name": "备注",
                    "element_type": "textarea",
                    "action": "fill",
                    "description": "弹窗中的备注输入框",
                }
            ]
        }

        result = self.run_discovery(dry_run=True)

        self.assertEqual(2, result["saved_elements"])
        self.assertEqual(2, self.client.calls)


class VisionClientHttpTest(unittest.TestCase):
    def test_should_send_images_as_data_urls(self) -> None:
        client = VisionLlmClient(base_url="https://api.example.test/v1", api_key="k", model="vision-model")
        captured: dict[str, Any] = {}

        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: Any) -> None:
                pass

            def read(self, size: int = -1) -> bytes:
                return json.dumps({"choices": [{"message": {"content": '{"features": []}'}}]}).encode("utf-8")

        def fake_urlopen(req: Any, timeout: int = 0) -> FakeResponse:
            captured["body"] = json.loads(req.data.decode("utf-8"))
            captured["url"] = req.full_url
            return FakeResponse()

        with patch("app.utils.vision_llm_client.request.urlopen", fake_urlopen):
            result = client.complete_json("sys", "看图", [b"png-bytes"])
        self.assertEqual({"features": []}, result)
        message = captured["body"]["messages"][1]["content"]
        self.assertEqual("text", message[0]["type"])
        self.assertTrue(message[1]["image_url"]["url"].startswith("data:image/png;base64,"))
        self.assertEqual("https://api.example.test/v1/chat/completions", captured["url"])

    def test_should_raise_clear_error_on_html_response(self) -> None:
        client = VisionLlmClient(base_url="https://api.example.test/v1", api_key="k", model="m")

        class HtmlResponse:
            def __enter__(self) -> "HtmlResponse":
                return self

            def __exit__(self, *args: Any) -> None:
                pass

            def read(self, size: int = -1) -> bytes:
                return b"<!doctype html><html></html>"

        with patch("app.utils.vision_llm_client.request.urlopen", lambda *a, **k: HtmlResponse()):
            with self.assertRaises(VisionModelError):
                client.complete_json("sys", "看图", [b"png"])


if __name__ == "__main__":
    unittest.main()
