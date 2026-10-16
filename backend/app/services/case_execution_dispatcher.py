from __future__ import annotations

from typing import Any

from app.enums.business import ExecutionModeEnum
from app.repositories.interfaces import ResourceRepository
from app.scheduler.jobs.case_execution_jobs import run_case_execution_job
from app.services.agent_task_service import AgentTaskService


class CaseExecutionDispatcher:
    """Route test execution to backend executors or installed local agents."""

    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository
        self.agent_tasks = AgentTaskService(repository)

    def execute(self, case_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute immediately or queue an agent task based on mode."""

        if self._should_dispatch_to_agent(case_type, payload):
            task = self.agent_tasks.create_case_execution_task(case_type, payload)
            return {
                "total": 1,
                "success_count": 0,
                "failed_count": 0,
                "queued_count": 1,
                "records": [],
                "agent_task": task,
            }
        return run_case_execution_job(case_type, payload, self.repository)

    def _should_dispatch_to_agent(self, case_type: str, payload: dict[str, Any]) -> bool:
        if case_type.upper() == "APP":
            return True
        mode = str(payload.get("mode") or "").lower()
        node_id = str(payload.get("node_id") or "").strip()
        if mode == ExecutionModeEnum.REMOTE_NODE.code:
            return True
        if case_type.upper() == "WEB" and mode == ExecutionModeEnum.LOCAL_HEADED.code and node_id:
            return True
        return False
