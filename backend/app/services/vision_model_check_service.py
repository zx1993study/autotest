import time

from app.services.web_vision_discovery_service import WebVisionDiscoveryService
from app.utils.vision_images import red_test_image
from app.utils.vision_llm_client import VisionLlmClient


class VisionModelCheckService:
    def __init__(self, repository):
        self.discovery = WebVisionDiscoveryService(repository)

    def check(self, model_id=None):
        model = self.discovery.model_service.active_model(model_id)
        configured = self.discovery._vision_client(int(model["id"]))
        client = VisionLlmClient(base_url=configured.api_url, api_key=configured.api_key, model=configured.model,
                                api_protocol=configured.api_protocol, reasoning_effort=configured.reasoning_effort,
                                timeout_sec=30, cache_enabled=False, rate_limit_retries=0)
        started = time.monotonic()
        result = {"model_id": model["id"], "model_name": configured.model, "healthy": False}
        try:
            answer = client.complete_json("Return only JSON.", 'Identify the dominant color of this image. Return {"color":"red"} or its actual color.', [red_test_image()])
            result["healthy"] = str(answer.get("color") or "").lower() == "red"
            result["message"] = "图片输入和 JSON 输出正常" if result["healthy"] else "模型未正确识别测试图片"
        except Exception as exc:  # noqa: BLE001 - health probes return diagnostics, not server errors.
            result["message"] = str(exc).replace(configured.api_key, "[redacted]")[:500]
        return {**result, "model_http_calls": client.requests_made, "elapsed_sec": round(time.monotonic() - started, 2)}
