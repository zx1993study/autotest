import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[2] / "packaging/server/merge_runtime.py"
SPEC = importlib.util.spec_from_file_location("runtime_merge", MODULE)
merge_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(merge_module)


class RuntimeMergeTest(unittest.TestCase):
    def test_newer_credentials_keep_the_old_copy_in_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            roots = [Path(temp) / name for name in ("incoming", "dest", "original", "backup")]
            for root in roots[:3]:
                (root / "auth").mkdir(parents=True)
            incoming, target, old = [root / "auth/config.json" for root in roots[:3]]
            incoming.write_text("new")
            target.write_text("old")
            old.write_text("old")
            os.utime(old, (1, 1))
            report = merge_module.merge(*roots)
            self.assertEqual(report["updated"], 1)
            self.assertEqual(target.read_text(), "new")
            self.assertEqual((roots[3] / "auth/config.json").read_text(), "old")

    def test_immutable_evidence_conflict_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            roots = [Path(temp) / name for name in ("incoming", "dest", "original", "backup")]
            for root in roots[:2]:
                (root / "screenshots").mkdir(parents=True)
            (roots[0] / "screenshots/a.png").write_bytes(b"new")
            (roots[1] / "screenshots/a.png").write_bytes(b"old")
            with self.assertRaises(ValueError):
                merge_module.merge(*roots)
            self.assertEqual((roots[1] / "screenshots/a.png").read_bytes(), b"old")
