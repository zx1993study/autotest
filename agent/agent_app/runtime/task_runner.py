from __future__ import annotations

from typing import Any

from agent_app.api.tasks import AgentTaskApi
from agent_app.auth.cache import AuthSnapshotCache
from agent_app.config import AgentConfig


class AgentTaskRunner:
    """Dispatch claimed tasks to local executors."""

    def __init__(self, config: AgentConfig, task_api: AgentTaskApi) -> None:
        self.config = config
        self.task_api = task_api
        self.auth_cache = AuthSnapshotCache(config.artifacts_dir / "auth")
        self.web_executor = None
        self.mobile_executor = None

    def run(self, task: dict[str, Any]) -> dict[str, Any]:
        """Run one claimed task on the local node."""

        data = task.get("data") if isinstance(task.get("data"), dict) else {}
        task_payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
        task_type = str(data.get("task_type") or task_payload.get("task_type") or "")
        task_id = int(task["id"])
        if task_type == 'app_exploration':
            if 'mobile' not in self.config.plugins:
                raise ValueError('Mobile plugin is not enabled')
            from agent_app.executors.app_exploration_executor import LocalAppExplorationExecutor
            if self.mobile_executor is None:
                from agent_app.executors.mobile_case_executor import LocalMobileCaseExecutor
                self.mobile_executor = LocalMobileCaseExecutor(self.config.artifacts_dir)
            return LocalAppExplorationExecutor(self.config,self.task_api,self.mobile_executor.pool).execute(
                task_id,data.get('lease_token'),task_payload)
        if task_type == "web_replay":
            if "web" not in self.config.plugins:
                raise ValueError("Web plugin is not enabled")
            if task_payload.get('recording'):
                from agent_app.executors.web_recording_executor import LocalWebRecordingExecutor

                return LocalWebRecordingExecutor(self.config, self.task_api).execute(task_id, data.get('lease_token'), task_payload)
            from agent_app.executors.web_replay_executor import LocalWebReplayExecutor
            if task_payload.get('cases'):
                protected = self.task_api.case_inputs(task_id, data.get('lease_token'))
                case = task_payload['cases'][0]
                task_payload['runtime_inputs'] = protected.get(str(case['id']), {})
            return LocalWebReplayExecutor(self.config, self.task_api).execute(task_id, data.get("lease_token"), task_payload)
        if task_type == "web_vision_discovery":
            if "web" not in self.config.plugins:
                raise ValueError("Web plugin is not enabled")
            from agent_app.executors.web_vision_executor import LocalWebVisionExecutor

            snapshot_ids = []
            try:
                try:
                    snapshot_ids = self._attach_auth_contexts(task_id, task_payload)
                except Exception:
                    if not (task_payload.get("discovery") or {}).get("wait_for_login"):
                        raise
                    task_payload["context"] = {}
                return LocalWebVisionExecutor(self.config, self.task_api).execute(task_id, data.get("lease_token"), task_payload)
            finally:
                for snapshot_id in snapshot_ids:
                    self.auth_cache.delete(task_id, snapshot_id)
        if task_type == "device_discovery":
            from agent_app.executors.device_discovery import LocalDeviceDiscovery

            return LocalDeviceDiscovery(self.config.node_key).execute(task_payload)
        if task_type != "case_execution":
            raise ValueError(f"暂不支持的 Agent 任务类型：{task_type}")
        case_type = str(task_payload.get("case_type") or "").upper()
        if case_type == "APP":
            if "mobile" not in self.config.plugins:
                raise ValueError("Mobile plugin is not enabled")
            if self.mobile_executor is None:
                from agent_app.executors.mobile_case_executor import (
                    LocalMobileCaseExecutor,
                )

                self.mobile_executor = LocalMobileCaseExecutor(self.config.artifacts_dir)
            return self.mobile_executor.execute(task_payload)
        if case_type != "WEB" or "web" not in self.config.plugins:
            raise ValueError(f"Execution plugin is not available: {case_type}")
        if self.web_executor is None:
            from agent_app.executors.web_case_executor import LocalWebCaseExecutor

            self.web_executor = LocalWebCaseExecutor(self.config.artifacts_dir)
        self.web_executor.window_context = (self.config, self.task_api, task_id, data.get("lease_token"))
        cases = task_payload.get('cases') or []
        if any(c.get('data', {}).get('secret_inputs') for c in cases):
            inputs = self.task_api.case_inputs(task_id, data.get('lease_token'))
            for case in cases:
                case.setdefault('data', {})['runtime_inputs'] = inputs.get(str(case['id']), {})
        return self._run_with_auth(task_id, task_payload, self.web_executor.execute)

    def _run_with_auth(
        self,
        task_id: int,
        task_payload: dict[str, Any],
        executor: Any,
    ) -> dict[str, Any]:
        snapshot_ids = self._attach_auth_contexts(task_id, task_payload)
        self._attach_ai_model_context(task_id, task_payload)
        try:
            return executor(task_payload)
        finally:
            for snapshot_id in snapshot_ids:
                self.auth_cache.delete(task_id, snapshot_id)

    def _attach_auth_contexts(self, task_id: int, task_payload: dict[str, Any]) -> list[str]:
        context = task_payload.get("context") if isinstance(task_payload.get("context"), dict) else {}
        auth_snapshots = context.get("auth_snapshots") if isinstance(context.get("auth_snapshots"), dict) else {}
        attached_by_case: dict[str, dict[str, Any]] = {}
        consumed_snapshot_ids: list[str] = []
        for case_key, snapshot in auth_snapshots.items():
            if not isinstance(snapshot, dict):
                continue
            snapshot_id = str(snapshot.get("snapshot_id") or "")
            if not snapshot_id:
                continue
            auth_context = self._load_auth_context(task_id, snapshot_id)
            attached_by_case[str(case_key)] = auth_context
            consumed_snapshot_ids.append(snapshot_id)

        default_snapshot = context.get("auth_snapshot") if isinstance(context.get("auth_snapshot"), dict) else {}
        default_snapshot_id = str(default_snapshot.get("snapshot_id") or "")
        if default_snapshot_id and default_snapshot_id not in consumed_snapshot_ids:
            context["auth_context"] = self._load_auth_context(task_id, default_snapshot_id)
            consumed_snapshot_ids.append(default_snapshot_id)

        if attached_by_case:
            context["auth_context_by_case"] = attached_by_case
            context["auth_context"] = next(iter(attached_by_case.values()))
        if context:
            task_payload["context"] = context
        return consumed_snapshot_ids

    def _attach_ai_model_context(self, task_id: int, task_payload: dict[str, Any]) -> None:
        context = task_payload.get("context") if isinstance(task_payload.get("context"), dict) else {}
        snapshot = context.get("ai_model") if isinstance(context.get("ai_model"), dict) else {}
        if snapshot.get("api_key"):
            return
        snapshot_id = str(snapshot.get("snapshot_id") or "")
        if not snapshot_id:
            return
        model = self.task_api.ai_model_context(task_id, snapshot_id)
        if model.get("transport") != "platform_proxy":
            raise ValueError("Platform must support task-scoped AI proxy; direct provider keys are not accepted")
        context["ai_model"] = {**model, "api_key": self.config.token, "base_url": f"{self.task_api.client.base_url}/agent/runtime/tasks/{task_id}/model/v1"}
        task_payload["context"] = context

    def _load_auth_context(self, task_id: int, snapshot_id: str) -> dict[str, Any]:
        auth_context = self.auth_cache.load_valid(task_id, snapshot_id)
        if auth_context is None:
            auth_context = self.task_api.auth_context(task_id, snapshot_id)
            self.auth_cache.save(task_id, snapshot_id, auth_context)
        return auth_context
