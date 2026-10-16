import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from agent_app.windows.local_control import read_window, request_local_show, window_path, write_json
from agent_app.windows.native import NativeBrowserWindow
from agent_app.windows.task_window import TaskBrowserWindow


class BrowserWindowControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict('os.environ', {'LOCALAPPDATA': self.temp.name})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.config = SimpleNamespace(server_url='https://fixture.test', node_key='fixture')

    def controller(self):
        with patch('agent_app.windows.task_window.NativeBrowserWindow') as factory:
            native = factory.return_value
            native.status, native.browser_name = 'open', 'Google Chrome'
            native.focus.return_value = 'blocked'
            window = TaskBrowserWindow(self.config, Mock(), 42, 'lease', 'Synthetic')
            window.page = Mock(is_closed=Mock(return_value=False), bring_to_front=AsyncMock())
            return window, native

    def test_local_commands_are_scoped_to_instance_and_expire(self):
        window, _ = self.controller()
        write_json(window_path(self.config), {'task_id': 42, 'window': window.state(), 'updated_at': time.time()})
        request_local_show(self.config)
        self.assertTrue(window._local_command())
        self.assertFalse(window._local_command())
        command_path = window_path(self.config).with_suffix('.show')
        for command in [{'id': 'foreign', 'window_id': 'foreign', 'created_at': time.time()}, {'id': 'expired', 'window_id': window.window_id, 'created_at': time.time() - 20}]:
            write_json(command_path, command)
            self.assertFalse(window._local_command())

    def test_stale_registry_cannot_activate_a_window(self):
        write_json(window_path(self.config), {'task_id': 42, 'window': {'status': 'open'}, 'updated_at': time.time() - 20})
        self.assertEqual({}, read_window(self.config))
        with self.assertRaises(ValueError):
            request_local_show(self.config)

    def test_activation_ack_reflects_native_result_not_submission(self):
        window, native = self.controller()
        asyncio.run(window.activate('command'))
        self.assertEqual('blocked', window.state()['focus'])
        self.assertEqual('command', window.state()['command_id'])
        native.focus.return_value = 'active'
        asyncio.run(window.activate())
        self.assertEqual('active', window.state()['focus'])
        self.assertEqual('command', window.state()['command_id'])

    def test_closed_page_cannot_be_activated(self):
        window, native = self.controller()
        window.page.is_closed.return_value = True
        asyncio.run(window.activate('command'))
        native.focus.assert_not_called()
        self.assertEqual('failed', window.state()['focus'])

    def test_phase_changes_do_not_repeatedly_take_focus(self):
        window, native = self.controller()
        asyncio.run(window.set_phase('analyzing'))
        native.focus.assert_not_called()
        asyncio.run(window.set_phase('waiting_login', activate=True))
        native.focus.assert_called_once()

    def test_registry_is_scoped_to_platform_and_node(self):
        self.assertNotEqual(window_path(self.config), window_path(SimpleNamespace(server_url='https://other.test', node_key='fixture')))

    def test_ambiguous_windows_are_not_selected(self):
        api = Mock()
        api.windows.side_effect = [[], [(10, 100), (20, 200)]]
        api.descendants.return_value = {100, 200}
        api.fingerprint.return_value = (123, 'C:/Chrome/chrome.exe')
        api.user.GetWindow.return_value = 0
        with patch('agent_app.windows.native.Win32', return_value=api):
            native = NativeBrowserWindow('Synthetic')
            native._find()
        self.assertIsNone(native.binding)

    def test_existing_and_foreign_windows_are_excluded(self):
        api = Mock()
        api.windows.side_effect = [[(10, 100)], [(10, 100), (20, 200), (30, 300)]]
        api.descendants.return_value = {100, 200}
        api.fingerprint.return_value = (123, 'C:/Chrome/chrome.exe')
        api.user.GetWindow.return_value = 0
        with patch('agent_app.windows.native.Win32', return_value=api):
            native = NativeBrowserWindow('Synthetic')
            native._find()
        self.assertEqual(20, native.binding[0])

    def test_closed_controller_cleans_native_strip_and_reports_final_state(self):
        window, native = self.controller()
        asyncio.run(window.close())
        native.close.assert_called_once()
        self.assertEqual('closed', read_window(self.config)['window']['status'])
