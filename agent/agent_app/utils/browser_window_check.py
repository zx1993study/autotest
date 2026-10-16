"""Local synthetic browser fixture for source and frozen window controls."""
import asyncio
import ctypes
import json
import tempfile
from ctypes import wintypes
from pathlib import Path
from types import SimpleNamespace

from agent_app.utils.playwright_runtime import chromium_launch_options
from agent_app.windows.local_control import request_local_show
from agent_app.windows.task_window import TaskBrowserWindow


class CheckApi:
    def __init__(self):
        self.states = []
        self.command = None

    def browser_window_exchange(self, task_id, lease_token, window):
        self.states.append(dict(window))
        if self.command and window['command_id'] == self.command['id']:
            self.command = None
        return {'command': self.command}


async def run():
    from playwright.async_api import async_playwright

    from agent_app.windows.native import Win32

    api = CheckApi()
    with tempfile.TemporaryDirectory() as directory:
        config = SimpleNamespace(server_url='https://window-check.invalid', node_key='window-check', artifacts_dir=Path(directory))
        async with async_playwright() as pw:
            options = chromium_launch_options(headless=False, slow_mo_ms=0)
            if 'executable_path' not in options:
                options['channel'] = 'chrome'
            unrelated = await pw.chromium.launch(**options)
            unrelated_page = await unrelated.new_page()
            await unrelated_page.set_content('<h1>Unrelated fixture window</h1>')
            window = TaskBrowserWindow(config, api, 700001, 'synthetic', 'Browser window check')
            browser = await pw.chromium.launch(**options)
            page = await browser.new_page()
            try:
                await page.set_content('<h1>Window fixture</h1><p>Ready</p>')
                await window.attach(page)
                assert window.state()['status'] == 'open', window.state()
                assert window.native.binding[:2] not in window.native.before
                native = Win32()
                native.user.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
                native.user.GetWindowLongW.restype = wintypes.LONG
                assert window.native.strip, 'Native task strip not created'
                assert not native.user.GetWindowLongW(window.native.strip, -20) & 8, 'Strip must not be topmost'
                assert native.user.GetWindow(window.native.strip, 4) == window.native.binding[0]
                await window.set_phase('waiting_login', activate=True)
                api.command = {'id': 'fixture-command', 'window_id': window.window_id, 'action': 'show'}
                for _ in range(40):
                    await asyncio.sleep(.2)
                    if any(s['command_id'] == 'fixture-command' for s in api.states):
                        break
                assert any(s['command_id'] == 'fixture-command' and s['focus'] in {'active', 'blocked'} for s in api.states), api.states
                native.user.ShowWindow(window.native.binding[0], 6)
                request_local_show(config)
                await asyncio.sleep(2)
                assert not native.user.IsIconic(window.native.binding[0]), 'Tray request did not restore minimized window'
                await page.screenshot(path=str(config.artifacts_dir / 'fixture.png'))
                await window.close()
                assert window.native.strip is None
                assert not unrelated_page.is_closed()
                return {'passed': True, 'browser': window.state()['browser_name'], 'activation': window.focus,
                        'owned_non_topmost_strip': True, 'remote_show_ack': True, 'tray_restore': True, 'unrelated_window_untouched': True}
            finally:
                await window.close()
                await browser.close()
                await unrelated.close()


def check():
    print(json.dumps(asyncio.run(run())))
