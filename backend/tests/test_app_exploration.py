import unittest
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

from test_agent_services import FakeResourceRepository
from web_automation.mobile import screen_from_xml, decision_command
from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.schemas.app_exploration import (AppExplorationStart, AppExplorationControl,
    AppExplorationAccept, AppRuntimeState, AppObservation, AppActionReport, AppConnectionReport)
from app.schemas.agent import AgentTaskReportRequest
from app.services.agent_task_service import AgentTaskService
from app.services.app_exploration_service import AppExplorationService
from app.services.app_exploration_control_service import AppExplorationControlService
from app.services.app_exploration_runtime_service import AppExplorationRuntimeService
from app.services.app_exploration_planner_service import AppExplorationPlannerService
from app.services.app_feature_testing_service import AppFeatureTestingService


class AppExplorationTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeResourceRepository()
        self.feature = self.repo.create('app_features',{'name':'Synthetic','project_id':1})
        self.device = self.repo.create('app_devices',{'name':'Phone','data':{
            'platform':'iOS','node_key':'synthetic','wda_url':'http://127.0.0.1:8100'}})
        self.entry = self.repo.create('app_entries',{'name':'App','project_id':1,'data':{'bundle_id':'test.app'}})
        self.model = self.repo.create('ai_models',{'data':{'supports_vision':True}})
        self.node = self.repo.create('agent_nodes',{'data':{'node_key':'synthetic',
            'agent_status':'online','last_seen_at':datetime.now(UTC).isoformat(),
            'capabilities':['app_exploration','app_execution','app_connection']}})
        self.service = AppExplorationService(self.repo)
        self.runtime = AppExplorationRuntimeService(self.repo)
        self.planner = AppExplorationPlannerService(self.repo)
        self.controls = AppExplorationControlService(self.repo)
        self.start_payload = AppExplorationStart(device_id=self.device['id'],entry_id=self.entry['id'],
            model_id=self.model['id'],prompt='输入你好，然后点击发送',approve_effects=True,request_id='synthetic-start-001')
        self.auth = {'node_key':'synthetic','lease_token':'synthetic-lease-token'}
        self.screen = screen_from_xml('<App><Field type="XCUIElementTypeTextField" name="消息"/>'
            '<Button type="XCUIElementTypeButton" name="发送"/><Button type="XCUIElementTypeButton" name="删除"/></App>',
            'test.app',SimpleNamespace(width=390,height=844))

    def task(self):
        public = self.service.start(self.feature['id'],self.start_payload)
        task = self.repo.get('agent_tasks',public['id'])
        task = self.repo.update('agent_tasks',task['id'],{'status':'running','data':{
            **task['data'],**self.auth,'claimed_by':'synthetic',
            'lease_expires_at':(datetime.now(UTC)+timedelta(seconds=120)).isoformat()}})
        self.runtime.connection(task['id'],AppConnectionReport(**self.auth,status='connected',wda_url='http://127.0.0.1:8100'))
        return self.repo.get('agent_tasks',task['id'])

    def observe(self, task):
        return self.runtime.observe(task['id'],AppObservation(**self.auth,
            observation_id=f"observation-{task['data']['live']['revision']:016}",screen=self.screen))

    def apply(self, task, output):
        self.planner.apply(task,deepcopy(task['data']['live']),output)
        return self.repo.get('agent_tasks',task['id'])['data']['live']

    def report(self, task, nonce, status, **kwargs):
        return self.runtime.action(task['id'],AppActionReport(**self.auth,nonce=nonce,status=status,**kwargs))

    def control(self, task, action, **kwargs):
        return self.controls.control(task['id'],self.feature['id'],AppExplorationControl(
            action=action,request_id=f'control-{action}-00001',**kwargs))

    def ready(self, task, action='tap', target=2):
        self.observe(task)
        return self.apply(task,{'kind':'action','step':{'name':'发送消息','action':action,'target_id':target}})

    def test_requires_operation_authorization_and_correct_project(self):
        self.start_payload.approve_effects = False
        with self.assertRaises(BusinessRuleError):
            self.service.start(self.feature['id'],self.start_payload)
        self.start_payload.approve_effects = True
        self.entry['project_id'] = 2
        with self.assertRaises(BusinessRuleError):
            self.service.start(self.feature['id'],self.start_payload)

    def test_new_capability_and_vision_model_required(self):
        self.node['data']['capabilities'] = ['app_execution']
        with self.assertRaises(BusinessRuleError):
            self.task()
        self.node['data']['capabilities'].append('app_exploration')
        self.model['data']['supports_vision'] = False
        with self.assertRaises(BusinessRuleError):
            self.task()

    def test_start_is_idempotent_and_device_exclusive(self):
        task = self.task()
        self.assertEqual(task['id'],self.service.start(self.feature['id'],self.start_payload)['id'])
        self.start_payload.request_id = 'synthetic-start-002'
        with self.assertRaises(BusinessRuleError):
            self.service.start(self.feature['id'],self.start_payload)
        self.assertEqual(1,len(self.repo.tables['agent_tasks']))

    def test_wrong_feature_or_lease_cannot_access(self):
        task = self.task()
        with self.assertRaises(ResourceNotFoundError):
            self.service.get(task['id'],99)
        with self.assertRaises(BusinessRuleError):
            self.runtime.state(task['id'],AppRuntimeState(node_key='other',lease_token='wrong-token'))
        task['data']['lease_expires_at'] = (datetime.now(UTC)-timedelta(seconds=1)).isoformat()
        with self.assertRaises(BusinessRuleError):
            self.runtime.state(task['id'],AppRuntimeState(**self.auth))

    def test_observation_is_idempotent_and_foreground_pinned(self):
        task = self.task()
        self.assertTrue(self.observe(task)['planning'])
        self.assertFalse(self.observe(task)['planning'])
        self.assertNotIn('screen',self.service.public(task)['live'])
        task['data']['live']['phase'] = 'observing'
        screen = {**self.screen,'bundle_id':'other.app'}
        with self.assertRaises(ValueError):
            self.runtime.observe(task['id'],AppObservation(**self.auth,observation_id='other-observation-01',screen=screen))

    def test_sensitive_screen_never_saved(self):
        task = self.task()
        secret = screen_from_xml('<Field type="XCUIElementTypeSecureTextField" label="密码" value="secret"/>',
            'test.app',SimpleNamespace(width=390,height=844))
        with patch('app.services.agent_task_service.AgentTaskService._store_agent_screenshot') as store:
            self.runtime.observe(task['id'],AppObservation(**self.auth,observation_id='secret-observation-01',
                screen=secret,screenshot_base64='synthetic'))
            store.assert_not_called()
        self.assertIsNone(task['data']['live']['preview'])
        self.assertTrue(task['data']['live']['manual_precondition'])
        self.assertNotIn('secret',str(task['data']['live']['screen']))

    def test_action_begins_once_completion_and_followup_append_only(self):
        task = self.task()
        live = self.ready(task)
        nonce = live['command']['nonce']
        self.assertTrue(self.report(task,nonce,'begin')['execute'])
        self.assertFalse(self.report(task,nonce,'begin')['execute'])
        self.report(task,nonce,'success')
        self.report(task,nonce,'success')
        self.assertFalse(self.report(task,nonce,'begin')['execute'])
        self.assertEqual(1,task['data']['live']['cursor'])
        self.apply(task,{'kind':'done','message':'本轮完成，业务未验证'})
        self.control(task,'message',message='接下来查看消息')
        self.assertEqual(1,task['data']['live']['cursor'])
        self.assertEqual(1,len(task['data']['live']['steps']))
        self.assertEqual('observing',task['data']['live']['phase'])

    def test_input_is_separate_editable_and_snapshot_retained(self):
        task = self.task()
        self.observe(task)
        live = self.apply(task,{'kind':'action','step':{'action':'input','target_id':1,'input_key':'message','value':'你好'}})
        nonce = live['command']['nonce']
        self.report(task,nonce,'begin')
        self.report(task,nonce,'success',input_value='你好')
        live = task['data']['live']
        self.assertEqual('你好',live['input_info']['message']['value'])
        self.assertEqual('你好',live['input_snapshot']['message'])
        self.assertEqual('message',live['steps'][0]['input_key'])
        executable = AppFeatureTestingService(self.repo)._steps_for_execution(live['steps'],live['input_info'])
        self.assertEqual('你好',executable[0]['value'])

    def test_missing_or_invented_targets_and_input_are_rejected(self):
        task = self.task()
        self.observe(task)
        with self.assertRaises(ValueError):
            self.apply(task,{'kind':'action','step':{'action':'tap','target_id':999}})
        with self.assertRaises(ValueError):
            self.apply(task,{'kind':'action','step':{'action':'input','target_id':1,'input_key':'message','value':'invented'}})

    def test_danger_confirmation_is_step_scoped(self):
        task = self.task()
        live = self.ready(task,target=3)
        self.assertEqual('waiting_approval',live['phase'])
        nonce = live['nonce']
        self.assertFalse(self.report(task,nonce,'begin')['execute'])
        with self.assertRaises(BusinessRuleError):
            self.control(task,'approve',nonce='wrong')
        self.control(task,'approve',nonce=nonce)
        self.assertTrue(self.report(task,nonce,'begin')['execute'])

    def test_unknown_result_requires_explicit_confirmation(self):
        task = self.task()
        nonce = self.ready(task)['command']['nonce']
        self.report(task,nonce,'begin')
        self.report(task,nonce,'failed')
        with self.assertRaises(BusinessRuleError):
            self.control(task,'resume')
        self.control(task,'confirm_not_executed',nonce=task['data']['live']['nonce'])
        self.assertEqual('observing',task['data']['live']['phase'])
        self.assertEqual([],task['data']['live']['steps'])

    def test_pause_before_begin_revokes_action(self):
        task = self.task()
        nonce = self.ready(task)['command']['nonce']
        self.control(task,'pause')
        with self.assertRaises(BusinessRuleError):
            self.report(task,nonce,'begin')
        self.assertEqual([],task['data']['live']['steps'])

    def test_pause_during_action_preserves_completion(self):
        task = self.task()
        nonce = self.ready(task)['command']['nonce']
        self.report(task,nonce,'begin')
        self.control(task,'pause')
        self.report(task,nonce,'success')
        self.assertEqual('paused',task['data']['live']['phase'])
        self.assertEqual(1,task['data']['live']['cursor'])

    def test_model_result_after_cancel_is_ignored(self):
        task = self.task()
        rev = self.observe(task)['revision']
        client = Mock()
        def cancel(*args):
            self.control(task,'cancel')
            return {'kind':'action','step':{'action':'tap','target_id':2}}
        client.complete_json.side_effect = cancel
        self.planner.client = Mock(return_value=client)
        self.planner.plan(task['id'],rev)
        self.assertEqual('canceled',task['data']['live']['phase'])
        self.assertFalse(task['data']['live'].get('command'))
        self.assertIsNone(client.timeout_sec)

    def test_model_receives_recent_failure_but_not_execution_nonce(self):
        task = self.task()
        rev = self.observe(task)['revision']
        task['data']['live']['timeline'] = [{'name':'点击发送','action':'tap','status':'failed',
            'error':'定位失效','nonce':'private-execution-nonce','outcome_unknown':False}]
        client = Mock()
        client.complete_json.return_value = {'kind':'question','message':'请确认当前页面'}
        self.planner.client = Mock(return_value=client)
        self.planner.plan(task['id'],rev)
        context = json.loads(client.complete_json.call_args.args[1])
        self.assertEqual('failed',context['recent_execution'][0]['status'])
        self.assertNotIn('nonce',context['recent_execution'][0])

    def test_save_actual_steps_without_replay_idempotent_and_evidence_linked(self):
        task = self.task()
        nonce = self.ready(task)['command']['nonce']
        self.report(task,nonce,'begin')
        self.report(task,nonce,'success')
        self.apply(task,{'kind':'done'})
        saved = self.service.accept(task['id'],self.feature['id'],AppExplorationAccept(name='Actual scenario'))
        self.assertEqual(saved,self.service.accept(task['id'],self.feature['id'],AppExplorationAccept(name='Again')))
        scenario = self.repo.get('app_feature_scenarios',saved['id'])
        self.assertEqual(1,len(scenario['data']['operation_steps']))
        self.assertEqual(1,len(self.repo.tables['agent_tasks']))
        report = AgentTaskReportRequest(**self.auth,status='success',result={'records':[{
            'name':'actual','status':'success','data':{'video_url':'/api/v1/app-recordings/synthetic.mp4'}}]})
        AgentTaskService(self.repo).report(task['id'],report)
        AgentTaskService(self.repo).report(task['id'],report)
        self.assertEqual(1,len(self.repo.tables['app_scenario_runs']))
        self.assertEqual('/api/v1/app-recordings/synthetic.mp4',scenario['data']['last_run']['video_url'])

    def test_save_failure_recoverable_without_erasing_actions(self):
        task = self.task()
        task['data']['live'].update(phase='waiting_next',steps=[{'action':'wait','duration_ms':100}])
        with patch.object(AppFeatureTestingService,'create_scenario',side_effect=RuntimeError('synthetic')):
            with self.assertRaises(RuntimeError):
                self.service.accept(task['id'],self.feature['id'],AppExplorationAccept(name='Synthetic'))
        self.assertEqual('waiting_next',task['data']['live']['phase'])
        self.assertEqual(1,len(task['data']['live']['steps']))

    def test_concurrent_save_creates_only_one_scenario(self):
        task = self.task()
        task['data']['live'].update(phase='waiting_next',steps=[{'action':'wait','duration_ms':100}])
        entered, release, duplicate = Event(), Event(), Event()
        original = AppFeatureTestingService.create_scenario
        def save(service, feature_id, payload):
            if entered.is_set():
                duplicate.set()
            entered.set()
            release.wait(2)
            return original(service,feature_id,payload)
        with patch.object(AppFeatureTestingService,'create_scenario',save), ThreadPoolExecutor(max_workers=2) as workers:
            first = workers.submit(self.service.accept,task['id'],self.feature['id'],AppExplorationAccept(name='First'))
            self.assertTrue(entered.wait(1))
            second = workers.submit(self.service.accept,task['id'],self.feature['id'],AppExplorationAccept(name='Second'))
            self.assertFalse(duplicate.wait(.1))
            release.set()
            self.assertEqual(first.result(),second.result())
        self.assertEqual(1,len(self.repo.tables['app_feature_scenarios']))

    def test_failure_archived_once_and_not_marked_verified(self):
        task = self.task()
        report = AgentTaskReportRequest(**self.auth,status='failed',result={})
        AgentTaskService(self.repo).report(task['id'],report)
        AgentTaskService(self.repo).report(task['id'],report)
        self.assertEqual(1,len(self.repo.tables['project_knowledge']))
        self.assertFalse(self.repo.tables['project_knowledge'][0]['data']['verified'])

    def test_manual_and_duplicate_elements_not_automatically_operated(self):
        secret = screen_from_xml('<Field type="XCUIElementTypeSecureTextField" label="密码"/>',
            'test.app',SimpleNamespace(width=390,height=844))
        with self.assertRaises(ValueError):
            decision_command({'step':{'action':'input','target_id':1,'input_key':'password','value':'secret'}},secret)
        duplicate = screen_from_xml('<App><B type="Button" name="发送"/><B type="Button" name="发送"/></App>',
            'test.app',SimpleNamespace(width=390,height=844))
        with self.assertRaises(ValueError):
            decision_command({'step':{'action':'tap','target_id':1}},duplicate)
