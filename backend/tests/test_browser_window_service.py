import unittest
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError
from test_agent_services import FakeResourceRepository

from app.core.exceptions import BusinessRuleError
from app.schemas.browser_window import BrowserWindowExchangeRequest
from app.services.browser_window_service import BrowserWindowService


class BrowserWindowServiceTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeResourceRepository()
        self.node = self.repo.create('agent_nodes', {'name': 'Fixture PC', 'status': 'active', 'data': {
            'node_key': 'fixture', 'agent_status': 'busy', 'capabilities': ['browser_window_control'],
            'last_seen_at': datetime.now(UTC).isoformat(),
        }})
        self.task = self.repo.create('agent_tasks', {'status': 'running', 'data': {
            'task_type': 'web_replay', 'node_key': 'fixture', 'claimed_by': 'fixture', 'lease_token': 'test-lease',
            'lease_expires_at': (datetime.now(UTC) + timedelta(seconds=120)).isoformat(),
        }})
        self.service = BrowserWindowService(self.repo)
        self.state = {'window_id': '0123456789abcdef', 'revision': 1, 'status': 'open', 'browser_name': 'Google Chrome', 'label': 'Fixture'}

    def exchange(self, **changes):
        self.state = {**self.state, **changes}
        return self.service.exchange(self.task['id'], BrowserWindowExchangeRequest(node_key='fixture', lease_token='test-lease', window=self.state))

    def test_show_waits_for_owned_agent_ack_and_is_coalesced(self):
        self.exchange()
        self.assertTrue(self.service.get(self.task['id'])['can_show'])
        result = self.service.request_show(self.task['id'])
        self.assertEqual(result, self.service.request_show(self.task['id']))
        self.assertEqual('pending', self.service.get(self.task['id'])['command']['status'])
        self.exchange(revision=2, command_id=result['command_id'], focus='blocked')
        self.assertEqual('blocked', self.service.get(self.task['id'])['command']['status'])

    def test_foreign_node_lease_or_expired_lease_cannot_control(self):
        for node, lease in [('other', 'test-lease'), ('fixture', 'foreign')]:
            with self.assertRaises(BusinessRuleError):
                self.service.exchange(self.task['id'], BrowserWindowExchangeRequest(node_key=node, lease_token=lease, window=self.state))
        self.task['data']['lease_expires_at'] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
        with self.assertRaises(BusinessRuleError):
            self.exchange()

    def test_stale_closed_and_offline_windows_cannot_be_shown(self):
        self.exchange()
        self.task['data']['browser_window_seen_at'] = (datetime.now(UTC) - timedelta(seconds=20)).isoformat()
        with self.assertRaises(BusinessRuleError):
            self.service.request_show(self.task['id'])
        self.exchange(revision=2, status='closed')
        self.assertFalse(self.service.get(self.task['id'])['can_show'])
        self.exchange(revision=3, status='open')
        self.node['data']['last_seen_at'] = (datetime.now(UTC) - timedelta(seconds=100)).isoformat()
        self.assertFalse(self.service.get(self.task['id'])['can_show'])

    def test_new_window_invalidates_old_command_and_late_old_reports(self):
        self.exchange()
        self.service.request_show(self.task['id'])
        self.exchange(revision=3, window_id='fedcba9876543210')
        self.assertEqual('closed', self.service.get(self.task['id'])['command']['status'])
        with self.assertRaises(BusinessRuleError):
            self.exchange(revision=2, window_id='0123456789abcdef')
        self.assertEqual('fedcba9876543210', self.service.get(self.task['id'])['window']['window_id'])

    def test_expired_request_is_not_dispatched(self):
        self.exchange()
        self.service.request_show(self.task['id'])
        self.task['data']['browser_window_command']['created_at'] = (datetime.now(UTC) - timedelta(seconds=20)).isoformat()
        self.assertIsNone(self.exchange(revision=2)['command'])
        self.assertEqual('expired', self.service.get(self.task['id'])['command']['status'])

    def test_headless_nonweb_and_old_agents_have_no_show_action(self):
        for mode in ['server_headless', 'local_headed']:
            self.task['data'].update(task_type='case_execution', payload={'case_type': 'WEB', 'execution': {'mode': mode}})
            self.assertEqual(mode == 'local_headed', self.service.get(self.task['id'])['headed'])
        self.task['data']['payload']['execution']['config'] = {'headless': 'true'}
        self.assertFalse(self.service.get(self.task['id'])['headed'])
        self.task['data'].update(task_type='device_discovery')
        with self.assertRaises(BusinessRuleError):
            self.exchange()
        self.node['data']['capabilities'] = []
        self.assertFalse(self.service.get(self.task['id'])['supported'])

    def test_native_handles_and_paths_cannot_be_uploaded(self):
        for key in ['hwnd', 'pid', 'executable_path']:
            with self.assertRaises(ValidationError):
                BrowserWindowExchangeRequest(node_key='fixture', lease_token='test-lease', window={**self.state, key: 42})

    def test_terminal_task_never_displays_stale_open_window(self):
        self.exchange()
        self.task['status'] = 'success'
        self.assertEqual('closed', self.service.get(self.task['id'])['window']['status'])
        with self.assertRaises(BusinessRuleError):
            self.service.request_show(self.task['id'])
