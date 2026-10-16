from __future__ import annotations

import asyncio
import unittest

from app.core.exceptions import BusinessRuleError
from app.scheduler.jobs.web_case_executor import WebCaseExecutor
from web_automation.engines.pipeline import ActionStrategyPipeline, AiBudget, AiBudgetExceeded
from web_automation.pages.base_page import BasePage


class FakeResourceRepository:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []

    def list(self, table: str, **kwargs: object) -> tuple[list[dict[str, object]], int]:
        return [], 0

    def get(self, table: str, item_id: int) -> dict[str, object] | None:
        return None

    def create(self, table: str, data: dict[str, object]) -> dict[str, object]:
        record = {"id": 99, **data}
        self.created.append(record)
        return record

    def update(self, table: str, item_id: int, data: dict[str, object]) -> dict[str, object] | None:
        return None

    def delete(self, table: str, item_id: int) -> bool:
        return False


class WebEngineConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.executor = WebCaseExecutor(FakeResourceRepository())

    def test_should_default_to_hybrid(self) -> None:
        config = self.executor.web_engine_config({"data": {}}, {})
        self.assertEqual("hybrid", config["engine"])
        self.assertIsNone(config["model_id"])

    def test_should_prefer_request_config(self) -> None:
        case = {"data": {"engine": "hybrid"}}
        payload = {"config": {"engine": "stagehand", "model_id": "7"}}
        config = self.executor.web_engine_config(case, payload)
        self.assertEqual("stagehand", config["engine"])
        self.assertEqual(7, config["model_id"])

    def test_should_reject_unknown_engine(self) -> None:
        with self.assertRaises(BusinessRuleError):
            self.executor.web_engine_config({"data": {}}, {"config": {"engine": "unknown"}})


class ExecuteRecordTest(unittest.TestCase):
    def test_should_record_engine_healing_and_ai_usage(self) -> None:
        repository = FakeResourceRepository()

        class StubExecutor(WebCaseExecutor):
            def _run_async_web_steps(self, case: dict, payload: dict, steps: list) -> dict:
                return {
                    "url": "https://example.test",
                    "step_count": 1,
                    "screenshots": [],
                    "events": [{"event": "step_healed"}],
                    "healing": [{"step_name": "保存", "source": "stagehand"}],
                    "ai_usage": {"llm_calls": 1, "cache_hits": 0, "healed_steps": 1},
                }

        executor = StubExecutor(repository)
        case = {
            "id": 1,
            "name": "新增客户",
            "project_id": 1,
            "steps": [{"name": "保存", "action": "click"}],
        }
        record = executor.execute(case, {"config": {"engine": "hybrid"}})
        self.assertEqual("success", record["status"])
        self.assertEqual("hybrid", record["data"]["engine"])
        self.assertEqual(1, record["data"]["ai_usage"]["llm_calls"])
        self.assertEqual("step_healed", record["data"]["events"][0]["event"])


class BasePageAuthTest(unittest.TestCase):
    def test_should_restore_playwright_local_storage_state(self) -> None:
        class FakeContext:
            def __init__(self) -> None:
                self.scripts: list[str] = []

            async def add_init_script(self, script: str) -> None:
                self.scripts.append(script)

            async def add_cookies(self, cookies: list[dict]) -> None:
                del cookies

        class FakePage:
            def __init__(self) -> None:
                self.context = FakeContext()

        page = FakePage()
        base_page = BasePage(page, action_timeout_ms=5000, navigation_timeout_ms=30000)
        auth_context = {
            "storage_state": {
                "cookies": [],
                "origins": [
                    {
                        "origin": "https://example.test",
                        "localStorage": [{"name": "token", "value": "abc"}],
                    }
                ],
            }
        }

        asyncio.run(base_page._apply_auth(auth_context, "https://example.test/customer"))

        self.assertEqual(1, len(page.context.scripts))
        self.assertIn("localStorage.setItem('token', 'abc')", page.context.scripts[0])


