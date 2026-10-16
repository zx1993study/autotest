import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from agent_app.runtime.execution_journal import ExecutionJournal
from agent_app.runtime.result_outbox import ResultOutbox
from agent_app.runtime.task_poller import AgentTaskPoller


class TaskPollerTest(unittest.TestCase):
    def test_heartbeat_continues_during_execution_and_offline_result_is_not_rerun(self):
        with tempfile.TemporaryDirectory() as directory, patch("agent_app.runtime.task_poller.write_state"):
            runner = Mock()
            runner.config = SimpleNamespace(server_url="https://platform.test", node_key="test-node", artifacts_dir=Path(directory))
            api, heartbeat = Mock(), Mock()
            heartbeat.interval_sec = .01
            renewed = threading.Event()
            api.renew.side_effect = lambda *_: renewed.set()
            api.claim_next.side_effect = [{"id": 1, "data": {"lease_token": "lease"}}, None]
            api.report.side_effect = ConnectionError("offline")

            def execute(_):
                self.assertTrue(renewed.wait(1))
                return {"failed_count": 0, "records": []}

            runner.run.side_effect = execute
            poller = AgentTaskPoller(api, heartbeat, runner, 1)
            with self.assertRaises(ConnectionError):
                poller.run_once()
            api.report.side_effect = None
            poller.run_once()
            runner.run.assert_called_once()
            self.assertEqual(api.report.call_count, 2)

    def test_crash_journal_recovers_uncertain_failure_without_running_steps(self):
        with tempfile.TemporaryDirectory() as directory:
            outbox = ResultOutbox(Path(directory))
            journal = ExecutionJournal(outbox)
            journal.start({"id": 7, "data": {"lease_token": "lease", "payload": {"case_type": "APP", "cases": [{"id": 1, "name": "Customer"}]}}})
            ExecutionJournal(outbox).recover()
            api = Mock()
            self.assertEqual(outbox.drain(api), 1)
            report = api.report.call_args.kwargs
            self.assertEqual(report["status"], "failed")
            self.assertTrue(report["result"]["records"][0]["data"]["outcome_unknown"])


if __name__ == "__main__":
    unittest.main()
