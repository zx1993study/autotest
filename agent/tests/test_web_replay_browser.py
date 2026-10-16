import os
import tempfile
import threading
import unittest
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from agent_app.executors.web_replay_executor import LocalWebReplayExecutor


class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        content = b'<html><body><label>Name<input id="name"></label><button onclick="document.querySelector(\"p\").textContent=\"Ready\"">Save</button><p>Waiting</p></body></html>'
        # Quoted HTML attributes need entities around the JavaScript string.
        content = content.replace(b'onclick="document.querySelector("p").textContent="Ready""', b'onclick="document.querySelector(\'p\').textContent=\'Ready\'"')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, *args):
        pass


@unittest.skipUnless(os.getenv('AUTOTEST_BROWSER_TEST') == '1', 'Opt-in real browser fixture')
class WebReplayBrowserTest(unittest.TestCase):
    def test_real_browser_steps_screenshots_and_recording(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), FixtureHandler)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        with tempfile.TemporaryDirectory() as tmp:
            executor = LocalWebReplayExecutor(SimpleNamespace(artifacts_dir=Path(tmp), node_key='fixture'), None)
            executor._state = AsyncMock(return_value={})
            payload = {'project_id': 1, 'generation_task_id': 100, 'target_url': f'http://127.0.0.1:{server.server_port}', 'wait_for_login': False,
                       'candidate': {'name': 'Fixture', 'input_info': {'name': 'Synthetic'}, 'steps': [
                           {'action': 'fill', 'locator_type': 'label', 'locator': 'Name', 'value': '{{name}}'},
                           {'action': 'click', 'locator_type': 'role', 'role': 'button', 'locator': 'Save'},
                           {'action': 'assert', 'locator_type': 'text', 'locator': 'Ready', 'expected': 'Ready'},
                       ]}}
            with patch('agent_app.executors.web_replay_executor.chromium_launch_options', return_value={'channel': 'chrome', 'headless': True}):
                result = executor.execute(100, 'lease', payload)
            self.assertEqual(0, result['failed_count'], str(result))
            data = result['records'][0]['data']
            self.assertEqual(3, data['step_count'])
            self.assertEqual(3, len(data['screenshots']))
            self.assertGreater(Path(data['video_local_path']).stat().st_size, 100)
            self.assertTrue(Path(data['video_local_path']).read_bytes().startswith(b'\x1aE\xdf\xa3'))
