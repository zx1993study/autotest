import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from agent_app.executors.app_connection import resolve_device, foreground_identity, AppConnectionError
from agent_app.executors.wda_sessions import WdaSessionPool
from agent_app.executors.app_exploration_executor import LocalAppExplorationExecutor

MODULE = 'agent_app.executors.app_connection'


class NativeAppConnectionTests(unittest.TestCase):
    def test_saved_url_reused_without_scan(self):
        device = {'id':1,'data':{'wda_url':'http://192.168.50.184:8100','udid':'real-phone'}}
        with patch(f'{MODULE}.LocalDeviceDiscovery') as factory:
            factory.return_value.execute.return_value = {'items':[{'wda_url':device['data']['wda_url']}]}
            resolved,_ = resolve_device(device,'test-node')
        self.assertEqual(device['data']['wda_url'],resolved['data']['wda_url'])
        self.assertEqual(1,factory.return_value.execute.call_count)

    def test_legacy_host_and_port_are_reused(self):
        with patch(f'{MODULE}.LocalDeviceDiscovery') as factory:
            factory.return_value.execute.return_value = {'items':[{'wda_url':'http://192.168.50.184:8100'}]}
            resolved,_ = resolve_device({'data':{'wda_host':'192.168.50.184','wda_port':8100}},'test-node')
        self.assertEqual('http://192.168.50.184:8100',resolved['data']['wda_url'])

    def test_changed_address_requires_real_reported_udid(self):
        device = {'data':{'wda_url':'http://192.168.50.184:8100','udid':'real-phone'}}
        with patch(f'{MODULE}.LocalDeviceDiscovery') as factory:
            scan = factory.return_value.execute
            scan.side_effect = [{'items':[]},{'items':[{'wda_url':'http://192.168.50.22:8100','reported_udid':'other-phone'}]}]
            with self.assertRaises(AppConnectionError):
                resolve_device(device,'test-node')
            scan.side_effect = [{'items':[]},{'items':[{'wda_url':'http://192.168.50.22:8100','reported_udid':'real-phone'}]}]
            resolved,_ = resolve_device(device,'test-node')
            self.assertEqual('http://192.168.50.22:8100',resolved['data']['wda_url'])
            self.assertEqual('192.168.50.184/24',scan.call_args.args[0]['subnet'])

    def test_cached_address_with_wrong_reported_identity_is_not_used(self):
        with patch(f'{MODULE}.LocalDeviceDiscovery') as factory:
            factory.return_value.execute.return_value = {'items':[{'reported_udid':'other-phone'}]}
            with self.assertRaises(AppConnectionError):
                resolve_device({'data':{'wda_url':'http://192.168.50.184:8100','udid':'real-phone'}},'test-node')

    def test_real_bundle_and_xml_application_name_not_visual_guess(self):
        session = Mock()
        session.app_current.return_value = {'bundleId':'test.real.app','name':''}
        session.source.return_value = '<App><Application type="XCUIElementTypeApplication" name="Target App"/></App>'
        self.assertEqual({'bundle_id':'test.real.app','app_name':'Target App'},foreground_identity(session))

    def test_foreground_changed_during_read_is_rejected(self):
        session = Mock()
        session.app_current.side_effect = [{'bundleId':'test.real.app','name':'App'}, {'bundleId':'test.other.app'}]
        with self.assertRaises(AppConnectionError):
            foreground_identity(session)

    def test_bootstrap_session_rekey_is_reused_and_invalidates_on_failure(self):
        session,client = Mock(),Mock()
        client.session.return_value = session
        pool = WdaSessionPool(Path('unused'),lambda _:client)
        device = {'data':{'wda_url':'http://127.0.0.1:8100','udid':'synthetic'}}
        with pool.connect(device,''):
            pool.bind(device,'test.app',session)
        with pool.connect(device,'test.app') as (_,reused):
            self.assertTrue(reused)
        self.assertEqual(1,client.session.call_count)
        with self.assertRaises(RuntimeError):
            with pool.connect(device,'test.app'):
                pool.bind(device,'test.other',session)
                raise RuntimeError('interrupted')
        self.assertFalse(pool.sessions)

    def test_canceled_before_connect_never_creates_session_or_scans(self):
        api,pool = Mock(),Mock()
        api.app_exchange.return_value = {'phase':'canceled'}
        executor = LocalAppExplorationExecutor(SimpleNamespace(artifacts_dir=Path('unused'),node_key='synthetic'),api,pool)
        with patch('agent_app.executors.app_exploration_executor.resolve_device') as resolve:
            result = executor.execute(1,'lease',{'resolve_connection':True,'device':{'id':1},'bundle_id':'',
                'feature_id':2,'project_id':1,'record_video':False})
        self.assertTrue(result['canceled'])
        pool.connect.assert_not_called()
        resolve.assert_not_called()
