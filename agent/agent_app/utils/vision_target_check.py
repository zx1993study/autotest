"""Isolated smoke test for login-page capture and discovery cancellation."""
import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from web_automation.discovery.browser import DiscoveryBrowserSession

from agent_app.executors.web_vision_executor import LocalWebVisionExecutor
from agent_app.runtime.task_cancelled import TaskCancelled
from agent_app.utils.playwright_runtime import chromium_launch_options


async def run():
    visited = []
    base = "https://discovery-fixture.invalid"

    class FixtureSession(DiscoveryBrowserSession):
        async def __aenter__(self):
            await super().__aenter__()
            async def respond(route):
                visited.append(route.request.url)
                html = '''<h1>Login fixture</h1><label>Account<input></label><input type="password">
                <button onclick="location.href='/home'">Login</button>
                <script>if(localStorage.token || sessionStorage.token) location.href='/home';
                if(location.pathname === '/redirect') location.href='/home';</script>'''
                if not route.request.url.endswith('/login'):
                    html = "<h1>Business fixture</h1><script>if(location.pathname === '/redirect') location.href='/home';</script>"
                await route.fulfill(content_type="text/html", body=html)
            await self.page.route(base + "/**", respond)
            return self

    options = chromium_launch_options(headless=True, slow_mo_ms=0)
    if "executable_path" not in options:
        options["channel"] = "chrome"
    with tempfile.TemporaryDirectory() as tmp:
        config = SimpleNamespace(server_url=base, node_key="fixture", artifacts_dir=Path(tmp))
        api = Mock()
        api.vision_state.return_value = {}
        def step(task_id, lease, data):
            if data["phase"] == "overview":
                assert data["page_url"] == base + "/login"
                return {"features": [{"feature": "Login", "capture_mode": "current_page"}]}
            assert data["phase"] == "captures" and len(data["captures"]) == 1
            assert len(data["captures"][0]["screenshot_base64"]) > 1000
            return {"saved_elements": 2}
        api.vision_step.side_effect = step
        window = SimpleNamespace(attach=AsyncMock(), close=AsyncMock(), set_phase=AsyncMock())
        payload = {"target_url": base + "/login", "discovery": {"project_id": 1, "wait_for_login": True, "reuse_login": True}, "context": {"auth_context": {"local_storage": {"token": "synthetic"}}}}
        with patch("agent_app.executors.web_vision_executor.DiscoveryBrowserSession", FixtureSession), patch("agent_app.executors.web_vision_executor.chromium_launch_options", return_value=options), patch("agent_app.executors.web_vision_executor.TaskBrowserWindow", return_value=window), patch("agent_app.executors.web_vision_executor.WebLoginCache") as cache:
            cache.return_value.restore_session = AsyncMock()
            cache.return_value.save = AsyncMock()
            executor = LocalWebVisionExecutor(config, api)
            result = await executor._execute(1, "fixture", payload)
            assert result["saved_elements"] == 2 and base + "/home" not in visited
            cache.return_value.load.assert_not_called()
            cache.return_value.save.assert_not_called()
            cache.return_value.restore_session.assert_not_called()
            assert all(call.args[2]["phase"] != "waiting_login" for call in api.vision_step.call_args_list)
            api.vision_step.reset_mock()
            try:
                await executor._execute(2, "fixture", {**payload, "target_url": base + "/redirect", "discovery": {"reuse_login": False}})
            except RuntimeError as exc:
                assert "跳转" in str(exc)
            else:
                raise AssertionError("Redirected page was analyzed")
            api.vision_step.assert_not_called()
            api.vision_step.side_effect = None
            api.vision_step.return_value = {"pending": True, "job_id": "blocked"}
            api.vision_state.return_value = {"cancel_requested": True}
            try:
                await executor._execute(3, "fixture", payload)
            except TaskCancelled:
                pass
            else:
                raise AssertionError("Canceled analysis kept running")
            assert window.close.await_count == 3


def check():
    asyncio.run(run())
    print("Login page isolated from auth/cache; no submit; redirect guard and cancellation: OK")
