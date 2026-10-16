import asyncio
import base64
import json
import time
from urllib.parse import urlsplit

from web_automation.discovery.dom import collect_dom
from web_automation.discovery.recording import RECORDING_SCRIPT, recording_candidate
from web_automation.engines.playwright import PlaywrightEngine

from agent_app.executors.result_builder import summarize_records
from agent_app.runtime.task_cancelled import TaskCancelled
from agent_app.utils.playwright_runtime import chromium_launch_options
from agent_app.windows.task_window import TaskBrowserWindow


class LocalWebRecordingExecutor:
    def __init__(self, config, api):
        self.config, self.api = config, api

    def execute(self, task_id, lease, payload):
        return asyncio.run(self._run(task_id, lease, payload))

    async def _run(self, task_id, lease, payload):
        from playwright.async_api import async_playwright

        events, shots = [], []
        window = TaskBrowserWindow(self.config, self.api, task_id, lease, f"录制 | {payload['name']}")
        target = urlsplit(payload['target_url']).netloc
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(**chromium_launch_options(headless=False, slow_mo_ms=0))
            context = await browser.new_context(viewport={'width': 1366, 'height': 900})
            async def observe(source, event):
                if urlsplit(source['frame'].url).netloc != target:
                    return
                if not isinstance(event, dict) or len(json.dumps(event)) > 20000:
                    event = {'error':'录制事件格式或大小无效'}
                if source['frame'] != source['page'].main_frame:
                    event = {'sequence': len(events) + 1, 'error': 'iframe 操作请使用 AI 实采 DOM 生成或手动补充定位'}
                if len(events) >= 60:
                    if len(events) == 60:
                        events.append({'sequence': 61, 'error': '录制超过 60 步，未保存完整脚本'})
                    return
                event['sequence'] = len(events) + 1
                events.append(event)
            try:
                await context.expose_binding('autotestRecord', observe)
                await context.add_init_script(RECORDING_SCRIPT)
                page = await context.new_page()
                await window.attach(page)
                await page.goto(payload['target_url'], wait_until='domcontentloaded')
                await window.set_phase('recording', activate=True)
                shots.append(await self._shot(page, task_id))
                while True:
                    if page.is_closed():
                        raise TaskCancelled('录制窗口已关闭，未保存')
                    state = await asyncio.to_thread(self.api.web_state, task_id, lease)
                    if state.get('cancel_requested'):
                        raise TaskCancelled('已取消录制')
                    if state.get('recording_stop'):
                        break
                    await asyncio.sleep(1)
                # Blur the focused editor so its final change event is captured.
                await page.evaluate('document.activeElement?.blur()')
                await asyncio.sleep(0.3)
                shots.append(await self._shot(page, task_id))
            finally:
                await window.close()
                await context.close()
                await browser.close()
        candidate, errors = recording_candidate(events, payload['name'])
        if not candidate['steps']:
            errors.append('未录制到可回放操作')
        record = {'name': f"操作录制 - {payload['name']}", 'project_id': payload['project_id'], 'status': 'failed' if errors else 'success',
                  'data': {'case_type': 'WEB', 'source_id': payload['source_id'], 'candidate': candidate, 'screenshots': shots,
                           'step_count': len(candidate['steps']), 'warnings': errors, 'business_result': 'not_configured'}}
        return summarize_records([record])

    async def _shot(self, page, task_id):
        private = page.locator('input[type=password], input[name*=captcha i], input[placeholder*=验证码]')
        masks = [private] + [PlaywrightEngine(page)._strict_locator({**c['locators'][0], 'frame_selector':c['frame_selector']}) for c in await collect_dom(page) if c['sensitive'] and c['locators']]
        raw = await page.screenshot(full_page=True, mask=masks)
        return {'screenshot_file': f'recording-{task_id}-{time.time_ns()}.png', 'screenshot_base64': base64.b64encode(raw).decode('ascii')}
