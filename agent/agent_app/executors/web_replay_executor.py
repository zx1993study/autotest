import asyncio
import base64
import time
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse

from web_automation.dynamic_values import DynamicValueContext
from web_automation.engines.playwright import PlaywrightEngine

from agent_app.executors.result_builder import summarize_records
from agent_app.utils.playwright_runtime import (
    chromium_launch_options,
    prepare_recording_runtime,
)
from agent_app.windows.task_window import TaskBrowserWindow
from agent_app.executors.web_manual_input import wait_manual_input, outcome_metadata
from agent_app.runtime.task_cancelled import TaskCancelled
from agent_app.executors.web_secret_redaction import redact_record


class LocalWebReplayExecutor:
    def __init__(self, config, task_api):
        self.config = config
        self.task_api = task_api

    def execute(self, task_id, lease_token, payload):
        return asyncio.run(self._run(task_id, lease_token, payload))

    async def _state(self, task_id, lease_token, phase="state"):
        return await asyncio.to_thread(self.task_api.client.post, f"/agent/runtime/tasks/{task_id}/replay/state", {
            "node_key": self.config.node_key, "lease_token": lease_token, "phase": phase,
        })

    async def _run(self, task_id, lease_token, payload):
        from playwright.async_api import async_playwright

        prepare_recording_runtime()

        candidate = payload["candidate"]
        steps = deepcopy(candidate["steps"])
        secure = payload.get('runtime_inputs') or {}
        dynamic = DynamicValueContext({**candidate.get("variables", {}), **candidate.get("input_info", {}), **{k:v.replace('{{', r'\{{') for k,v in secure.items()}})
        root = self.config.artifacts_dir / "web-replay" / str(task_id)
        root.mkdir(parents=True, exist_ok=True)
        screenshots, timeline = [], []
        started, status, error = time.monotonic(), "success", None
        video_path = None
        window = TaskBrowserWindow(self.config, self.task_api, task_id, lease_token, candidate['name'])
        private = payload.get('wait_for_login') or any(s.get('action') == 'manual' or s.get('sensitive') for s in steps)
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(**chromium_launch_options(headless=False, slow_mo_ms=80))
            context = await browser.new_context(**({'record_video_dir': str(root)} if not private else {}), viewport={"width": 1366, "height": 900})
            page = await context.new_page()
            try:
                await window.attach(page)
                await page.goto(payload["target_url"], wait_until="domcontentloaded", timeout=30000)
                if payload.get("wait_for_login"):
                    await window.set_phase("waiting_login", activate=True)
                    await self._login(task_id, lease_token)
                    await page.goto(payload['target_url'], wait_until='domcontentloaded', timeout=30000)
                await window.set_phase("running")
                await self._state(task_id, lease_token, "running")
                engine = PlaywrightEngine(page, default_timeout=10000)
                for index, original in enumerate(steps, 1):
                    if urlparse(page.url).netloc != urlparse(payload["target_url"]).netloc:
                        raise RuntimeError("当前页面不在目标站点，停止操作")
                    if (await self._state(task_id, lease_token)).get("cancel_requested"):
                        raise RuntimeError("用户取消验证")
                    step = dynamic.resolve(original)
                    step["require_unique"] = True
                    try:
                        if step.get('action') == 'manual':
                            await wait_manual_input(page, step, (self.config, self.task_api, task_id, lease_token), window, index)
                        else:
                            await engine.execute(step)
                        timeline.append({"step": index, "name": original.get("name"), "status": "success"})
                    except Exception:
                        timeline.append({"step": index, "name": original.get("name"), "status": "failed"})
                        raise
                    if not private:
                        screenshots.append(await self._capture(page, root, index))
                if urlparse(page.url).netloc != urlparse(payload["target_url"]).netloc:
                    raise RuntimeError("验证跳转到了目标站点以外")
            except TaskCancelled:
                raise
            except Exception as exc:  # noqa: BLE001 - report failure evidence, never silently retry actions.
                status, error = "failed", str(exc)
                if not private:
                    screenshots.append(await self._capture(page, root, len(timeline)))
            finally:
                await window.close()
                await context.close()
                if page.video:
                    video_path = await page.video.path()
                await browser.close()
        record = {
            "name": f"Web 复现验证 - {candidate['name']}", "project_id": payload["project_id"], "status": status,
            "data": {"case_type": "WEB", "generation_task_id": payload["generation_task_id"], "engine": "playwright",
                     "step_count": sum(s["status"] == "success" for s in timeline), "steps": steps, "step_timeline": timeline,
                     "screenshots": screenshots, "duration_ms": int((time.monotonic() - started) * 1000), "error": error},
        }
        if video_path:
            record["data"]["video_local_path"] = str(video_path)
        record['data'].update(outcome_metadata(steps, sum(s['status'] == 'success' for s in timeline), status))
        if private:
            record['data']['privacy_notice'] = '包含人工登录或敏感输入，已关闭录屏和步骤截图'
        if secure:
            original = payload['cases'][0]
            record = redact_record(record, {**original, 'data':{**original['data'], 'variables':secure}})
        return summarize_records([record])

    async def _login(self, task_id, lease_token):
        await self._state(task_id, lease_token, "waiting_login")
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            state = await self._state(task_id, lease_token)
            if state.get("cancel_requested"):
                raise RuntimeError("用户取消验证")
            if state.get("login_confirmed"):
                return
            await asyncio.sleep(1)
        raise RuntimeError("等待人工登录超时")

    async def _capture(self, page, root: Path, index):
        path = root / f"step-{index}-{time.time_ns()}.png"
        try:
            await page.screenshot(path=str(path), full_page=True)
            return {"step_order": index, "screenshot_file": path.name, "screenshot_base64": base64.b64encode(path.read_bytes()).decode("ascii")}
        except Exception:  # noqa: BLE001 - a screenshot failure must not erase execution failure evidence.
            return {"step_order": index, "screenshot_error": "截图失败"}
