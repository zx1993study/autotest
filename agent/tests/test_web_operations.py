import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from agent_app.api.client import AgentApiError
from agent_app.api.tasks import AgentTaskApi

from agent_app.executors.web_manual_input import outcome_metadata, wait_manual_input
from agent_app.runtime.task_cancelled import TaskCancelled
from web_automation.discovery.recording import recording_candidate


class WebOperationsTest(unittest.IsolatedAsyncioTestCase):
    def test_read_only_status_poll_recovers_from_connection_reset(self):
        client = SimpleNamespace(post=Mock(side_effect=[ConnectionResetError(), {'cancel_requested': False}]))
        api = AgentTaskApi(client, SimpleNamespace(node_key='test-node'))
        with patch('agent_app.api.tasks.time.sleep'):
            self.assertEqual({'cancel_requested': False}, api.web_state(1, 'lease'))
        self.assertEqual(2, client.post.call_count)

    def test_state_write_and_rejected_lease_are_not_retried(self):
        for data, error in (({'phase': 'waiting'}, ConnectionResetError()), (None, AgentApiError('Lease rejected'))):
            client = SimpleNamespace(post=Mock(side_effect=error))
            with self.assertRaises(type(error)):
                AgentTaskApi(client, SimpleNamespace(node_key='test-node')).web_state(1, 'lease', data)
            self.assertEqual(1, client.post.call_count)

    async def test_manual_input_stays_local_and_can_continue(self):
        locator = SimpleNamespace(wait_for=AsyncMock(),count=AsyncMock(return_value=1),input_value=AsyncMock(return_value='private-password'))
        page = SimpleNamespace(get_by_label=Mock(return_value=locator),is_closed=Mock(return_value=False))
        api = SimpleNamespace(web_state=Mock(side_effect=[{}, {'waiting_input':{'confirmed':True}}]))
        window = SimpleNamespace(set_phase=AsyncMock())
        await wait_manual_input(page,{'action':'manual','locator_type':'label','locator':'Password'},(None,api,4,'lease'),window,1)
        self.assertNotIn('private-password',str(api.web_state.call_args_list))

    async def test_manual_input_cancel_and_ambiguity_do_not_click(self):
        locator = SimpleNamespace(wait_for=AsyncMock(),count=AsyncMock(return_value=1),input_value=AsyncMock())
        page = SimpleNamespace(get_by_label=Mock(return_value=locator),is_closed=Mock(return_value=False))
        api = SimpleNamespace(web_state=Mock(side_effect=[{}, {'cancel_requested':True}]))
        with self.assertRaises(TaskCancelled):
            await wait_manual_input(page,{'action':'manual','locator_type':'label','locator':'Password'},(None,api,4,'lease'),SimpleNamespace(set_phase=AsyncMock()),1)
        locator.input_value.assert_not_called()
        locator.count.return_value = 2
        with self.assertRaises(ValueError):
            await wait_manual_input(page,{'action':'manual','locator_type':'label','locator':'Password'},(None,api,4,'lease'),SimpleNamespace(set_phase=AsyncMock()),1)

    async def test_optional_captcha_absent_does_not_wait_for_user_or_read_value(self):
        locator = SimpleNamespace(count=AsyncMock(return_value=0), wait_for=AsyncMock(), input_value=AsyncMock())
        page = SimpleNamespace(get_by_placeholder=Mock(return_value=locator), wait_for_load_state=AsyncMock())
        await wait_manual_input(page, {'action':'manual','locator_type':'placeholder','locator':'Captcha','optional':True}, None, None, 1)
        page.wait_for_load_state.assert_awaited_once_with('networkidle', timeout=10000)
        locator.wait_for.assert_not_called()
        locator.input_value.assert_not_called()

    async def test_optional_captcha_present_still_requires_interactive_context(self):
        locator = SimpleNamespace(count=AsyncMock(return_value=1), wait_for=AsyncMock(), input_value=AsyncMock())
        page = SimpleNamespace(get_by_placeholder=Mock(return_value=locator), wait_for_load_state=AsyncMock())
        with self.assertRaisesRegex(RuntimeError, '有头 Agent'):
            await wait_manual_input(page, {'action':'manual','locator_type':'placeholder','locator':'Captcha','optional':True}, None, None, 1)
        locator.input_value.assert_not_called()

    async def test_optional_captcha_present_waits_for_confirmation_without_transmitting_code(self):
        locator = SimpleNamespace(count=AsyncMock(return_value=1), wait_for=AsyncMock(), input_value=AsyncMock(return_value='private-captcha'))
        page = SimpleNamespace(get_by_placeholder=Mock(return_value=locator), wait_for_load_state=AsyncMock(), is_closed=Mock(return_value=False))
        api = SimpleNamespace(web_state=Mock(side_effect=[{}, {'waiting_input':{'confirmed':True}}]))
        window = SimpleNamespace(set_phase=AsyncMock())
        await wait_manual_input(page, {'action':'manual','locator_type':'placeholder','locator':'Captcha','optional':True}, (None,api,4,'lease'), window, 3, 9)
        self.assertNotIn('private-captcha', str(api.web_state.call_args_list))
        self.assertEqual('waiting_input', api.web_state.call_args_list[0].args[-1]['phase'])
        self.assertEqual(3, api.web_state.call_args_list[0].args[-1]['step'])
        locator.input_value.assert_awaited_once()

    async def test_optional_captcha_configuration_timeout_is_not_silently_skipped(self):
        locator = SimpleNamespace(count=AsyncMock(return_value=0))
        page = SimpleNamespace(get_by_placeholder=Mock(return_value=locator), wait_for_load_state=AsyncMock(side_effect=TimeoutError('configuration timeout')))
        with self.assertRaises(TimeoutError):
            await wait_manual_input(page, {'action':'manual','locator_type':'placeholder','locator':'Captcha','optional':True}, None, None, 1)
        locator.count.assert_not_called()

    def test_no_assertion_is_not_a_business_pass(self):
        self.assertEqual('not_configured',outcome_metadata([{'action':'fill'}],1,'success')['business_result'])
        self.assertEqual('passed',outcome_metadata([{'action':'assert', 'expected':'Saved'}],1,'success')['business_result'])
        self.assertEqual('failed',outcome_metadata([{'action':'assert', 'expected':'Saved'}],0,'failed')['business_result'])
        self.assertEqual('not_run',outcome_metadata([{'action':'click'},{'action':'assert', 'expected':'Saved'}],0,'failed')['business_result'])

    def test_recording_splits_inputs_and_manual_fields_have_no_values(self):
        events = [{'sequence':1,'key':'name','value':'First','step':{'action':'fill','locator_type':'label','locator':'Name'}},
                  {'sequence':2,'key':'password','sensitive':True,'step':{'action':'manual','locator_type':'label','locator':'Password'}}]
        candidate, errors = recording_candidate(events,'Recorded')
        self.assertFalse(errors)
        self.assertEqual({'name':'First'},candidate['input_info'])
        self.assertEqual('{{name}}',candidate['steps'][0]['value'])
        self.assertNotIn('value',candidate['steps'][1])


if __name__ == '__main__':
    unittest.main()
