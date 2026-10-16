import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import test_app_exploration as fixtures
from app.core.exceptions import BusinessRuleError
from app.schemas.app_exploration import AppConnectionReport, AppObservation
from web_automation.mobile import screen_from_xml


class AppConnectionTests(unittest.TestCase):
    setUp = fixtures.AppExplorationTests.setUp
    task = fixtures.AppExplorationTests.task
    apply = fixtures.AppExplorationTests.apply
    control = fixtures.AppExplorationTests.control
    report = fixtures.AppExplorationTests.report

    def missing_app(self):
        self.entry['data'] = {'bundle_id':None, 'no_reset':True}
        return self.task()

    def identify(self, task, name='App', bundle='test.real.app'):
        return self.runtime.connection(task['id'], AppConnectionReport(**self.auth,
            status='identified', bundle_id=bundle, app_name=name))

    def desktop(self, task, icons=None):
        xml = icons or '<I type="XCUIElementTypeIcon" name="App"/>'
        screen = screen_from_xml(f'<App>{xml}</App>', 'com.apple.springboard', SimpleNamespace(width=390,height=844))
        self.runtime.observe(task['id'], AppObservation(**self.auth, observation_id='desktop-observation-001',screen=screen))
        return screen

    def test_missing_id_starts_connecting_with_saved_address(self):
        task = self.missing_app()
        self.assertEqual('connecting',task['data']['live']['phase'])
        self.assertEqual('http://127.0.0.1:8100',task['data']['payload']['device']['data']['wda_url'])
        self.assertEqual('',task['data']['payload']['bundle_id'])

    def test_identity_persisted_and_next_task_reuses_it(self):
        task = self.missing_app()
        self.assertEqual('test.real.app',self.identify(task)['bundle_id'])
        self.assertTrue(self.entry['data']['no_reset'])
        self.assertEqual('foreground_name',self.entry['data']['bundle_discovery']['source'])
        self.assertEqual('observing',task['data']['live']['phase'])
        self.control(task,'cancel')
        task['status'] = 'canceled'
        self.start_payload.request_id = 'new-app-request-00001'
        self.assertEqual('test.real.app',self.service.start(self.feature['id'],self.start_payload)['bundle_id'])

    def test_wrong_or_unknown_name_requires_confirmation_and_fresh_read(self):
        task = self.missing_app()
        self.identify(task,name='')
        self.assertEqual('waiting_app_confirmation',task['data']['live']['phase'])
        self.assertIsNone(self.entry['data']['bundle_id'])
        self.control(task,'confirm_app',nonce=task['data']['live']['nonce'])
        self.assertIsNone(self.entry['data']['bundle_id'])
        self.identify(task,name='')
        self.assertEqual('user_confirmed',self.entry['data']['bundle_discovery']['source'])

    def test_app_changed_after_confirmation_is_not_bound(self):
        task = self.missing_app()
        self.identify(task,name='')
        self.control(task,'confirm_app',nonce=task['data']['live']['nonce'])
        self.identify(task,name='Other',bundle='test.other.app')
        self.assertIsNone(self.entry['data']['bundle_id'])
        self.assertEqual('waiting_app_confirmation',task['data']['live']['phase'])

    def test_desktop_and_wda_runner_cannot_be_saved(self):
        task = self.missing_app()
        for bundle in ('com.apple.springboard','com.yios.wda.xctrunner','invented id'):
            with self.assertRaises(BusinessRuleError):
                self.identify(task,bundle=bundle)
        self.assertIsNone(self.entry['data']['bundle_id'])

    def test_cancel_pause_and_wrong_lease_prevent_binding(self):
        task = self.missing_app()
        self.control(task,'pause')
        self.assertFalse(self.identify(task)['accepted'])
        self.control(task,'cancel')
        self.assertFalse(self.identify(task)['accepted'])
        with self.assertRaises(BusinessRuleError):
            self.runtime.connection(task['id'], AppConnectionReport(node_key='other',lease_token='wrong-token',
                status='identified',bundle_id='test.real.app',app_name='App'))
        self.assertIsNone(self.entry['data']['bundle_id'])

    def test_existing_bundle_is_never_overwritten(self):
        task = self.missing_app()
        self.entry['data']['bundle_id'] = 'test.existing.app'
        with self.assertRaises(BusinessRuleError):
            self.identify(task)
        self.assertEqual('test.existing.app',self.entry['data']['bundle_id'])
        self.assertEqual('',task['data']['payload']['bundle_id'])

    def test_verified_new_address_only(self):
        task = self.missing_app()
        self.device['data']['udid'] = 'real-device-123'
        payload = AppConnectionReport(**self.auth,status='connected',wda_url='http://192.168.50.12:8100')
        with self.assertRaises(BusinessRuleError):
            self.runtime.connection(task['id'],payload)
        payload.reported_udid = 'real-device-123'
        self.runtime.connection(task['id'],payload)
        self.assertEqual(payload.wda_url,self.device['data']['wda_url'])

    def test_bootstrap_tap_is_once_and_not_a_business_step(self):
        task = self.missing_app()
        self.desktop(task)
        self.apply(task,{'kind':'action','step':{'action':'tap','target_id':1}})
        command = task['data']['live']['command']
        self.assertTrue(command['app_bootstrap'])
        self.assertTrue(self.report(task,command['nonce'],'begin')['execute'])
        self.assertFalse(self.report(task,command['nonce'],'begin')['execute'])
        self.report(task,command['nonce'],'success')
        self.assertFalse(self.report(task,command['nonce'],'begin')['execute'])
        self.assertFalse(self.report(task,command['nonce'],'success')['execute'])
        self.assertEqual(0,task['data']['live']['cursor'])
        self.assertEqual([],task['data']['live']['steps'])
        self.assertEqual('connecting',task['data']['live']['phase'])
        task['data']['live']['observation_id'] = None
        self.desktop(task)
        self.apply(task,{'kind':'action','step':{'action':'tap','target_id':1}})
        self.assertEqual('waiting_app',task['data']['live']['phase'])

    def test_model_cannot_click_wrong_duplicate_or_non_icon_target(self):
        for icons,target in (('<I type="XCUIElementTypeIcon" name="Other"/>',1),
                             ('<I type="XCUIElementTypeIcon" name="App"/><I type="XCUIElementTypeIcon" name="App"/>',1),
                             ('<I type="Button" name="App"/>',1)):
            with self.subTest(icons=icons):
                task = self.missing_app()
                self.desktop(task,icons)
                self.apply(task,{'kind':'action','step':{'action':'tap','target_id':target}})
                self.assertEqual('waiting_app',task['data']['live']['phase'])
                self.assertFalse(task['data']['live'].get('command'))
                self.control(task,'cancel')
                task['status'] = 'canceled'
                self.start_payload.request_id += 'x'

    def test_model_cannot_supply_bundle_id_and_gets_target_app(self):
        task = self.missing_app()
        self.desktop(task)
        client = Mock()
        client.complete_json.return_value = {'kind':'action','bundle_id':'fake.bundle', 'step':{'action':'tap','target_id':1}}
        self.planner.client = Mock(return_value=client)
        self.planner.plan(task['id'],task['data']['live']['revision'])
        self.assertIn('target_app',client.complete_json.call_args.args[1])
        self.assertEqual('',task['data']['payload']['bundle_id'])
        self.assertIsNone(self.entry['data']['bundle_id'])

    def test_concurrent_update_rolls_back_both_task_and_entry(self):
        task = self.missing_app()
        previous = deepcopy(task['data'])
        original = self.repo.resolve_app_connection
        def concurrent(task_id,node_key,transition):
            self.entry['data']['bundle_id'] = 'test.concurrent.app'
            return original(task_id,node_key,transition)
        self.repo.resolve_app_connection = concurrent
        with self.assertRaises(BusinessRuleError):
            self.identify(task)
        self.assertEqual(previous,task['data'])
        self.assertEqual('test.concurrent.app',self.entry['data']['bundle_id'])
