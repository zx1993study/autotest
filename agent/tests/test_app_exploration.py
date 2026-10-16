import unittest
import tempfile
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from web_automation.mobile import screen_from_xml, decision_command
from agent_app.executors.app_exploration_executor import LocalAppExplorationExecutor
from agent_app.executors.mobile_observation import capture
from agent_app.executors.wda_actions import WdaActions

MODULE = 'agent_app.executors.app_exploration_executor'


class AppExplorationExecutorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = SimpleNamespace(artifacts_dir=Path(self.temp.name))
        self.api = Mock()
        self.session = Mock()
        self.element = Mock()
        self.session.return_value.find_elements.return_value = [self.element]
        self.screen = screen_from_xml('<B type="Button" name="发送"/>','test.app',
            SimpleNamespace(width=390,height=844))
        self.command = decision_command({'step':{'name':'发送','action':'tap','target_id':1}},self.screen)
        self.command['nonce'] = 'synthetic-command-0001'
        self.payload = {'device':{'id':1},'feature_id':2,'project_id':1,'bundle_id':'test.app','record_video':False}
        self.pool = Mock()
        @contextmanager
        def connect(*args):
            yield self.session, True
        self.pool.connect.side_effect = connect
        self.executor = LocalAppExplorationExecutor(self.config,self.api,self.pool,sleep=lambda _:None)
        self.patches = [patch(f'{MODULE}.capture',return_value=(self.screen,None,None)),
            patch(f'{MODULE}.requested',return_value=False)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def test_success_records_once_and_uses_same_session(self):
        def exchange(task,lease,operation,payload):
            if operation == 'state':
                return states.pop(0)
            if operation == 'action':
                return {'execute':payload['status']=='begin'}
            return {}
        states = [{'phase':'observing'},{'phase':'planning'},{'phase':'ready','command':self.command},
            {'phase':'waiting_user'},{'phase':'finishing','cursor':1,'steps':[self.command['step']],
             'timeline':[{'status':'success'}],'input_snapshot':{'message':'actual'}}]
        self.api.app_exchange.side_effect = exchange
        result = self.executor.execute(1,'synthetic',self.payload)
        self.pool.connect.assert_called_once()
        self.element.click.assert_called_once()
        self.session.return_value.find_elements.assert_called_once()
        self.session.return_value.get.assert_not_called()
        self.assertEqual(0,result['failed_count'])
        self.assertEqual('操作完成，业务结果未验证',result['records'][0]['data']['result_label'])
        self.assertEqual({'message':'actual'},result['records'][0]['data']['input_snapshot'])

    def test_lost_completion_ack_stops_without_repeating_action(self):
        def exchange(task,lease,operation,payload):
            if operation == 'state':
                return {'phase':'ready','command':self.command}
            if payload['status'] == 'success':
                raise ConnectionError('ack lost')
            return {'execute':True}
        self.api.app_exchange.side_effect = exchange
        result = self.executor.execute(1,'synthetic',self.payload)
        self.assertEqual(1,result['failed_count'])
        self.element.click.assert_called_once()
        self.assertIn('不会自动重复',result['records'][0]['data']['error'])

    def test_stale_screen_and_ambiguous_locator_never_click(self):
        self.api.app_exchange.return_value = {'execute':True}
        for ambiguous in (False,True):
            self.session.return_value.find_elements.return_value = [self.element,self.element] if ambiguous else [self.element]
            with patch(f'{MODULE}.capture',return_value=({**self.screen,'hash':'changed'} if not ambiguous else self.screen,None,None)):
                self.executor.action(1,'synthetic',self.payload,self.session,WdaActions(self.session),self.command)
            self.assertEqual('stale',self.api.app_exchange.call_args.args[3]['status'])
        self.element.click.assert_not_called()

    def test_no_begin_authorization_no_device_call(self):
        self.api.app_exchange.return_value = {'execute':False}
        self.executor.action(1,'synthetic',self.payload,self.session,WdaActions(self.session),self.command)
        self.session.assert_not_called()
        self.element.click.assert_not_called()

    def test_failure_does_not_retry_and_cancellation_keeps_partial_result(self):
        self.api.app_exchange.return_value = {'execute':True}
        self.element.click.side_effect = RuntimeError('device failure')
        self.executor.action(1,'synthetic',self.payload,self.session,WdaActions(self.session),self.command)
        self.element.click.assert_called_once()
        self.assertEqual('failed',self.api.app_exchange.call_args.args[3]['status'])
        self.api.app_exchange.return_value = {'phase':'canceled','cursor':1,'steps':[{'action':'tap'}]}
        result = self.executor.execute(1,'synthetic',self.payload)
        self.assertTrue(result['canceled'])
        self.assertEqual(1,result['records'][0]['data']['step_count'])

    def test_sensitive_fields_after_element_limit_disable_screenshot(self):
        session = Mock()
        session.app_current.return_value = {'bundleId':'test.app'}
        session.window_size.return_value = SimpleNamespace(width=390,height=844)
        session.source.return_value = '<App>'+''.join(f'<B type="Button" name="{i}"/>' for i in range(220))+\
            '<Field type="XCUIElementTypeSecureTextField" name="密码" value="secret"/></App>'
        screen, encoded, frame = capture(session,'test.app')
        self.assertTrue(screen['sensitive'])
        self.assertIsNone(encoded)
        self.assertIsNone(frame)
        session.screenshot.assert_not_called()
        self.assertNotIn('secret',str(screen))

    def test_wrong_foreground_bundle_stops_before_source_capture(self):
        session = Mock()
        session.app_current.return_value = {'bundleId':'other.app'}
        with self.assertRaises(ValueError):
            capture(session,'test.app')
        session.source.assert_not_called()

    def test_missing_bundle_is_discovered_and_same_session_rebound(self):
        self.payload['bundle_id'] = ''
        states = [{'phase':'connecting'}, {'phase':'observing','bundle_id':'test.app'}, {'phase':'finishing'}]
        def exchange(task,lease,operation,payload):
            return states.pop(0) if operation == 'state' else {'accepted':True,'bundle_id':'test.app'}
        self.api.app_exchange.side_effect = exchange
        with patch(f'{MODULE}.foreground_identity',return_value={'bundle_id':'test.app','app_name':'App'}):
            result = self.executor.execute(1,'synthetic',self.payload)
        self.pool.connect.assert_called_once()
        self.pool.bind.assert_called_once_with(self.payload['device'],'test.app',self.session)
        self.element.click.assert_not_called()
        self.assertEqual('test.app',result['records'][0]['data']['bundle_id'])
        self.assertEqual(0,result['failed_count'])

    def test_bootstrap_tap_uses_desktop_identity_not_empty_bundle(self):
        self.payload['bundle_id'] = ''
        self.command.update(app_bootstrap=True,expected_bundle_id='com.apple.springboard')
        self.api.app_exchange.return_value = {'execute':True}
        with patch(f'{MODULE}.capture',return_value=(self.screen,None,None)) as capture_screen:
            self.executor.action(1,'synthetic',self.payload,self.session,WdaActions(self.session),self.command)
        capture_screen.assert_called_once_with(self.session,'com.apple.springboard')
        self.element.click.assert_called_once()


if __name__ == '__main__':
    unittest.main()
