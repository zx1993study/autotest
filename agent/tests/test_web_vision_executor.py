import asyncio
import base64
import io
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from agent_app.auth.web_login_cache import WebLoginCache
from agent_app.executors.web_vision_executor import LocalWebVisionExecutor
from agent_app.runtime.capabilities import available_capabilities
from web_automation.discovery.browser import DiscoveryBrowserSession


class WebVisionExecutorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = SimpleNamespace(server_url='https://platform.test', node_key='local', artifacts_dir=Path(self.temp.name))
        self.payload = {'target_url': 'https://example.test/customers', 'discovery': {'project_id': 1, 'wait_for_login': True, 'reuse_login': True}}

    def test_web_capability_requires_web_plugin_and_playwright(self):
        with patch('agent_app.runtime.capabilities.find_spec', return_value=object()):
            self.assertIn('web_vision_discovery', available_capabilities(('web',)))
            self.assertNotIn('web_vision_discovery', available_capabilities(('mobile',)))

    def test_login_cache_is_scoped_and_expired_state_is_not_reused(self):
        cache = WebLoginCache(self.config, self.payload)
        other = WebLoginCache(self.config, {**self.payload, 'discovery': {'project_id': 2}})
        self.assertNotEqual(cache.path, other.path)
        page = Mock(context=Mock(storage_state=AsyncMock(return_value={'cookies': [], 'origins': []})))
        page.evaluate = AsyncMock(side_effect=['https://example.test', {'token': 'synthetic-test'}])
        asyncio.run(cache.save(page))
        self.assertEqual(cache.load()['session_storage']['token'], 'synthetic-test')
        with patch('agent_app.auth.web_login_cache.time.time', return_value=10**12):
            self.assertEqual(cache.load(), {})

    def test_cross_origin_session_storage_is_not_cached(self):
        cache = WebLoginCache(self.config, self.payload)
        page = Mock(evaluate=AsyncMock(return_value='https://other.test'))
        asyncio.run(cache.save(page))
        self.assertFalse(cache.path.exists())

    def test_cancel_and_closed_browser_stop_without_model_calls(self):
        api = Mock()
        api.vision_state.return_value = {'cancel_requested': True}
        session = Mock(page=Mock(is_closed=Mock(return_value=False)))
        executor = LocalWebVisionExecutor(self.config, api)
        with self.assertRaisesRegex(RuntimeError, '取消'):
            asyncio.run(executor._wait_login(session, 1, 'lease', self.payload))
        session.page.is_closed.return_value = True
        with self.assertRaisesRegex(RuntimeError, '关闭'):
            asyncio.run(executor._wait_login(session, 1, 'lease', self.payload))
        self.assertTrue(all(call.args[2]['phase'] == 'waiting_login' for call in api.vision_step.call_args_list))

    @unittest.skipUnless(os.getenv('AUTOTEST_TEST_BROWSER') == '1', 'Explicit real-browser smoke test')
    def test_real_headed_browser_in_worker_thread_and_manual_continue(self):
        from PIL import Image, ImageStat

        class FixtureSession(DiscoveryBrowserSession):
            async def __aenter__(self):
                await super().__aenter__()
                await self.page.route('https://example.test/**', lambda route: route.fulfill(content_type='text/html', body='''
                    <body style="background:white;color:black"><h1>Customers</h1>
                    <button onclick="document.querySelector('dialog').showModal()">Add</button>
                    <dialog><h2>New customer</h2><input aria-label="Customer name">
                    <button onclick="this.closest('dialog').close()">Cancel</button></dialog></body>'''))
                return self

        api = Mock()
        api.vision_state.return_value = {'login_confirmed': True}
        phases = []
        def step(task, lease, data):
            phases.append(data['phase'])
            if data['phase'] == 'overview':
                pixels = Image.open(io.BytesIO(base64.b64decode(data['screenshot_base64'])))
                self.assertGreater(max(ImageStat.Stat(pixels).stddev), 1)
                return {'features': [{'feature': 'Add', 'entry_hint': 'Add'}]}
            if data['phase'] == 'captures':
                self.assertEqual(len(data['captures']), 1)
                return {'saved_elements': 2, 'model_http_calls': 2}
            return {'waiting': True}
        api.vision_step.side_effect = step
        with patch('agent_app.executors.web_vision_executor.DiscoveryBrowserSession', FixtureSession), patch('agent_app.executors.web_vision_executor.chromium_launch_options', return_value={'channel': 'msedge', 'headless': False}) as launch, ThreadPoolExecutor(max_workers=1) as workers:
            result = workers.submit(LocalWebVisionExecutor(self.config, api).execute, 1, 'lease', self.payload).result(timeout=45)
        self.assertEqual(phases, ['waiting_login', 'overview', 'captures'])
        self.assertEqual(result['saved_elements'], 2)
        launch.assert_called_once_with(headless=False, slow_mo_ms=0)
        self.assertNotIn('storage_state', str(result))


if __name__ == '__main__':
    unittest.main()
