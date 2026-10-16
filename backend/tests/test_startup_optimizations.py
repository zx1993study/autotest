from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packaging" / "desktop"))
from single_instance import InstanceLease
from app.db import init_db
from app.services.ai_prompt_seed_service import AiPromptSeedService, DEFAULT_AI_PROMPTS


class StartupOptimizationTest(unittest.TestCase):
    def test_default_prompt_refresh_skips_unchanged_database_writes(self):
        rows = [{"id": index + 1, **deepcopy(item)} for index, item in enumerate(DEFAULT_AI_PROMPTS)]
        repository = Mock()
        repository.list.return_value = rows, len(rows)
        service = AiPromptSeedService(repository)
        self.assertEqual(service.seed_defaults(), {"created_count": 0, "updated_count": 0})
        repository.update.assert_not_called()
        rows[1]["description"] = "outdated"
        self.assertEqual(service.seed_defaults()["updated_count"], 1)
        repository.update.assert_called_once()

    def test_manual_prompt_overwrite_is_preserved(self):
        rows = [{"id": index + 1, **deepcopy(item)} for index, item in enumerate(DEFAULT_AI_PROMPTS)]
        repository = Mock()
        repository.list.return_value = rows, len(rows)
        self.assertEqual(AiPromptSeedService(repository).seed_defaults(overwrite=True)["updated_count"], len(rows))

    def test_schema_columns_are_checked_in_one_query_per_group(self):
        tables = ("api_test_cases", "web_test_cases", "app_test_cases", "miniapp_test_cases")
        columns = ("requirement_title", "requirement_document", "generation_json", "api_ids_json", "web_feature_ids_json")
        connection = Mock()
        connection.execute.side_effect = [[(name, "strategy_ids_json") for name in tables], [("execution_plans", name) for name in columns]]
        engine = Mock()
        engine.begin.return_value.__enter__ = Mock(return_value=connection)
        engine.begin.return_value.__exit__ = Mock(return_value=False)
        with patch.object(init_db, "engine", engine), patch.object(init_db, "settings", SimpleNamespace(database_url="mysql+pymysql://localhost/test")):
            init_db.ensure_test_case_strategy_columns()
            init_db.ensure_execution_plan_requirement_columns()
        self.assertEqual(connection.execute.call_count, 2)

    def test_missing_schema_columns_are_still_added_by_explicit_setup(self):
        connection = Mock()
        connection.execute.side_effect = [[], None, None, None, None]
        engine = Mock()
        engine.begin.return_value.__enter__ = Mock(return_value=connection)
        engine.begin.return_value.__exit__ = Mock(return_value=False)
        with patch.object(init_db, "engine", engine), patch.object(init_db, "settings", SimpleNamespace(database_url="mysql+pymysql://localhost/test")):
            init_db.ensure_test_case_strategy_columns()
        self.assertEqual(connection.execute.call_count, 5)
        self.assertTrue(all("ALTER TABLE" in str(call.args[0]) for call in connection.execute.call_args_list[1:]))

    def test_instance_lease_is_exclusive_and_released_after_close(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = InstanceLease(Path(directory)), InstanceLease(Path(directory))
            try:
                self.assertTrue(first.acquire())
                self.assertFalse(second.acquire())
                first.release()
                self.assertTrue(second.acquire())
            finally:
                first.release()
                second.release()


if __name__ == "__main__":
    unittest.main()
