import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.exceptions import BusinessRuleError
from app.schemas.agent import AgentHeartbeatRequest, AgentRegisterRequest
from app.services.agent_node_service import AgentNodeService
from app.services.web_case_secret_service import WebCaseSecretService
from app.services.web_feature_testing_service import WebFeatureTestingService
from app.services.web_page_management_service import WebPageManagementService
from test_agent_services import FakeResourceRepository


class WebAgentSecretDomainTest(unittest.TestCase):
    def setUp(self):
        self.storage = tempfile.TemporaryDirectory()
        self.addCleanup(self.storage.cleanup)
        environment = patch.dict(os.environ, {'AUTOTEST_STORAGE_DIR': self.storage.name})
        environment.start()
        self.addCleanup(environment.stop)
        self.repo = FakeResourceRepository()
        self.nodes = AgentNodeService(self.repo)
        self.features = WebFeatureTestingService(self.repo)

    def register(self):
        return self.nodes.register(AgentRegisterRequest(
            node_key='local-web', name='Local Web',
            capabilities=['case_execution', 'web_secret_inputs'],
        ))

    def create_case(self):
        group = WebPageManagementService(self.repo).create_group({
            'name': 'Login', 'project_id': 1, 'url': 'https://example.test/login',
        })
        feature = self.features.save_feature(group['id'], {
            'name': 'Login', 'feature_type': 'login', 'parameters': [
                {'key': 'password', 'label': 'Password', 'type': 'password',
                 'locator_type': 'label', 'locator': 'Password'},
            ],
        })
        self.features.save_version(feature['id'], {'name': 'Login', 'steps': [
            {'action': 'fill', 'locator_type': 'label', 'locator': 'Password', 'value': '{{password}}'},
            {'action': 'assert', 'locator_type': 'text', 'locator': 'Ready', 'expected': 'Ready'},
        ]})
        case = self.features.save_case(feature['id'], {
            'name': 'Login', 'input_info': {'password': 'synthetic-secret'},
        })
        return feature, case

    def test_registration_without_key_does_not_create_one(self):
        node = self.register()
        self.assertFalse(node['data']['web_secret_inputs_ready'])
        self.assertFalse((Path(self.storage.name) / 'web-input-secrets' / 'key').exists())

    def test_heartbeat_rechecks_encryption_domain_without_disclosing_key(self):
        self.register()
        WebCaseSecretService().protect([{'key': 'password', 'type': 'password'}], {'password': 'synthetic'})
        node = self.nodes.heartbeat('local-web', AgentHeartbeatRequest())
        self.assertTrue(node['data']['web_secret_inputs_ready'])
        self.assertEqual(64, len(node['data']['web_input_key_id']))
        with tempfile.TemporaryDirectory() as other, patch.dict(os.environ, {'AUTOTEST_STORAGE_DIR': other}):
            WebCaseSecretService().protect([{'key': 'password', 'type': 'password'}], {'password': 'other'})
            foreign = self.nodes.list_nodes()[0][0]
            self.assertFalse(foreign['data']['web_secret_inputs_ready'])

    def test_mismatched_node_rejected_before_queue_and_matching_node_succeeds(self):
        self.register()
        feature, case = self.create_case()
        payload = {'case_ids': [case['id']], 'node_key': 'local-web',
                   'headless': False, 'approve_side_effects': True, 'record_video': False}
        with self.assertRaisesRegex(BusinessRuleError, '密码通道未匹配'):
            self.features.run(feature['id'], payload)
        self.assertFalse(self.repo.tables.get('agent_tasks'))
        self.nodes.heartbeat('local-web', AgentHeartbeatRequest())
        queued = self.features.run(feature['id'], payload)
        self.assertEqual('pending', queued['status'])
        self.assertEqual(queued['agent_task_id'], self.features.detail(feature['id'])['feature']['data']['last_agent_task_id'])
        task = self.repo.get('agent_tasks', queued['agent_task_id'])
        self.assertNotIn('synthetic-secret', str(task))


if __name__ == '__main__':
    unittest.main()