class ActionStrategyPipelineTest(unittest.TestCase):
    def pipeline(
        self,
        *,
        engine: str = "hybrid",
        max_calls: int = 3,
        saved: list[tuple[int, dict]] | None = None,
        invalidated: list[int] | None = None,
    ) -> ActionStrategyPipeline:
        return ActionStrategyPipeline(
            engine=engine,
            budget=AiBudget(max_calls),
            target_url="https://example.test/customer",
            max_healing_time_ms=5000,
            disable_ai_after_429=True,
            save_cache=(lambda element_id, cache: saved.append((element_id, cache))) if saved is not None else None,
            invalidate_cache=invalidated.append if invalidated is not None else None,
        )

    def test_static_success_does_not_call_ai(self) -> None:
        calls = {"static": 0, "ai": 0}

        async def static_action() -> None:
            calls["static"] += 1

        async def ai_action() -> dict:
            calls["ai"] += 1
            return {"selector": "#resolved"}

        outcome = asyncio.run(
            self.pipeline().execute(
                {"name": "保存", "action": "click"},
                static_action=static_action,
                cached_action=lambda selector: static_action(),
                ai_action=ai_action,
            )
        )
        self.assertEqual("playwright", outcome.source)
        self.assertEqual({"static": 1, "ai": 0}, calls)

    def test_cache_hit_skips_static_and_ai(self) -> None:
        calls = {"cache": 0, "static": 0, "ai": 0}
        saved: list[tuple[int, dict]] = []

        async def cached_action(selector: str) -> None:
            self.assertEqual("#cached", selector)
            calls["cache"] += 1

        async def static_action() -> None:
            calls["static"] += 1

        async def ai_action() -> dict:
            calls["ai"] += 1
            return {"selector": "#resolved"}

        outcome = asyncio.run(
            self.pipeline(saved=saved).execute(
                {
                    "name": "保存",
                    "action": "click",
                    "element_id": 5,
                    "ai_cache": {"selector": "#cached", "source": "stagehand"},
                },
                static_action=static_action,
                cached_action=cached_action,
                ai_action=ai_action,
            )
        )
        self.assertEqual("ai_cache", outcome.source)
        self.assertEqual({"cache": 1, "static": 0, "ai": 0}, calls)
        self.assertEqual("#cached", saved[0][1]["selector"])
        self.assertEqual("stagehand", saved[0][1]["source"])
        self.assertEqual("ai_cache", saved[0][1]["last_execution_source"])

    def test_stale_cache_and_static_failure_are_healed_once(self) -> None:
        saved: list[tuple[int, dict]] = []
        invalidated: list[int] = []
        calls = {"ai": 0}

        async def fail() -> None:
            raise RuntimeError("locator stale")

        async def ai_action() -> dict:
            calls["ai"] += 1
            return {"selector": "#new", "method": "click"}

        outcome = asyncio.run(
            self.pipeline(saved=saved, invalidated=invalidated).execute(
                {
                    "name": "保存",
                    "action": "click",
                    "element_id": 5,
                    "locator": "#old",
                    "ai_cache": {"selector": "#cached"},
                },
                static_action=fail,
                cached_action=lambda selector: fail(),
                ai_action=ai_action,
            )
        )
        self.assertTrue(outcome.healed)
        self.assertEqual(1, calls["ai"])
        self.assertEqual([5], invalidated)
        self.assertEqual("#new", saved[0][1]["selector"])
        self.assertEqual("#old", outcome.healing["old_locator"])
        self.assertIn("step_healed", [item["event"] for item in outcome.events])

    def test_stagehand_engine_skips_static_action(self) -> None:
        calls = {"static": 0, "ai": 0}

        async def static_action() -> None:
            calls["static"] += 1

        async def ai_action() -> dict:
            calls["ai"] += 1
            return {"selector": "#new"}

        outcome = asyncio.run(
            self.pipeline(engine="stagehand").execute(
                {"name": "保存", "action": "click"},
                static_action=static_action,
                cached_action=lambda selector: static_action(),
                ai_action=ai_action,
            )
        )
        self.assertEqual("stagehand", outcome.source)
        self.assertEqual({"static": 0, "ai": 1}, calls)

    def test_429_disables_follow_up_ai_calls(self) -> None:
        pipeline = self.pipeline(max_calls=2)

        async def fail_static() -> None:
            raise RuntimeError("missing")

        async def rate_limited() -> dict:
            raise RuntimeError("429 Too Many Requests")

        with self.assertRaisesRegex(RuntimeError, "429"):
            asyncio.run(
                pipeline.execute(
                    {"name": "保存", "action": "click"},
                    static_action=fail_static,
                    cached_action=lambda selector: fail_static(),
                    ai_action=rate_limited,
                )
            )
        with self.assertRaisesRegex(AiBudgetExceeded, "disabled"):
            asyncio.run(
                pipeline.execute(
                    {"name": "删除", "action": "click"},
                    static_action=fail_static,
                    cached_action=lambda selector: fail_static(),
                    ai_action=rate_limited,
                )
            )
        self.assertEqual("step_failed", pipeline.last_events[-1]["event"])
        self.assertEqual("stagehand", pipeline.last_events[-1]["source"])

    def test_textual_rate_limit_error_disables_follow_up_ai_calls(self) -> None:
        pipeline = self.pipeline(max_calls=2)

        async def fail_static() -> None:
            raise RuntimeError("missing")

        async def rate_limited() -> dict:
            raise RuntimeError("RateLimitError: Too Many Requests")

        with self.assertRaisesRegex(RuntimeError, "Too Many Requests"):
            asyncio.run(
                pipeline.execute(
                    {"name": "保存", "action": "click"},
                    static_action=fail_static,
                    cached_action=lambda selector: fail_static(),
                    ai_action=rate_limited,
                )
            )
        with self.assertRaisesRegex(AiBudgetExceeded, "disabled"):
            asyncio.run(
                pipeline.execute(
                    {"name": "删除", "action": "click"},
                    static_action=fail_static,
                    cached_action=lambda selector: fail_static(),
                    ai_action=rate_limited,
                )
            )


if __name__ == "__main__":
    unittest.main()
