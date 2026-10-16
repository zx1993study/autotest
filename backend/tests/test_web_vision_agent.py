import base64
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

from app.core.exceptions import BusinessRuleError
from app.schemas.ai import WebVisionDiscoveryRequest
from app.schemas.web_vision_agent import VisionStepRequest
from app.services.agent_task_lease_service import AgentTaskLeaseService
from app.services.vision_model_check_service import VisionModelCheckService
from app.services.web_vision_agent_service import WebVisionAgentService
from app.services.web_vision_control_service import WebVisionControlService
from app.services.web_vision_step_service import WebVisionStepService
from app.utils.cancellable_model_request import ModelRequestCancelled
from app.utils.vision_images import red_test_image, save_vision_image
from app.utils.vision_llm_client import VisionModelError
from pydantic import ValidationError
from test_agent_services import FakeResourceRepository


class WebVisionAgentTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = FakeResourceRepository()
        self.page = self.repo.create('web_pages', {'name': 'Customers', 'project_id': 1, 'data': {'url': 'https://example.test/customers'}})
        self.repo.create('agent_nodes', {'status': 'active', 'data': {'node_key': 'local', 'agent_status': 'online', 'capabilities': ['web_vision_discovery'], 'last_seen_at': datetime.now(UTC).isoformat()}})
        self.service = WebVisionAgentService(self.repo)
        self.client = Mock(api_key='synthetic-key', model='synthetic-model', requests_made=0, timeout_sec=60, rate_limit_retries=0)
        self.service.discovery.model_service.active_model = Mock(return_value={'id': 7, 'data': {'model': 'synthetic-model'}})
        self.service.discovery._vision_client = Mock(return_value=self.client)
        self.service.discovery.task_runtime.detail_files.storage_dir = Path(self.temp.name)
        self.request = WebVisionDiscoveryRequest(project_id=1, page_id=self.page['id'], headless=False, node_key='local', wait_for_login=True)

    def claimed(self):
        queued = self.service.queue(self.request)
        task = self.repo.get('agent_tasks', queued['agent_task_id'])
        task.update(status='running')
        task['data'].update(claimed_by='local', lease_token='lease')
        return task, queued['task_id']

    def step(self, task, phase, **values):
        values.setdefault('page_url', task['data']['payload']['target_url'])
        return self.service.step(task['id'], VisionStepRequest(node_key='local', lease_token='lease', phase=phase, **values))

    def test_queue_pins_model_and_does_not_ship_provider_credentials(self):
        task, ai_id = self.claimed()
        self.assertEqual(task['data']['payload']['discovery']['vision_model_id'], 7)
        self.assertNotIn('synthetic-key', str(task))
        self.assertEqual(self.repo.get('ai_generation_tasks', ai_id)['data']['model_http_calls'], 0)
        self.assertEqual(self.service.active(1, self.page['id'])['agent_task_id'], task['id'])

    def test_stale_node_wrong_project_and_headless_login_rejected(self):
        with self.assertRaises(ValidationError):
            WebVisionDiscoveryRequest(project_id=1, page_id=1, wait_for_login=True)
        with self.assertRaises(BusinessRuleError):
            self.service.queue(self.request.model_copy(update={'project_id': 2}))
        self.repo.tables['agent_nodes'][0]['data']['last_seen_at'] = '2000-01-01T00:00:00+00:00'
        with self.assertRaises(BusinessRuleError):
            self.service.queue(self.request)

    def test_manual_login_is_required_and_retry_resets_confirmation(self):
        task, _ = self.claimed()
        self.step(task, 'waiting_login')
        self.assertFalse(self.service.state(task['id'], VisionStepRequest(node_key='local', lease_token='lease', phase='overview'))['login_confirmed'])
        with self.assertRaises(BusinessRuleError):
            self.step(task, 'overview')
        self.service.interact(task['id'], 'continue')
        self.step(task, 'waiting_login', login_retry=True)
        self.assertIn('仍在登录页', task['data']['progress'])
        self.service.interact(task['id'], 'cancel')
        self.assertTrue(self.service.state(task['id'], VisionStepRequest(node_key='local', lease_token='lease', phase='overview'))['cancel_requested'])
        self.client.complete_json.assert_not_called()

    def test_runtime_requires_owner_lease_and_running_task(self):
        task, _ = self.claimed()
        for node, lease in [('other', 'lease'), ('local', 'wrong')]:
            with self.assertRaises(BusinessRuleError):
                self.service.state(task['id'], VisionStepRequest(node_key=node, lease_token=lease, phase='overview'))
        task['status'] = 'failed'
        with self.assertRaises(BusinessRuleError):
            self.step(task, 'waiting_login')

    def test_model_failure_records_http_calls_and_redacts_key(self):
        task, ai_id = self.claimed()
        self.step(task, 'waiting_login')
        self.service.interact(task['id'], 'continue')
        def unavailable(*args):
            self.client.requests_made += 1
            raise VisionModelError('HTTP 503 synthetic-key')
        self.service.discovery._discover_features = unavailable
        encoded = base64.b64encode(red_test_image()).decode('ascii')
        with patch('app.utils.vision_images.storage_path', return_value=Path(self.temp.name)), self.assertRaises(VisionModelError):
            self.step(task, 'overview', screenshot_base64=encoded)
        ai = self.repo.get('ai_generation_tasks', ai_id)
        self.assertEqual(ai['status'], 'failed')
        self.assertEqual(ai['data']['result']['model_http_calls'], 1)
        self.assertNotIn('synthetic-key', str(ai))
        self.assertEqual(task['data']['model_http_calls'], 1)

    def test_overview_and_captures_are_idempotent(self):
        task, ai_id = self.claimed()
        self.step(task, 'waiting_login')
        self.service.interact(task['id'], 'continue')
        task['data']['vision_features'] = []
        self.assertEqual(self.step(task, 'overview'), {'features': []})
        first = self.step(task, 'captures')
        self.assertEqual(self.step(task, 'captures'), first)
        self.assertEqual(self.repo.get('ai_generation_tasks', ai_id)['status'], 'success')
        self.client.complete_json.assert_not_called()

    def test_renew_preserves_discovery_progress(self):
        task, _ = self.claimed()
        task['data'].update(vision_phase='waiting_login', model_http_calls=2)
        AgentTaskLeaseService(self.repo).renew(task['id'], VisionStepRequest(node_key='local', lease_token='lease', phase='overview'))
        self.assertEqual(task['data']['vision_phase'], 'waiting_login')
        self.assertEqual(task['data']['model_http_calls'], 2)

    def test_invalid_screenshots_are_rejected(self):
        for encoded in ['invalid', base64.b64encode(b'not png').decode()]:
            with self.assertRaises(BusinessRuleError):
                save_vision_image(1, encoded)

    def test_login_target_does_not_ship_auth_or_wait_for_login(self):
        self.page['data'].update(url='https://example.test/login', auth_id=999)
        task, _ = self.claimed()
        payload = task['data']['payload']
        self.assertFalse(payload['discovery']['wait_for_login'])
        self.assertFalse(payload['discovery']['reuse_login'])
        self.assertEqual(payload['context'], {})

    def test_redirected_overview_is_rejected_before_model_and_persistence(self):
        task, _ = self.claimed()
        with self.assertRaisesRegex(BusinessRuleError, '地址不一致'):
            self.step(task, 'overview', page_url='https://example.test/home')
        self.client.complete_json.assert_not_called()
        self.assertNotIn('features', self.page['data'])

    def test_root_url_login_route_uses_saved_hash_router_and_no_auth(self):
        self.page['data'].update(url='https://example.test/', route='/login', auth_id=999)
        self.repo.create('web_page_groups', {'project_id': 1, 'data': {'url': 'https://example.test/#/orders'}})
        task, _ = self.claimed()
        payload = task['data']['payload']
        self.assertEqual(payload['target_url'], 'https://example.test/#/login')
        self.assertFalse(payload['discovery']['wait_for_login'])
        self.assertFalse(payload['discovery']['reuse_login'])
        self.assertEqual(payload['context'], {})

    def test_continue_cannot_revive_canceled_analysis(self):
        task, ai_id = self.claimed()
        self.step(task, 'waiting_login')
        WebVisionControlService(self.repo).cancel(ai_id)
        with self.assertRaises(ModelRequestCancelled):
            self.service.interact(task['id'], 'continue')
        self.assertEqual(self.repo.get('ai_generation_tasks', ai_id)['status'], 'canceled')

    def test_cancel_during_analysis_is_idempotent_and_blocks_late_results(self):
        task, ai_id = self.claimed()
        control = WebVisionControlService(self.repo)
        self.assertEqual(control.cancel(ai_id), {'accepted': True})
        self.assertEqual(control.cancel(ai_id), {'accepted': True})
        self.assertTrue(self.service.state(task['id'], VisionStepRequest(node_key='local', lease_token='lease', phase='overview'))['cancel_requested'])
        with self.assertRaises(ModelRequestCancelled):
            self.step(task, 'overview')
        self.service.discovery.task_runtime.finish_task(ai_id, 'success', {'features': ['late']}, only_if_active=True)
        self.service.finish({**task, 'status': 'failed'})
        self.assertEqual(self.repo.get('ai_generation_tasks', ai_id)['status'], 'canceled')
        self.client.complete_json.assert_not_called()

    def test_cancel_pending_prevents_agent_claim(self):
        queued = self.service.queue(self.request)
        WebVisionControlService(self.repo).cancel(queued['task_id'])
        self.assertEqual(self.repo.get('agent_tasks', queued['agent_task_id'])['status'], 'canceled')

    def test_step_job_is_short_idempotent_and_pollable(self):
        self.page['data']['url'] = 'https://example.test/login'
        task, _ = self.claimed()
        jobs = WebVisionStepService(self.repo)
        jobs.vision.discovery = self.service.discovery
        request = VisionStepRequest(node_key='local', lease_token='lease', phase='overview', page_url=self.page['data']['url'])
        response, job_id = jobs.begin(task['id'], request)
        self.assertTrue(response['pending'])
        self.assertEqual(jobs.begin(task['id'], request), (response, None))
        self.client.complete_json.assert_not_called()
        jobs.vision.step = Mock(return_value={'features': []})
        jobs.run(task['id'], request, job_id, lambda: False)
        self.assertEqual(jobs.begin(task['id'], request), ({'features': []}, None))
        self.assertEqual(self.service.state(task['id'], request)['analysis']['status'], 'success')

    def test_cancel_stalled_job_never_runs_the_model(self):
        task, ai_id = self.claimed()
        jobs = WebVisionStepService(self.repo)
        request = VisionStepRequest(node_key='local', lease_token='lease', phase='overview', page_url=self.page['data']['url'])
        _, job_id = jobs.begin(task['id'], request)
        WebVisionControlService(self.repo).cancel(ai_id)
        jobs.run(task['id'], request, job_id, lambda: True)
        self.assertEqual(task['data']['vision_job']['status'], 'canceled')
        self.assertEqual(self.repo.get('ai_generation_tasks', ai_id)['status'], 'canceled')
        self.client.complete_json.assert_not_called()

    def test_health_probe_reaches_provider_without_cache_and_redacts_errors(self):
        configured = Mock(api_key='private-key', api_url='https://example.test/responses', api_protocol='responses', reasoning_effort='low', model='model', timeout_sec=60)
        client = Mock(requests_made=1)
        client.complete_json.side_effect = VisionModelError('HTTP503 private-key')
        with patch('app.services.vision_model_check_service.WebVisionDiscoveryService') as discovery, patch('app.services.vision_model_check_service.VisionLlmClient', return_value=client) as constructor:
            discovery.return_value._vision_client.return_value = configured
            result = VisionModelCheckService(self.repo).check(7)
        self.assertFalse(result['healthy'])
        self.assertEqual(result['model_http_calls'], 1)
        self.assertNotIn('private-key', result['message'])
        self.assertFalse(constructor.call_args.kwargs['cache_enabled'])
        self.assertEqual(constructor.call_args.kwargs['api_protocol'], 'responses')


if __name__ == '__main__':
    unittest.main()
