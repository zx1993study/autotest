import json
import unittest

from agent_app.executors.result_builder import build_execution_record
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


if __name__ == '__main__':
    unittest.main()
