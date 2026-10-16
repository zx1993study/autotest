import unittest
from copy import deepcopy

from app.schemas.list_summaries import GenerationTaskSummary
from app.services.generation_task_query_service import GenerationTaskQueryService


class GenerationTaskListSummaryTest(unittest.TestCase):
    def test_list_keeps_summary_and_does_not_load_verification_details(self):
        class Repository:
            def list(self, table, **kwargs):
                return [task], 1

            def get(self, *args):
                raise AssertionError("List must not read individual Agent task details")

        task = {"id": 1, "name": "Generation", "status": "success", "project_id": 1, "data": {
            "domain": "WEB", "source_id": 2, "task_type": "business_generation", "progress": "Done",
            "model_http_calls": 3, "agent_task_id": 5, "conversation": [{"content": "x" * 100000}],
            "payload": {"token": "secret"}, "result": {"candidate": {"steps": []}},
        }}
        original = deepcopy(task)
        rows, total = GenerationTaskQueryService(Repository()).list(1, 1, 20)
        self.assertEqual(total, 1)
        self.assertEqual(rows[0]["data"], GenerationTaskSummary.model_validate(task["data"]).model_dump(exclude_none=True))
        self.assertEqual(rows[0]["data"]["source_id"], 2)
        self.assertNotIn("result", rows[0]["data"])
        self.assertNotIn("payload", rows[0]["data"])
        self.assertEqual(task, original)


if __name__ == "__main__":
    unittest.main()
