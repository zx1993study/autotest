"""User cancellation for local and server-side Web discovery tasks."""
from datetime import UTC, datetime

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.utils.cancellable_model_request import ModelRequestCancelled


class WebVisionControlService:
    def __init__(self, repository):
        self.repository = repository

    def cancelled(self, task_id):
        task = self.repository.get("ai_generation_tasks", task_id)
        return not task or task.get("status") == "canceled" or bool((task.get("data") or {}).get("cancel_requested"))

    def check(self, task_id):
        if self.cancelled(task_id):
            raise ModelRequestCancelled("用户已中止 AI 分析")

    def cancel(self, task_id):
        task = self.repository.get("ai_generation_tasks", task_id)
        if not task:
            raise ResourceNotFoundError("未找到 AI 分析任务")
        data = dict(task.get("data") or {})
        if data.get("task_type") != "web_vision_discovery":
            raise BusinessRuleError("该任务不是 Web AI 分析任务")
        if task["status"] == "canceled":
            return {"accepted": True}
        if task["status"] not in {"queued", "pending", "running"}:
            raise BusinessRuleError("任务已结束，无法中止")
        data.update(cancel_requested=True, progress="已中止", status="canceled", finished_at=int(datetime.now(UTC).timestamp()))
        if not self.repository.update_if_status("ai_generation_tasks", task_id, task["status"], {"status": "canceled", "data": data}):
            raise BusinessRuleError("任务状态已变化，请刷新后重试")
        agent_id = data.get("agent_task_id")
        agent = self.repository.get("agent_tasks", agent_id) if agent_id else None
        if agent and agent["status"] == "pending":
            self.repository.update_if_status("agent_tasks", agent_id, "pending", {"status": "canceled", "data": {**agent["data"], "cancel_requested": True, "progress": "已中止"}})
        elif agent and agent["status"] == "running":
            self.repository.patch_running_agent_task(agent_id, agent["data"]["claimed_by"], {"cancel_requested": True, "progress": "正在中止"})
        return {"accepted": True}
