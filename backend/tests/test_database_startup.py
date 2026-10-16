from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy.exc import OperationalError

from app.db import init_db


class DatabaseStartupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = MagicMock()
        self.engine = MagicMock()
        self.engine.begin.return_value.__enter__.return_value = self.connection
        self.settings = SimpleNamespace(database_url="mysql+pymysql://localhost/test")
        self.columns = {
            (table.name, column.name)
            for table in init_db.Base.metadata.sorted_tables for column in table.columns
        }
        self.index = MagicMock()
        self.index.scalar.return_value = 1

    def test_existing_database_does_not_open_a_bootstrap_connection(self) -> None:
        with patch.object(init_db, "engine", self.engine), patch.object(init_db, "settings", self.settings), patch.object(init_db, "create_engine") as create_engine:
            init_db.ensure_database_exists()
        self.engine.connect.assert_called_once()
        create_engine.assert_not_called()

    def test_unknown_database_still_gets_created(self) -> None:
        self.engine.connect.side_effect = OperationalError("connect", {}, Exception(1049, "Unknown database"))
        bootstrap = MagicMock()
        with patch.object(init_db, "engine", self.engine), patch.object(init_db, "settings", self.settings), patch.object(init_db, "create_engine", return_value=bootstrap):
            init_db.ensure_database_exists()
        statement = bootstrap.connect.return_value.__enter__.return_value.execute.call_args.args[0]
        self.assertIn("CREATE DATABASE IF NOT EXISTS `test`", str(statement))
        bootstrap.dispose.assert_called_once()

    def test_network_or_authentication_errors_are_not_treated_as_a_missing_database(self) -> None:
        error = OperationalError("connect", {}, Exception(1045, "Access denied"))
        self.engine.connect.side_effect = error
        with patch.object(init_db, "engine", self.engine), patch.object(init_db, "settings", self.settings), patch.object(init_db, "create_engine") as create_engine:
            with self.assertRaises(OperationalError):
                init_db.ensure_database_exists()
        create_engine.assert_not_called()

    def test_complete_schema_uses_two_queries_without_ddl(self) -> None:
        self.connection.execute.side_effect = [list(self.columns), self.index]
        with patch.object(init_db, "engine", self.engine), patch.object(init_db, "settings", self.settings), patch.object(init_db.Base.metadata, "create_all") as create_all:
            init_db.ensure_schema_compatibility()
        create_all.assert_not_called()
        self.assertEqual(self.connection.execute.call_count, 2)
        self.engine.begin.assert_called_once()

    def test_missing_table_is_created_and_schema_is_refreshed(self) -> None:
        missing = init_db.Base.metadata.tables["api_test_cases"]
        partial = [row for row in self.columns if row[0] != missing.name]
        self.connection.execute.side_effect = [partial, list(self.columns), self.index]
        with patch.object(init_db, "engine", self.engine), patch.object(init_db, "settings", self.settings), patch.object(init_db.Base.metadata, "create_all") as create_all:
            init_db.ensure_schema_compatibility()
        create_all.assert_called_once_with(bind=self.connection, tables=[missing])
        self.assertEqual(self.connection.execute.call_count, 3)

    def test_legacy_columns_are_still_upgraded(self) -> None:
        partial = self.columns - {("api_test_cases", "strategy_ids_json"), ("execution_plans", "requirement_title")}
        self.connection.execute.side_effect = [list(partial), None, None, self.index]
        with patch.object(init_db, "engine", self.engine), patch.object(init_db, "settings", self.settings):
            init_db.ensure_schema_compatibility()
        statements = [str(call.args[0]) for call in self.connection.execute.call_args_list]
        self.assertEqual(sum("ALTER TABLE" in statement for statement in statements), 2)

    def test_sqlite_initial_install_behavior_is_unchanged(self) -> None:
        with patch.object(init_db, "settings", SimpleNamespace(database_url="sqlite:///:memory:")), patch.object(init_db.Base.metadata, "create_all") as create_all:
            init_db.ensure_schema_compatibility()
        create_all.assert_called_once_with(bind=init_db.engine)

    def test_connection_only_startup_never_creates_or_seeds_database(self) -> None:
        self.settings.auto_create_schema = False
        with patch.object(init_db, "engine", self.engine), patch.object(init_db, "settings", self.settings), patch.object(init_db, "_initialized", False), patch.object(init_db, "ensure_database_exists") as create_database, patch.object(init_db, "ensure_schema_compatibility") as schema, patch.object(init_db, "seed_default_data") as seed:
            self.assertTrue(init_db.ensure_initialized())
        self.engine.connect.return_value.__enter__.return_value.execute.assert_called_once()
        statement = self.engine.connect.return_value.__enter__.return_value.execute.call_args.args[0]
        self.assertEqual(str(statement), "SELECT 1")
        create_database.assert_not_called()
        schema.assert_not_called()
        seed.assert_not_called()

    def test_connection_only_failure_does_not_fall_back_to_initialization(self) -> None:
        self.settings.auto_create_schema = False
        self.engine.connect.side_effect = OperationalError("connect", {}, Exception(1049, "Unknown database"))
        with patch.object(init_db, "engine", self.engine), patch.object(init_db, "settings", self.settings), patch.object(init_db, "_initialized", False), patch.object(init_db, "_last_error", None), patch.object(init_db, "ensure_database_exists") as create_database, patch.object(init_db, "seed_default_data") as seed:
            self.assertFalse(init_db.ensure_initialized(raise_on_error=False))
            self.assertFalse(init_db.database_status()["ready"])
        create_database.assert_not_called()
        seed.assert_not_called()
