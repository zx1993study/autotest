from __future__ import annotations

import unittest

from agent_app.executors.result_builder import build_execution_record, summarize_records


class ResultBuilderTest(unittest.TestCase):
    def test_build_execution_record_matches_platform_payload(self) -> None:
        record = build_execution_record(
            case={"id": 12, "name": "登录", "project_id": 3, "assertions": []},
            execution={"mode": "local_headed", "node_id": "local-win-01"},
            status="success",
            description="ok",
            result={"duration_ms": 88, "step_count": 2, "url": "http://example.test"},
            error=None,
        )

        self.assertEqual(record["name"], "WEB 用例执行 - 登录")
        self.assertEqual(record["status"], "success")
        self.assertEqual(record["data"]["case_id"], 12)
        self.assertEqual(record["data"]["node_id"], "local-win-01")

    def test_summarize_records_counts_failed_records(self) -> None:
        summary = summarize_records([
            {"status": "success"},
            {"status": "failed"},
        ])

        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["success_count"], 1)
        self.assertEqual(summary["failed_count"], 1)


if __name__ == "__main__":
    unittest.main()
