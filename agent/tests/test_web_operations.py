import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from agent_app.executors.web_manual_input import outcome_metadata, wait_manual_input
from agent_app.runtime.task_cancelled import TaskCancelled
from web_automation.discovery.recording import recording_candidate


class WebOperationsTest(unittest.IsolatedAsyncioTestCase):
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

    def test_no_assertion_is_not_a_business_pass(self):
        self.assertEqual('not_configured',outcome_metadata([{'action':'fill'}],1,'success')['business_result'])
        self.assertEqual('passed',outcome_metadata([{'action':'assert'}],1,'success')['business_result'])
        self.assertEqual('failed',outcome_metadata([{'action':'assert'}],0,'failed')['business_result'])
        self.assertEqual('not_run',outcome_metadata([{'action':'click'},{'action':'assert'}],0,'failed')['business_result'])

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
