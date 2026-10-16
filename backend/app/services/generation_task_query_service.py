from copy import deepcopy

from app.schemas.list_summaries import GenerationTaskSummary
from app.services.ai_generation_service import AiGenerationService
from app.services.business_generation_service import TASKS


class GenerationTaskQueryService:
    def __init__(self, repository):
        self.repository = repository

    def public_task(self, task):
        task = deepcopy(task)
        data = task.get("data") or {}
        data.pop("payload", None)
        data.pop("accepted_candidate", None)
        data.pop('previous_candidate', None)
        original = data.pop("repair_original", None)
        candidate = (data.get("result") or {}).get("candidate")
        if original and candidate:
            data["repair_changes"] = [{"step": i + 1, "before": {k: a.get(k) for k in ("locator_type", "locator", "role")}, "after": {k: b.get(k) for k in ("locator_type", "locator", "role")}}
                                     for i, (a, b) in enumerate(zip(original["steps"], candidate["steps"], strict=False))
                                     if any(a.get(k) != b.get(k) for k in ("locator_type", "locator", "role"))]
        if data.get("agent_task_id"):
            agent = self.repository.get("agent_tasks", data["agent_task_id"]) or {}
            ad = agent.get("data") or {}
            data["verification"] = {"status": agent.get("status"), "phase": ad.get("replay_phase"), "result": ad.get("result"), "error": ad.get("error")}
        task["data"] = data
        return task

    def list(self, project_id, page, page_size):
        rows, total = self.repository.list(TASKS, project_id=project_id, page=page, page_size=page_size)
        return [{**task, "data": GenerationTaskSummary.model_validate(task.get("data") or {}).model_dump(exclude_none=True)} for task in rows], total

    def get(self, task_id):
        return self.public_task(AiGenerationService(self.repository).get_generation_task_detail(task_id))
