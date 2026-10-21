import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from agent_app.executors.result_builder import build_execution_record
from agent_app.executors.web_case_executor import LocalWebCaseExecutor
from agent_app.executors.web_secret_redaction import redact_record
from web_automation.compiler import ExecutionPlanCompiler


class WebSecretInputsTest(unittest.TestCase):
    def case(self, password='synthetic-secret'):
        return {'id':1, 'name':'Login', 'steps':[{'action':'fill','locator_type':'label','locator':'Password','value':'{{password}}','sensitive':True,'input_key':'password'}],
                'data':{'request':{'url':'https://example.test/login'}, 'variables':{},'secret_inputs':{'password':'encrypted-snapshot'},'runtime_inputs':{'password':password}}}

    def test_password_is_literal_even_when_it_contains_dynamic_syntax(self):
        password = 'literal{{timestamp}}\\{{not-a-variable}}'
        case = ExecutionPlanCompiler().compile_case(self.case(password),{})
        self.assertEqual(password,case.steps[0]['value'])

    def test_result_screenshot_masks_sensitive_fields_for_success_and_failure(self):
        import asyncio

        case = ExecutionPlanCompiler().compile_case(self.case(), {})
        with tempfile.TemporaryDirectory() as directory:
            executor = LocalWebCaseExecutor(Path(directory))

            async def write_png(**kwargs):
                Path(kwargs['path']).write_bytes(b'\x89PNG\r\n\x1a\n')

            page = Mock(screenshot=AsyncMock(side_effect=write_png))
            for error in (None, 'Business assertion failed'):
                shot = asyncio.run(executor._capture_screenshot(page, case, case.steps[0], error))
                self.assertEqual(error, shot['error'])
                self.assertIn('screenshot_base64', shot)
                self.assertFalse(page.screenshot.call_args.kwargs['full_page'])
                self.assertGreaterEqual(len(page.screenshot.call_args.kwargs['mask']), 2)

    def test_missing_protected_runtime_input_cannot_execute(self):
        case = self.case()
        case['data'].pop('runtime_inputs')
        with self.assertRaisesRegex(ValueError,'Protected inputs'):
            ExecutionPlanCompiler().compile_case(case,{})

    def test_record_redacts_password_steps_errors_dynamic_values_and_auth_state(self):
        case = ExecutionPlanCompiler().compile_case(self.case(),{})
        result = {'steps':list(case.steps), 'events':[{'error':'fill synthetic-secret failed'}], 'cookies':[{'value':'session-secret'}], 'storage_state':{'origins':[{'value':'session-secret'}]}}
        record = build_execution_record(case.raw,{},'failed','synthetic-secret failed',result,'synthetic-secret failed')
        protected = redact_record(record,case.raw)
        self.assertNotIn('synthetic-secret',json.dumps(protected))
        self.assertNotIn('session-secret',json.dumps(protected))
        self.assertEqual('[redacted]',protected['data']['steps'][0]['value'])

    def test_authenticated_page_without_password_does_not_return_session_secrets(self):
        record = {'description': 'session-cookie failed', 'data': {
            'cookies': [{'value': 'session-cookie'}],
            'storage_state': {'cookies': [{'value': 'session-cookie'}]},
            'error': 'request Bearer session-header failed', 'steps': [],
        }}
        protected = redact_record(record, {'data': {}}, {
            'cookies': [{'value': 'session-cookie'}],
            'headers': {'Authorization': 'Bearer session-header'},
        })
        self.assertNotIn('session-cookie', json.dumps(protected))
        self.assertNotIn('session-header', json.dumps(protected))
        self.assertEqual([], protected['data']['cookies'])
        self.assertEqual({}, protected['data']['storage_state'])

    def test_unprotected_login_can_still_explicitly_produce_cookie_auth(self):
        record = {'data': {'cookies': [{'value': 'legacy-login-cookie'}]}}
        self.assertEqual(record, redact_record(record, {'data': {}}))

    def test_executor_redacts_injected_auth_without_secret_input_fields(self):
        cookies = [{'name': 'session', 'value': 'synthetic-session-cookie'}]

        async def replay(case, config, steps, result):
            result.update(cookies=cookies, storage_state={'cookies': cookies}, step_count=1)

        with tempfile.TemporaryDirectory() as directory:
            executor = LocalWebCaseExecutor(Path(directory))
            executor._run_playwright = AsyncMock(side_effect=replay)
            result = executor.execute({
                'execution': {'config': {'engine': 'playwright'}},
                'cases': [{'id': 1, 'name': 'Customer list', 'steps': [{'action': 'assert', 'expected': 'Customers'}]}],
                'context': {'auth_context': {'cookies': cookies}},
            })

        self.assertEqual('success', result['records'][0]['status'])
        self.assertNotIn('synthetic-session-cookie', json.dumps(result))
        self.assertEqual([], result['records'][0]['data']['cookies'])
        self.assertEqual({}, result['records'][0]['data']['storage_state'])


if __name__ == '__main__':
    unittest.main()
