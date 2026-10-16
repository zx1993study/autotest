import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.models.resource_record import ResourceRecord
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class EmptyDefaultModuleMaintenanceTest(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[2] / "scripts/remove_empty_default_api_modules.py"
        spec = importlib.util.spec_from_file_location("remove_empty_modules", path)
        self.script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.script)
        self.engine = create_engine("sqlite:///:memory:")
        ResourceRecord.__table__.create(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        self.addCleanup(self.engine.dispose)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.backup = Path(self.temp.name) / "backup.json"
        self.patcher = patch.object(self.script, "SessionLocal", self.sessions)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        with self.sessions() as session:
            session.add(ResourceRecord(id=1, table_name="api_modules", name="\u672a\u5206\u7ec4", project_id=10, data_json={"data": {"module_key": "__ungrouped__"}}))
            session.commit()

    def remove(self, apply=False):
        return self.script.remove([1], ":memory:", self.backup, apply)

    def test_dry_run_preserves_records_and_does_not_write_backup(self):
        self.assertTrue(self.remove()["dry_run"])
        self.assertFalse(self.backup.exists())
        with self.sessions() as session:
            self.assertIsNotNone(session.get(ResourceRecord, 1))

    def test_apply_backs_up_only_modules_and_preserves_interfaces(self):
        with self.sessions() as session:
            session.add(ResourceRecord(id=2, table_name="api_interfaces", name="named", project_id=10, data_json={"data": {"module": "Customers", "module_id": 3}}))
            session.commit()
        self.assertEqual(self.remove(True)["deleted_ids"], [1])
        snapshot = json.loads(self.backup.read_text(encoding="utf-8"))
        self.assertEqual([item["id"] for item in snapshot], [1])
        with self.sessions() as session:
            self.assertIsNone(session.get(ResourceRecord, 1))
            self.assertIsNotNone(session.get(ResourceRecord, 2))

    def test_used_default_module_is_never_deleted(self):
        for data in ({"module_id": 1}, {"module": ""}, {}, {"module": None}):
            with self.subTest(data=data), self.sessions() as session:
                session.add(ResourceRecord(id=2, table_name="api_interfaces", name="used", project_id=10, data_json={"data": data}))
                session.commit()
                with self.assertRaisesRegex(ValueError, "interface references"):
                    self.remove(True)
                self.assertFalse(self.backup.exists())
                self.assertIsNotNone(session.get(ResourceRecord, 1))
                session.delete(session.get(ResourceRecord, 2))
                session.commit()

    def test_database_and_target_guards_prevent_changes(self):
        for ids, database in (([1], "unexpected"), ([1, 99], ":memory:")):
            with self.assertRaises(ValueError):
                self.script.remove(ids, database, self.backup, True)
        self.assertFalse(self.backup.exists())
        with self.sessions() as session:
            self.assertIsNotNone(session.get(ResourceRecord, 1))

    def test_existing_backup_is_not_overwritten(self):
        self.backup.write_text("existing", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.remove(True)
        self.assertEqual(self.backup.read_text(encoding="utf-8"), "existing")
        with self.sessions() as session:
            self.assertIsNotNone(session.get(ResourceRecord, 1))
