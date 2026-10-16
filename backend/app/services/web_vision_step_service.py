"""Queue short screenshot requests and expose durable model-analysis progress."""
from secrets import token_urlsafe

from app.core.exceptions import BusinessRuleError
from app.services.web_vision_agent_service import WebVisionAgentService
from app.utils.cancellable_model_request import ModelRequestCancelled


class WebVisionStepService:
    def __init__(self, repository):
        self.repository = repository
        self.vision = WebVisionAgentService(repository)

    def begin(self, task_id, request):
        task = self.vision._owned(task_id, request)
        self.vision.validate_step(task, request)
        if request.phase == "waiting_login":
            return self.vision.step(task_id, request), None
        data = task["data"]
        previous = data.get("vision_job") or {}
        if previous and previous["status"] == "running":
            if previous["phase"] != request.phase:
                raise BusinessRuleError("已有 AI 分析正在进行")
            return {"pending": True, "job_id": previous["id"]}, None
        if previous and previous["phase"] == request.phase and previous["status"] == "success":
            return previous["result"], None
        job = {"id": token_urlsafe(12), "phase": request.phase, "status": "running"}
        changed = self.repository.patch_running_agent_task(task_id, request.node_key, {"vision_job": job, "vision_phase": request.phase, "progress": "正在调用视觉模型分析截图"}, expected={"vision_job": previous})
        if not changed:
            raise BusinessRuleError("分析状态已变化，请刷新后重试")
        return {"pending": True, "job_id": job["id"]}, job["id"]

    def run(self, task_id, request, job_id, cancelled):
        task = self.vision._owned(task_id, request)
        job = (task["data"].get("vision_job") or {})
        if job.get("id") != job_id or job.get("status") != "running":
            return
        self.vision.discovery.cancel_check = cancelled
        try:
            result = self.vision.step(task_id, request)
            if cancelled():
                raise ModelRequestCancelled("用户已中止 AI 分析")
            completed = {**job, "status": "success", "result": result}
        except Exception as exc:  # noqa: BLE001 - analysis failure is delivered by polling, not a lost HTTP response.
            completed = {**job, "status": "canceled" if cancelled() else "failed", "error": str(exc).replace(getattr(self.vision.discovery.last_client, "api_key", "") or "\0", "[redacted]")}
        self.repository.patch_running_agent_task(task_id, request.node_key, {"vision_job": completed}, expected={"vision_job": job})
