from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from agent_app.executors.wda_sessions import WdaSessionPool
from agent_app.runtime.result_outbox import ResultOutbox
from agent_app.runtime.capabilities import available_capabilities
from agent_app.utils.file_lease import FileLease


class MobileRuntimeTest(unittest.TestCase):
    def test_session_is_reused_and_invalidated_without_replaying_actions(self):
        with tempfile.TemporaryDirectory() as temp:
            session = Mock()
            client = Mock()
            client.session.return_value = session
            pool = WdaSessionPool(Path(temp), lambda url: client)
            device = {"data": {"udid": "test-phone", "wda_url": "http://127.0.0.1:8100"}}
            with pool.connect(device, "test.app") as (_, reused):
                self.assertFalse(reused)
            with pool.connect(device, "test.app") as (_, reused):
                self.assertTrue(reused)
            self.assertEqual(client.session.call_count, 1)
            with self.assertRaises(RuntimeError):
                with pool.connect(device, "test.app"):
                    raise RuntimeError("submission outcome unknown")
            self.assertEqual(client.session.call_count, 1)
            with pool.connect(device, "test.app"):
                pass
            self.assertEqual(client.session.call_count, 2)

    def test_completed_results_survive_upload_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            outbox = ResultOutbox(Path(temp))
            outbox.save(1, {"status": "success", "result": {}, "error": None, "lease_token": "test-lease"})
            api = Mock()
            api.report.side_effect = ConnectionError("offline")
            with self.assertRaises(ConnectionError):
                outbox.drain(api)
            self.assertTrue((Path(temp) / "1.json").exists())
            api.report.side_effect = None
            self.assertEqual(outbox.drain(api), 1)
            self.assertFalse((Path(temp) / "1.json").exists())

    def test_file_lock_prevents_duplicate_workers(self):
        with tempfile.TemporaryDirectory() as temp:
            first, second = FileLease(Path(temp) / "worker.lock"), FileLease(Path(temp) / "worker.lock")
            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())
            first.release()
            self.assertTrue(second.acquire())
            second.release()

    def test_capabilities_only_include_installed_plugins(self):
        with patch("agent_app.runtime.capabilities.find_spec", return_value=None):
            self.assertEqual(available_capabilities(("mobile", "web", "ai_web")), ("case_execution",))


if __name__ == "__main__":
    unittest.main()
