from __future__ import annotations

import hashlib
import logging
import threading
import time

from agent_app.api.tasks import AgentTaskApi
from agent_app.runtime.execution_journal import ExecutionJournal
from agent_app.runtime.heartbeat import HeartbeatTicker
from agent_app.runtime.local_state import write_state
from agent_app.runtime.result_outbox import ResultOutbox
from agent_app.runtime.stop_request import requested
from agent_app.runtime.task_cancelled import TaskCancelled
from agent_app.runtime.task_runner import AgentTaskRunner


class AgentTaskPoller:
    """Poll remote tasks and report local execution results."""

    def __init__(
        self,
        task_api: AgentTaskApi,
        heartbeat: HeartbeatTicker,
        runner: AgentTaskRunner,
        poll_interval_sec: int,
    ) -> None:
        self.task_api = task_api
        self.heartbeat = heartbeat
        self.runner = runner
        self.poll_interval_sec = max(1, poll_interval_sec)
        config = runner.config
        namespace = hashlib.sha256(f"{config.server_url}|{config.node_key}".encode()).hexdigest()[:20]
        self.outbox = ResultOutbox(config.artifacts_dir / "outbox" / namespace)
        self.journal = ExecutionJournal(self.outbox)
        self.journal.recover()

    def run_forever(self) -> None:
        while not requested(self.runner.config):
            try:
                self.run_once()
            except Exception as exc:  # noqa: BLE001 - the tray worker must keep reporting recoverable outages.
                logging.getLogger(__name__).warning("Agent poll failed: %s", type(exc).__name__)
            time.sleep(self.poll_interval_sec)

    def run_once(self) -> None:
        write_state(self.runner.config, "online")
        self.heartbeat.send_if_due("online")
        self.outbox.drain(self.task_api)
        if requested(self.runner.config):
            return
        task = self.task_api.claim_next()
        if not task:
            return
        task_id = int(task["id"])
        self.journal.start(task)
        write_state(self.runner.config, "busy", task_id)
        stopped = threading.Event()
        ticker = threading.Thread(target=self._keep_alive, args=(task, stopped), daemon=True)
        ticker.start()
        error = None
        try:
            try:
                self.heartbeat.send_now("busy", current_task_id=task_id)
                result = self.runner.run(task)
                status = "success" if int(result.get("failed_count") or 0) == 0 else "failed"
                if result.get('canceled'):
                    status = 'canceled'
            except TaskCancelled as exc:
                status, result, error = "canceled", {"records": []}, str(exc)
            except Exception as exc:  # noqa: BLE001 - report executor failures without replay.
                status, result, error = "failed", {"records": []}, str(exc)
            self.outbox.save(task_id, {"status": status, "result": result, "error": error, "lease_token": (task.get("data") or {}).get("lease_token")})
            self.journal.complete(task_id)
            write_state(self.runner.config, "uploading", task_id)
            self.outbox.drain(self.task_api)
            self.heartbeat.send_now("online")
        finally:
            stopped.set()
            ticker.join(timeout=35)

    def _keep_alive(self, task, stopped):
        task_id = int(task["id"])
        while not stopped.wait(self.heartbeat.interval_sec):
            try:
                write_state(self.runner.config, "busy", task_id)
                self.heartbeat.send_now("busy", current_task_id=task_id)
                self.task_api.renew(task_id, (task.get("data") or {}).get("lease_token"))
            except Exception as exc:  # noqa: BLE001 - retain the completed result during an outage.
                logging.getLogger(__name__).warning("Agent heartbeat failed: %s", type(exc).__name__)
