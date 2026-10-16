import json
import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException
from test_agent_services import FakeResourceRepository
from test_model_api_protocol import ModelHttpResponse, completed_response

from app.core.exceptions import BusinessRuleError
from app.schemas.agent import AgentModelCompletionRequest
from app.services.agent_model_proxy_service import AgentModelProxyService
from app.services.ai_generation_service import AiGenerationService
from app.services.ai_model_service import AiModelResourceService
from app.services.web_vision_discovery_service import WebVisionDiscoveryService
from app.utils.vision_llm_client import VisionLlmClient


class ModelProtocolServicesTest(unittest.TestCase):
    def setUp(self):
        self.repo = FakeResourceRepository()
        self.model = self.repo.create("ai_models", {"name": "test", "status": "active", "data": {
            "model": "test-model", "base_url": "https://example.test", "api_protocol": "responses",
            "reasoning_effort": "low", "supports_vision": True, "is_current": True,
        }})
        self.captured = []
        self.key = "synthetic-provider-key"
        self.secret = patch("app.services.ai_secret_service.AiSecretService.load_api_key", return_value=self.key)
        self.secret.start()
        self.addCleanup(self.secret.stop)

    def open_response(self, request, timeout=0):
        self.captured.append((request.full_url, json.loads(request.data), timeout))
        return ModelHttpResponse(events=[{"type": "response.completed", "response": completed_response()}])

    def test_text_generator_uses_responses_and_parses_json(self):
        with patch("app.services.ai_generation_service.request.urlopen", self.open_response):
            result = AiGenerationService(self.repo)._call_model(self.model["id"], {"system": "JSON only", "user": "test"})
        self.assertEqual(result, {"status": "ok"})
        self.assertEqual(self.captured[0][0], "https://example.test/responses")
        self.assertNotIn("temperature", self.captured[0][1])

    def test_vision_factory_and_actual_client_share_model_protocol(self):
        client = WebVisionDiscoveryService(self.repo)._vision_client(self.model["id"])
        self.assertEqual(client.api_protocol, "responses")
        self.assertEqual(client.reasoning_effort, "low")
        client.cache_dir = None
        with patch("app.utils.vision_llm_client.request.urlopen", self.open_response):
            client.complete_json("JSON only", "test", [b"image"])
        self.assertEqual(self.captured[0][1]["input"][0]["content"][1]["type"], "input_image")
        self.assertEqual(client.requests_made, 1)

    def test_agent_proxy_preserves_chat_contract_and_hides_provider_key(self):
        task = self.repo.create("agent_tasks", {"status": "running", "data": {
            "payload": {"context": {"ai_model": {"model_id": self.model["id"]}}},
        }})
        payload = AgentModelCompletionRequest(messages=[{"role": "user", "content": "test"}], model="untrusted-model")
        with patch("app.services.agent_model_proxy_service.urlopen", self.open_response):
            result = AgentModelProxyService(self.repo).completion(task["id"], payload)
        self.assertEqual(result["choices"][0]["message"]["content"], '{"status":"ok"}')
        self.assertEqual(self.captured[0][1]["model"], "test-model")
        self.assertNotIn(self.key, json.dumps(result))

    def test_failed_stream_is_redacted_and_not_a_success(self):
        failure = lambda *args, **kwargs: ModelHttpResponse(events=[{"type": "error", "message": self.key}])
        with patch("app.services.ai_generation_service.request.urlopen", failure), self.assertRaises(HTTPException) as raised:
            AiGenerationService(self.repo)._call_model(self.model["id"], {"system": "JSON", "user": "test"})
        self.assertNotIn(self.key, str(raised.exception))
        self.assertEqual(raised.exception.status_code, 502)

    def test_legacy_client_keeps_chat_and_invalid_protocol_does_not_save_secret(self):
        client = VisionLlmClient(base_url="https://example.test", api_key=self.key, model="test")
        self.assertEqual(client.api_url, "https://example.test/v1/chat/completions")
        service = AiModelResourceService(self.repo)
        service.secret_service.save_api_key = Mock()
        with self.assertRaises(BusinessRuleError):
            service.update(self.model["id"], {"data": {"api_protocol": "invalid", "api_key": self.key}})
        service.secret_service.save_api_key.assert_not_called()


if __name__ == "__main__":
    unittest.main()
