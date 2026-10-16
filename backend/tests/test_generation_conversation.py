import base64
import json
import unittest
from unittest.mock import Mock

from app.core.exceptions import BusinessRuleError
from app.schemas.business_generation import GenerationRequest, ReferenceScreenshot
from app.services.business_generation_service import BusinessGenerationService
from app.services.generation_task_query_service import GenerationTaskQueryService
from app.utils.vision_images import red_test_image
from test_agent_services import FakeResourceRepository


class GenerationConversationTest(unittest.TestCase):
    def setUp(self):
        self.repo = FakeResourceRepository()
        self.source = self.repo.create('app_features', {'name':'Synthetic chat', 'project_id':1})
        self.model = self.repo.create('ai_models', {'status':'active','data':{'supports_vision':True}})
        self.service = BusinessGenerationService(self.repo)
        self.client = Mock(api_key='synthetic-key', requests_made=1)
        self.client.complete_json.return_value = {'questions':['请提供设备平台和页面截图'], 'warnings':[]}
        self.service._client = Mock(return_value=self.client)

    def submit(self, prompt='发送你好', parent=None, **kwargs):
        task = self.service.submit('APP', GenerationRequest(source_id=self.source['id'], model_id=self.model['id'], prompt=prompt, parent_task_id=parent, **kwargs))
        self.service.run(task['id'])
        return self.service.get(task['id'])

    def test_followup_passes_prior_questions_and_new_message_without_operating(self):
        first = self.submit()
        second = self.submit('iOS，接下来点击发送', first['id'])
        context = json.loads(self.client.complete_json.call_args.args[1])['context']
        self.assertEqual(['user','assistant','user'], [m['role'] for m in context['conversation']])
        self.assertIn('设备平台', context['conversation'][1]['content'])
        self.assertEqual(first['id'], second['data']['parent_task_id'])
        self.assertEqual(4, len(second['data']['conversation']))
        self.assertEqual(['context','model','validation','review'], [s['code'] for s in second['data']['stages']])
        self.assertTrue(all(s['status']=='success' for s in second['data']['stages']))
        self.assertFalse(self.repo.tables.get('agent_tasks'))

    def test_foreign_source_and_active_parent_cannot_be_continued(self):
        first = self.submit()
        other = self.repo.create('app_features', {'name':'Other','project_id':2})
        with self.assertRaises(BusinessRuleError):
            self.service.submit('APP', GenerationRequest(source_id=other['id'], prompt='Next', parent_task_id=first['id']))
        first['status'] = 'running'
        with self.assertRaises(BusinessRuleError):
            self.submit(parent=first['id'])

    def test_app_screenshots_continue_in_next_turn_and_public_payload_is_hidden(self):
        screenshot = ReferenceScreenshot(description='Synthetic screenshot', image_base64=base64.b64encode(red_test_image()).decode())
        first = self.submit(screenshots=[screenshot])
        second = self.submit('下一步发送消息', first['id'])
        self.assertEqual(1,len(self.client.complete_json.call_args.args[2]))
        public = GenerationTaskQueryService(self.repo).public_task(second)
        self.assertNotIn('payload',public['data'])
        self.assertNotIn('previous_candidate',public['data'])
        self.assertNotIn(screenshot.image_base64,json.dumps(public))

    def test_failed_generation_keeps_conversation_and_failed_public_stage(self):
        from app.utils.vision_llm_client import VisionModelError
        self.client.complete_json.side_effect = VisionModelError('HTTP 503 synthetic-key')
        task = self.submit()
        self.assertEqual('failed',task['status'])
        self.assertEqual('failed',task['data']['stages'][-1]['status'])
        self.assertNotIn('synthetic-key',json.dumps(task['data']['conversation']))


if __name__ == '__main__':
    unittest.main()
