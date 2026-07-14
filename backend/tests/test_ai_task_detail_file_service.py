from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.services.ai_task_detail_file_service import AiTaskDetailFileService


class AiTaskDetailFileServiceTest(unittest.TestCase):
    """Verify AI task details are overwritten in one stable file per task."""

    def test_save_result_overwrites_stable_task_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = AiTaskDetailFileService(Path(temp_dir))

            first_file = service.save_result(12, {"status": "running", "saved_pages": 1})
            second_file = service.save_result(12, {"status": "success", "saved_pages": 2})
            files = list(Path(temp_dir).glob("*.json"))

            self.assertEqual(first_file, "task-12.json")
            self.assertEqual(second_file, "task-12.json")
            self.assertEqual(len(files), 1)
            self.assertEqual(service.load_result("task-12.json")["saved_pages"], 2)

    def test_load_result_rejects_non_task_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = AiTaskDetailFileService(Path(temp_dir))

            self.assertEqual(service.load_result("../secret.json"), {})


if __name__ == "__main__":
    unittest.main()
