import json
import os
import tempfile
import unittest
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.services.web_case_secret_service import WebCaseSecretService
from app.services.web_feature_testing_service import WebFeatureTestingService
from app.services.web_page_management_service import WebPageManagementService
from test_agent_services import FakeResourceRepository


class WebLoginInputsTest(unittest.TestCase):
    def setUp(self):
        self.storage = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {'AUTOTEST_STORAGE_DIR':self.storage.name})
        self.environment.start()
        self.repo = FakeResourceRepository()
        self.service = WebFeatureTestingService(self.repo)
        group = WebPageManagementService(self.repo).create_group({'name':'Login', 'project_id':1, 'url':'https://example.test/login'})
        self.parameters = [{'key':key, 'label':label, 'type':'manual', 'locator_type':'label', 'locator':locator} for key,label,locator in (
            ('manual_1','人工输入账号','Account'), ('manual_2','人工输入密码','Password'), ('manual_3','输入验证码','Captcha'))]
        self.feature = self.service.save_feature(group['id'], {'name':'Login', 'feature_type':'login', 'parameters':self.parameters})
        self.version = self.service.save_version(self.feature['id'], {'name':'Login', 'steps':[
            {'name':p['label'], 'action':'manual','locator_type':'label','locator':p['locator']} for p in self.parameters
        ] + [{'action':'click','locator_type':'text','locator':'Login'}]})

    def tearDown(self):
        self.environment.stop()
        self.storage.cleanup()

    def save(self, password='synthetic-secret', **kwargs):
        inputs = {'manual_1':'synthetic-user'}
        if password is not None:
            inputs['manual_2'] = password
        return self.service.save_case(self.feature['id'], {'name':'Login input', 'input_info':inputs, **kwargs})

    def test_legacy_manual_account_and_password_become_editable_without_changing_version(self):
        row = self.repo.tables['web_function_versions'][0]
        row['data']['parameters'] = deepcopy(self.parameters)
        original = deepcopy(row)
        detail = self.service.detail(self.feature['id'])
        self.assertEqual(['text','password','manual'], [p['type'] for p in detail['versions'][0]['data']['parameters']])
        self.assertEqual(original, self.repo.tables['web_function_versions'][0])

    def test_save_encrypts_and_public_case_does_not_disclose_password(self):
        saved = self.save()
        raw = self.repo.get('web_test_cases', saved['id'])
        self.assertNotIn('synthetic-secret', json.dumps(raw))
        self.assertNotIn('secret_inputs', saved['data'])
        self.assertEqual(['manual_2'], saved['data']['secret_keys'])
        self.assertEqual('fill', saved['steps'][0]['action'])
        self.assertTrue(saved['steps'][1]['sensitive'])
        self.assertEqual('manual', saved['steps'][2]['action'])
        self.assertEqual({'manual_2':'synthetic-secret'}, WebCaseSecretService(self.repo).reveal(raw['data']['secret_inputs']))

    def test_edit_retains_unmodified_password_and_copy_is_independent(self):
        saved = self.save()
        edited = self.service.save_case(self.feature['id'], {'name':'Edited', 'input_info':{'manual_1':'other-user'}}, saved['id'])
        original_secret = deepcopy(self.repo.get('web_test_cases', edited['id'])['data']['secret_inputs'])
        copied = self.save('wrong-secret', copy_from_case_id=saved['id'], allow_invalid_inputs=True)
        self.assertNotEqual(original_secret, self.repo.get('web_test_cases', copied['id'])['data']['secret_inputs'])
        self.assertEqual(original_secret, self.repo.get('web_test_cases', edited['id'])['data']['secret_inputs'])
        empty = self.service.save_case(self.feature['id'], {'name':'Empty password', 'input_info':{'manual_2':''}, 'allow_invalid_inputs':True}, saved['id'])
        self.assertEqual({'manual_2':''}, WebCaseSecretService(self.repo).reveal(self.repo.get('web_test_cases', empty['id'])['data']['secret_inputs']))

    def test_captcha_cannot_be_stored_and_foreign_copy_rejected(self):
        with self.assertRaises(BusinessRuleError):
            self.save(input_info={'manual_3':'1234'})
        foreign = self.repo.create('web_test_cases', {'name':'Foreign', 'source_id':999, 'project_id':2})
        with self.assertRaises(ResourceNotFoundError):
            self.save(copy_from_case_id=foreign['id'])

    def test_runtime_requires_own_running_unexpired_lease_and_uses_task_snapshot(self):
        saved = self.save()
        raw = deepcopy(self.repo.get('web_test_cases', saved['id']))
        task = self.repo.create('agent_tasks', {'status':'running','data':{
            'claimed_by':'test-node','lease_token':'lease','lease_expires_at':(datetime.now(UTC)+timedelta(minutes=1)).isoformat(),
            'payload':{'case_type':'WEB','cases':[raw]}}})
        service = WebCaseSecretService(self.repo)
        with self.assertRaises(BusinessRuleError):
            service.task_inputs(task['id'], 'foreign-node', 'lease')
        with self.assertRaises(BusinessRuleError):
            service.task_inputs(task['id'], 'test-node', 'bad-lease')
        with self.assertRaises(BusinessRuleError):
            self.service.save_case(self.feature['id'], {'name':'Updated', 'input_info':{'manual_2':'later-secret'}}, saved['id'])
        self.assertEqual({str(saved['id']):{'manual_2':'synthetic-secret'}}, service.task_inputs(task['id'],'test-node','lease'))
        task['data']['lease_expires_at'] = (datetime.now(UTC)-timedelta(seconds=1)).isoformat()
        with self.assertRaises(BusinessRuleError):
            service.task_inputs(task['id'], 'test-node', 'lease')


if __name__ == '__main__':
    unittest.main()
