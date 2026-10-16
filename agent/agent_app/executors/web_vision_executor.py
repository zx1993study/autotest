import asyncio
import base64
import time
from urllib.parse import urlsplit

from web_automation.discovery.browser import (
    DiscoveryBrowserSession,
    close_feature,
    is_login_page,
    open_feature,
)
from web_automation.discovery.target import is_login_url, require_target_page
from web_automation.discovery.dom import collect_dom
from web_automation.pages.base_page import BasePage

from agent_app.auth.web_login_cache import WebLoginCache
from agent_app.runtime.task_cancelled import TaskCancelled
from agent_app.utils.playwright_runtime import chromium_launch_options
from agent_app.windows.task_window import TaskBrowserWindow


class LocalWebVisionExecutor:
    def __init__(self, config, task_api):
        self.config = config
        self.api = task_api

    def execute(self, task_id, lease_token, payload):
        return asyncio.run(self._execute(task_id, lease_token, payload))

    async def _execute(self, task_id, lease_token, payload):
        options = payload["discovery"]
        login_target = is_login_url(payload["target_url"])
        cache = WebLoginCache(self.config, payload)
        cached = cache.load() if not login_target and options.get("reuse_login", True) else {}
        launch = chromium_launch_options(headless=False, slow_mo_ms=0)
        window = TaskBrowserWindow(self.config, self.api, task_id, lease_token, f"AI \u53d1\u73b0 | {payload.get('window_label') or options.get('page_id', '')}")
        try:
            async with DiscoveryBrowserSession(headless=False, launch_options=launch, storage_state=cached.get("storage_state")) as session:
                await window.attach(session.page)
                if not login_target:
                    await cache.restore_session(session.page, cached)
                auth = {} if cached else (payload.get("context") or {}).get("auth_context") or {}
                if login_target:
                    await session.goto(payload["target_url"])
                else:
                    await BasePage(session.page, action_timeout_ms=3000, navigation_timeout_ms=30000).prepare(payload["target_url"], auth)
                await session.page.wait_for_timeout(700)
                if not login_target and options.get("wait_for_login"):
                    await window.set_phase("waiting_login", activate=True)
                    await self._wait_login(session, task_id, lease_token, payload, window)
                if not login_target and await is_login_page(session.page):
                    raise RuntimeError("页面仍在登录页，请启用手动登录并完成验证码后继续")
                require_target_page(payload["target_url"], str(session.page.url))
                if not login_target and options.get("reuse_login", True):
                    await cache.save(session.page)
                await window.set_phase("analyzing")
                image = base64.b64encode(await session.page.screenshot(full_page=True)).decode("ascii")
                require_target_page(payload["target_url"], str(session.page.url))
                response = await self._analysis(session, task_id, lease_token, {"phase": "overview", "page_url": str(session.page.url), "screenshot_base64": image, "dom": await collect_dom(session.page)})
                await window.set_phase("running")
                require_target_page(payload["target_url"], str(session.page.url))
                captures, errors = await self._captures(session, response.get("features") or [], task_id, lease_token)
                await window.set_phase("analyzing")
                result = await self._analysis(session, task_id, lease_token, {"phase": "captures", "captures": captures, "feature_errors": errors})
        finally:
            await window.close()
        return {**result, "records": [], "failed_count": 0}

    async def _analysis(self, session, task_id, lease_token, data):
        response = await asyncio.to_thread(self.api.vision_step, task_id, lease_token, data)
        if not response.get("pending"):
            return response
        while True:
            state = await self._check_state(session, task_id, lease_token)
            job = state.get("analysis") or {}
            if job.get("id") == response["job_id"]:
                if job.get("status") == "success":
                    return job["result"]
                if job.get("status") in {"failed", "canceled"}:
                    raise RuntimeError(job.get("error") or "AI 分析失败")
            await asyncio.sleep(1)

    async def _check_state(self, session, task_id, lease_token):
        if session.page.is_closed():
            await asyncio.to_thread(self.api.vision_cancel, task_id, lease_token)
            raise TaskCancelled("本地浏览器已关闭，发现任务终止")
        state = await asyncio.to_thread(self.api.vision_state, task_id, lease_token)
        if state.get("cancel_requested"):
            raise TaskCancelled("用户已中止 AI 分析")
        return state

    async def _wait_login(self, session, task_id, lease_token, payload, window=None):
        deadline = time.monotonic() + int(payload["discovery"].get("login_timeout_sec") or 600)
        await asyncio.to_thread(self.api.vision_step, task_id, lease_token, {"phase": "waiting_login"})
        while time.monotonic() < deadline:
            if session.page.is_closed():
                raise RuntimeError("本地浏览器已关闭，发现任务终止")
            state = await asyncio.to_thread(self.api.vision_state, task_id, lease_token)
            if state.get("cancel_requested"):
                raise TaskCancelled("用户取消了手动登录")
            if state.get("login_confirmed"):
                await session.goto(payload["target_url"])
                await session.page.wait_for_timeout(700)
                if not await is_login_page(session.page):
                    return
                await asyncio.to_thread(self.api.vision_step, task_id, lease_token, {"phase": "waiting_login", "login_retry": True})
                if window:
                    await window.activate()
            await asyncio.sleep(2)
        raise TimeoutError("手动登录等待超时，请重新执行发现任务")

    async def _captures(self, session, features, task_id=None, lease_token=None):
        captures, errors = [], []
        for index, feature in enumerate(features, 1):
            if task_id is not None:
                await self._check_state(session, task_id, lease_token)
            name = str(feature.get("feature") or "")
            if str(feature.get("risk") or "").lower() == "destructive":
                errors.append({"feature": name, "error": "风险功能已记录候选，请补充目标数据和确认条件后生成脚本"})
                continue
            return_url = str(session.page.url)
            requests = []
            def observe(request):
                location = urlsplit(request.url)
                if request.resource_type in {"xhr", "fetch"} and location.netloc == urlsplit(return_url).netloc and len(requests) < 100:
                    requests.append({"method": request.method, "path": location.path})
            session.page.on("request", observe)
            try:
                if feature.get("capture_mode") != "current_page":
                    await open_feature(session.page, str(feature.get("entry_hint") or name))
                await session.page.wait_for_timeout(700)
                shot = await session.page.screenshot(full_page=False)
                captures.append({"feature_id": f"feature_{index}", "feature_name": name, "screenshot_base64": base64.b64encode(shot).decode("ascii"), "requests": requests, "dom": await collect_dom(session.page)})
            except Exception:  # noqa: BLE001 - one inaccessible feature must not stop discovery.
                errors.append({"feature": name, "error": "功能入口未找到或截图失败"})
            finally:
                session.page.remove_listener("request", observe)
                await close_feature(session.page, return_url)
        return captures, errors
