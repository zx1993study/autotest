import base64
import copy
import io
import json
from zipfile import ZipFile
import unittest
from datetime import UTC, datetime
from unittest.mock import Mock, patch

from pydantic import ValidationError
from test_agent_services import FakeResourceRepository

from app.core.exceptions import BusinessRuleError
from app.main import create_app
from app.schemas.business_generation import GenerationRequest, ReplayRequest, ReplayStateRequest, ReferenceScreenshot
from app.services.business_generation_service import BusinessGenerationService, TASKS
from app.services.generation_candidate_service import safe_context, validate_candidate
from app.services.generation_repair_service import GenerationRepairService, check_repair
from app.services.generation_script_service import GenerationScriptService
from app.services.generation_task_query_service import GenerationTaskQueryService
from app.services.web_replay_service import WebReplayService
from app.utils.vision_images import red_test_image


class BusinessGenerationTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeResourceRepository()
        self.project = self.repo.create('projects', {'name': 'Synthetic'})
        self.source = self.repo.create('web_pages', {'name': 'Synthetic', 'project_id': self.project['id'], 'data': {'url': 'http://127.0.0.1/fixture'}})
        self.model = self.repo.create('ai_models', {'status': 'active', 'data': {'supports_vision': True}})
        self.repo.create('agent_nodes', {'status': 'active', 'data': {'node_key': 'synthetic', 'agent_status': 'online', 'capabilities': ['web_replay'], 'last_seen_at': datetime.now(UTC).isoformat()}})
        self.service = BusinessGenerationService(self.repo)
        self.candidate = {'name': 'Synthetic case', 'steps': [
            {'name': 'Name', 'action': 'fill', 'locator_type': 'label', 'locator': 'Name', 'value': '{{customer}}'},
            {'name': 'Verify', 'action': 'assert', 'locator_type': 'text', 'locator': 'Ready', 'expected': 'Ready'},
        ], 'input_info': {'customer': 'Synthetic'}, 'assertions': []}
        self.client = Mock(requests_made=1, api_key='synthetic-key')
        self.client.complete_json.return_value = {'candidate': self.candidate, 'questions': [], 'warnings': []}
        self.service._client = Mock(return_value=self.client)

    def generate(self):
        task = self.service.submit('WEB', GenerationRequest(source_id=self.source['id'], prompt='Fill Name and assert Ready', model_id=self.model['id']))
        self.service.run(task['id'])
        return self.service.get(task['id'])

    def replay(self, task):
        return WebReplayService(self.repo).queue(task['id'], ReplayRequest(candidate=task['data']['result']['candidate'], node_key='synthetic', approve_side_effects=True))

    def test_generation_calls_model_but_does_not_execute_or_save(self):
        task = self.generate()
        self.assertEqual('success', task['status'])
        self.assertEqual(1, task['data']['model_http_calls'])
        self.client.complete_json.assert_called_once()
        self.assertFalse(self.repo.tables.get('agent_tasks'))
        self.assertFalse(self.repo.tables.get('case_drafts'))
        self.assertTrue(task['data']['result']['candidate']['steps'][0]['require_unique'])

    def test_failure_is_not_rule_fallback_and_key_is_redacted(self):
        from app.utils.vision_llm_client import VisionModelError
        self.client.complete_json.side_effect = VisionModelError('HTTP 503 synthetic-key')
        task = self.generate()
        self.assertEqual('failed', task['status'])
        self.assertNotIn('synthetic-key', task['data']['error'])
        self.assertIn('503', task['data']['error'])
        self.assertFalse(task['data'].get('result'))

    def test_web_model_contract_explains_optional_assertion_expected(self):
        self.generate()
        system, payload, _ = self.client.complete_json.call_args.args
        contract = json.loads(payload)['output']['candidate']['steps'][0]
        self.assertIn('expected', contract)
        self.assertIn('assert步骤必须提供expected非空文本', system)
        self.assertIn('断言可选', system)
        self.client.complete_json.return_value = {'candidate': {
            'name': 'Incomplete assertion', 'steps': [
                {'action': 'assert', 'locator_type': 'text', 'locator': 'Ready', 'value': 'Ready'},
            ],
        }}
        failed = self.generate()
        self.assertEqual('failed', failed['status'])
        self.assertIn('需要 expected', failed['data']['error'])

    def test_canceled_generation_cannot_overwrite_terminal_state(self):
        def cancel(*args):
            item = self.repo.tables[TASKS][-1]
            WebReplayService(self.repo).control(item['id'], 'cancel')
            return {'candidate': self.candidate}
        self.client.complete_json.side_effect = cancel
        self.assertEqual('canceled', self.generate()['status'])

    def test_unknown_business_result_does_not_block_web_draft(self):
        self.client.complete_json.return_value = {'questions': ['What is success?']}
        task = self.generate()
        self.assertEqual('success', task['status'])
        self.assertIsNotNone(self.service.accept(task['id'], self.candidate))

    def test_screenshots_validate_size_magic_and_dimensions(self):
        valid = ReferenceScreenshot(description='Synthetic screenshot', image_base64=base64.b64encode(red_test_image()).decode())
        self.assertTrue(valid.image_base64)
        with self.assertRaises(ValidationError):
            ReferenceScreenshot(description='bad', image_base64=base64.b64encode(b'bad').decode())
        with self.assertRaises(ValidationError):
            GenerationRequest(source_id=1, prompt='   ')

    def test_foreign_api_path_auth_and_unknown_assertions_are_rejected_or_pinned(self):
        source = {'id': 20, 'data': {'method': 'POST', 'path': '/safe', 'auth_id': 9}}
        result = validate_candidate('API', {'name': 'API', 'path': '/unsafe', 'auth_id': 2, 'assertions': [{'type': 'status', 'expected': 200}]}, source)
        self.assertEqual('/safe', result['path'])
        self.assertEqual(9, result['auth_id'])
        with self.assertRaises(BusinessRuleError):
            validate_candidate('API', {'name': 'bad', 'headers': {'Authorization': 'secret'}}, source)

    def test_optional_web_assertions_but_no_arbitrary_code_or_empty_assertion(self):
        candidate = copy.deepcopy(self.candidate)
        candidate['steps'].pop()
        self.assertTrue(validate_candidate('WEB', candidate, self.source)['steps'])
        self.assertTrue(validate_candidate('APP', {'name':'App','steps':[{'action':'tap','locator_type':'text','locator':'Ready'}]},self.source)['steps'])
        with self.assertRaises(BusinessRuleError):
            validate_candidate('APP', {'name':'App', 'steps':[{'action':'tap'}]}, self.source)
        for change in ('exec', 'empty_assertion'):
            candidate = copy.deepcopy(self.candidate)
            if change == 'no_assertion':
                candidate['steps'].pop()
            elif change == 'exec':
                candidate['steps'][0]['action'] = 'evaluate'
            else:
                candidate['steps'][1]['expected'] = ''
            with self.assertRaises(BusinessRuleError):
                validate_candidate('WEB', candidate, self.source)

    def test_context_removes_credentials_in_fields_keys_and_free_text(self):
        context = safe_context({'Authorization': 'secret', 'items': [{'name': 'token', 'data': {'example': 'secret'}}], 'text': 'Bearer token123'})
        self.assertNotIn('secret', str(context))
        self.assertNotIn('token123', str(context))

    def test_candidate_must_be_explicitly_approved_before_replay(self):
        task = self.generate()
        with self.assertRaises(BusinessRuleError):
            WebReplayService(self.repo).queue(task['id'], ReplayRequest(candidate=self.candidate, node_key='synthetic'))
        result = self.replay(task)
        agent = self.repo.get('agent_tasks', result['agent_task_id'])
        self.assertEqual('web_replay', agent['data']['task_type'])
        with self.assertRaises(BusinessRuleError):
            self.replay(task)
        with self.assertRaises(BusinessRuleError):
            self.service.accept(task['id'], self.candidate)

    def test_manual_login_control_and_runtime_owner_checks(self):
        task = self.generate()
        queued = self.replay(task)
        agent = self.repo.get('agent_tasks', queued['agent_task_id'])
        agent.update(status='running')
        agent['data'].update(claimed_by='synthetic', lease_token='lease')
        service = WebReplayService(self.repo)
        service.state(agent['id'], ReplayStateRequest(node_key='synthetic', lease_token='lease', phase='waiting_login'))
        service.control(task['id'], 'continue')
        self.assertTrue(service.state(agent['id'], ReplayStateRequest(node_key='synthetic', lease_token='lease'))['login_confirmed'])
        with self.assertRaises(BusinessRuleError):
            service.state(agent['id'], ReplayStateRequest(node_key='foreign', lease_token='lease'))

    def test_accept_is_idempotent_and_changed_candidate_loses_verified_state(self):
        task = self.generate()
        queued = self.replay(task)
        self.repo.get('agent_tasks', queued['agent_task_id']).update(status='success')
        candidate = copy.deepcopy(task['data']['result']['candidate'])
        candidate['input_info']['customer'] = 'Changed'
        saved = self.service.accept(task['id'], candidate)
        again = self.service.accept(task['id'], candidate)
        self.assertEqual(saved, again)
        self.assertFalse(self.repo.tables.get('case_drafts'))
        stored = self.repo.tables['web_function_versions'][0]['data']['candidate']
        self.assertEqual('pending', stored['generation_meta']['verification']['status'])
        self.assertEqual('pending', GenerationScriptService(self.repo).export(task['id'])['status'])

    def test_verified_script_export_uses_safe_literals(self):
        task = self.generate()
        queued = self.replay(task)
        self.repo.get('agent_tasks', queued['agent_task_id']).update(status='success')
        self.service.accept(task['id'], task['data']['result']['candidate'])
        script = GenerationScriptService(self.repo).export(task['id'])['script']
        compile(script, '<exported>', 'exec')
        self.assertIn('PlaywrightEngine', script)

    def test_script_export_keeps_verified_url_and_variable_context(self):
        self.candidate['variables'] = {'suffix': '{{timestamp}}'}
        task = self.generate()
        queued = self.replay(task)
        self.repo.get('agent_tasks', queued['agent_task_id']).update(status='success')
        self.service.accept(task['id'], task['data']['result']['candidate'])
        self.source['data']['url'] = 'https://unverified.example.invalid/new'
        exported = GenerationScriptService(self.repo).export(task['id'])
        script = exported['script']
        with ZipFile(io.BytesIO(base64.b64decode(exported['bundle_base64']))) as archive:
            steps = json.loads(archive.read('steps.json'))
            self.assertEqual('http://127.0.0.1/fixture', steps['url'])
            self.assertEqual('{{timestamp}}', steps['variables']['suffix'])
        self.assertIn('DynamicValueContext', script)
        self.assertIn('Browser left the target site', script)
        compile(script, '<exported>', 'exec')

    def test_unverified_failure_lessons_are_not_retrieved(self):
        refs = []
        for kind, verification in [('principle', None), ('app_failure_lesson', None), ('automation_experience', 'candidate'), ('automation_experience', 'verified')]:
            data = {'domain': 'WEB', 'kind': kind}
            if verification:
                data['verification_status'] = verification
            item = self.repo.create('project_knowledge', {'project_id': self.project['id'], 'status': 'active', 'data': data})
            if kind == 'principle' or verification == 'verified':
                refs.append(item['id'])
        self.assertEqual(refs, self.service._context('WEB', self.source, True)['knowledge_refs'])

    def test_failure_archive_is_candidate_until_repair_verifies(self):
        task = self.generate()
        queued = self.replay(task)
        agent = self.repo.get('agent_tasks', queued['agent_task_id'])
        agent.update(status='failed')
        agent['data']['result'] = {'records': [{'data': {'error': 'Locator missing'}}]}
        repair = GenerationRepairService(self.repo)
        repair.finish(agent)
        repair.finish(agent)
        self.assertEqual(1, len(self.repo.tables['project_knowledge']))
        self.assertEqual('candidate', self.repo.tables['project_knowledge'][0]['data']['verification_status'])
        repaired = copy.deepcopy(self.candidate)
        repaired['steps'][0]['locator'] = 'New name'
        check_repair(self.candidate, repaired)
        repaired['steps'][1]['expected'] = 'Different'
        with self.assertRaises(BusinessRuleError):
            check_repair(self.candidate, repaired)

    def test_direct_case_repair_verifies_knowledge_without_parent_generation(self):
        task = self.generate()
        knowledge = self.repo.create('project_knowledge', {'project_id': self.project['id'], 'data': {'verification_status': 'candidate', 'content': 'Missing locator'}})
        task['data'].update(repair_case_id=123, failure_knowledge_id=knowledge['id'])
        agent = self.repo.get('agent_tasks', self.replay(task)['agent_task_id'])
        agent['status'] = 'success'
        GenerationRepairService(self.repo).finish(agent)
        self.assertEqual('verified', self.repo.get('project_knowledge', knowledge['id'])['data']['verification_status'])

    def test_case_repair_requires_verification_then_rebinds_only_failed_case(self):
        task = self.generate()
        self.service.accept(task['id'], task['data']['result']['candidate'])
        case = self.repo.tables['web_test_cases'][0]
        original_version = case['data']['script_version']
        parameters = copy.deepcopy(self.repo.tables['web_function_versions'][0]['data']['parameters'])
        repaired = copy.deepcopy(task['data']['result']['candidate'])
        repaired['steps'][0]['locator'] = 'Customer name'
        self.client.complete_json.return_value = {'candidate': repaired, 'questions': [], 'warnings': []}
        queued = self.service.submit('WEB', GenerationRequest(source_id=self.source['id'], prompt='Repair locator', model_id=self.model['id']))
        queued['data'].update(repair_original=task['data']['result']['candidate'], repair_case_id=case['id'], repair_parameters=parameters)
        self.service.run(queued['id'])
        candidate = self.service.get(queued['id'])['data']['result']['candidate']
        with self.assertRaises(BusinessRuleError):
            self.service.accept(queued['id'], candidate)
        agent = self.repo.get('agent_tasks', self.replay(queued)['agent_task_id'])
        agent['status'] = 'success'
        self.service.accept(queued['id'], candidate)
        saved = self.repo.get('web_test_cases', case['id'])
        self.assertNotEqual(original_version, saved['data']['script_version'])
        self.assertEqual('Customer name', saved['steps'][0]['locator'])
        self.assertEqual(case['data']['input_info'], saved['data']['input_info'])
        self.assertEqual('verified', self.repo.get('web_function_versions', saved['data']['script_version'])['status'])

    def test_public_tasks_do_not_expose_reference_images(self):
        task = self.generate()
        value = GenerationTaskQueryService(self.repo).get(task['id'])
        self.assertNotIn('payload', value['data'])
        self.assertIn('payload', task['data'])

    def test_old_ai_routes_are_hard_removed(self):
        with patch('app.main.configure_logging'):
            paths = create_app().openapi()['paths']
        self.assertFalse(any('/api/v1/ai/' in p for p in paths))
        self.assertIn('/api/v1/web-testing/generation', paths)
        self.assertIn('/api/v1/system/model-configs', paths)
