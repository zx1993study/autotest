import base64
import io
import json
import unittest
from datetime import UTC, datetime
from unittest.mock import Mock
from zipfile import ZipFile

from app.core.exceptions import BusinessRuleError
from app.schemas.ai import WebVisionDiscoveryRequest
from app.schemas.web_operation import WebOperationControl, WebOperationState, WebRecordingAccept, WebRecordingStart
from app.services.web_feature_testing_service import WebFeatureTestingService
from app.services.web_operation_service import WebOperationService
from app.services.web_page_management_service import WebPageManagementService
from app.services.web_recording_service import WebRecordingService
from app.services.web_script_export_service import WebScriptExportService
from app.services.web_vision_discovery_service import FeatureCapture, WebVisionDiscoveryService
from test_agent_services import FakeResourceRepository
from web_automation.discovery.dom import safe_dom


class WebOperationWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.repo = FakeResourceRepository()
        group = WebPageManagementService(self.repo).create_group({'name':'Form','project_id':1,'url':'https://example.test/login'})
        self.service = WebFeatureTestingService(self.repo)
        self.feature = self.service.save_feature(group['id'], {'name':'Login','feature_type':'login'})
        self.manual = {'name':'Password','action':'manual','locator_type':'label','locator':'Password'}
        self.dom = ({'tag':'input','type':'password','name':'password','label':'Password','required':True,'required_known':True,
                     'locators':[{'locator_type':'label','locator':'Password'}],'value':'never-store'},)

    def task(self, steps=None):
        return self.repo.create('agent_tasks', {'status':'running','data':{'task_type':'web_replay','claimed_by':'node-test','lease_token':'lease',
             'payload':{'candidate':{'steps':steps or [self.manual]},'source_id':self.feature['id'],'project_id':1}}})

    def test_null_rules_and_manual_secret_are_normalized_without_assertion(self):
        output = {'parameters':[{'key':'password','label':'Password','required':None,'condition':None,'validation':None,'options':None}],
                  'candidate':{'name':'Login','steps':[{'name':'Password','action':'fill','locator_type':'label','locator':'Password','value':'never-store'}],
                               'input_info':{'password':'never-store'}}}
        capture = FeatureCapture('one','Login','capture.png',None,dom=self.dom)
        self.service.persist_discovery(self.feature,capture,output,[])
        detail = self.service.detail(self.feature['id'])
        proposal = detail['feature']['data']['discovery_proposal']
        self.assertEqual('password',proposal['parameters'][0]['type'])
        self.assertTrue(proposal['parameters'][0]['required'])
        self.assertEqual('fill',proposal['candidate']['steps'][0]['action'])
        self.assertTrue(proposal['candidate']['steps'][0]['sensitive'])
        self.assertNotIn('never-store',json.dumps(proposal))
        self.service.accept_discovery(self.feature['id'])
        self.assertTrue(self.service.detail(self.feature['id'])['cases'])

    def test_model_failure_keeps_screenshot_and_dom_attached(self):
        discovery = WebVisionDiscoveryService(self.repo)
        discovery._extract_feature_elements_batch = Mock(side_effect=RuntimeError('AI offline'))
        saved, errors = discovery._extract_and_save_captures(Mock(),WebVisionDiscoveryRequest(project_id=1,page_id=self.feature['id']),self.feature,
                                                           [FeatureCapture('one','Login','capture.png',None,dom=self.dom)])
        self.assertFalse(saved)
        self.assertIn('AI offline',errors[0]['error'])
        detail = self.service.detail(self.feature['id'])
        self.assertEqual(['capture.png'],detail['screenshots'])
        self.assertNotIn('never-store',json.dumps(detail['feature']['data']['dom_snapshot']))

    def test_manual_continue_is_step_scoped_and_cannot_repeat(self):
        task = self.task()
        service = WebOperationService(self.repo)
        request = WebOperationState(node_key='node-test',lease_token='lease',phase='waiting_input',step=1)
        state = service.state(task['id'],request)
        nonce = state['waiting_input']['nonce']
        with self.assertRaises(BusinessRuleError):
            service.control(task['id'],WebOperationControl(action='continue',nonce='stale'))
        service.control(task['id'],WebOperationControl(action='continue',nonce=nonce))
        self.assertTrue(service.state(task['id'],request.model_copy(update={'phase':'state'}))['waiting_input']['confirmed'])
        with self.assertRaises(BusinessRuleError):
            service.control(task['id'],WebOperationControl(action='continue',nonce=nonce))

    def test_foreign_lease_and_nonmanual_step_are_rejected(self):
        task = self.task([{'action':'click'}])
        service = WebOperationService(self.repo)
        for node in ('node-test','foreign'):
            with self.assertRaises(BusinessRuleError):
                service.state(task['id'],WebOperationState(node_key=node,lease_token='lease',phase='waiting_input',step=1))
        service.control(task['id'],WebOperationControl(action='cancel'))
        self.assertTrue(task['data']['cancel_requested'])

    def test_recording_requires_upgrade_and_accept_is_idempotent(self):
        self.repo.create('agent_nodes',{'status':'active','data':{'node_key':'node-test','agent_status':'online','last_seen_at':datetime.now(UTC).isoformat(),'capabilities':['web_replay']}})
        service = WebRecordingService(self.repo)
        request = WebRecordingStart(node_key='node-test',approve_side_effects=True)
        with self.assertRaises(BusinessRuleError):
            service.start(self.feature['id'],request)
        self.repo.tables['agent_nodes'][0]['data']['capabilities'].append('web_recording')
        task = self.repo.get('agent_tasks',service.start(self.feature['id'],request)['agent_task_id'])
        task['status'] = 'success'
        task['data']['result'] = {'records':[{'data':{'screenshots':[{'screenshot_file':'record.png'}]}}]}
        accept = WebRecordingAccept(task_id=task['id'],candidate={'name':'Recorded','steps':[self.manual],'input_info':{}})
        first = service.accept(self.feature['id'],accept)
        self.assertEqual(first['id'],service.accept(self.feature['id'],accept)['id'])
        self.assertEqual(1,len(self.repo.tables['web_test_cases']))

    def test_export_draft_has_separate_inputs_and_portable_runtime(self):
        candidate = {'name':'Draft','steps':[{'action':'fill','locator_type':'label','locator':'Name','value':'{{name}}'}],'input_info':{'name':'Synthetic'}}
        version = self.service.save_version(self.feature['id'],candidate)
        output = WebScriptExportService(self.repo).feature(self.feature['id'],version['id'])
        self.assertEqual('draft',output['status'])
        with ZipFile(io.BytesIO(base64.b64decode(output['bundle_base64']))) as archive:
            self.assertEqual({'name':'Synthetic'},json.loads(archive.read('inputs.json')))
            self.assertNotIn('input_info',json.loads(archive.read('steps.json')))
            self.assertIn('web_automation/engines/playwright.py',archive.namelist())
            compile(archive.read('run.py'),'<export>','exec')

    def test_dom_allowlist_excludes_values_and_secrets(self):
        rows = safe_dom(self.dom)
        self.assertTrue(rows[0]['sensitive'])
        self.assertNotIn('value',rows[0])


if __name__ == '__main__':
    unittest.main()
