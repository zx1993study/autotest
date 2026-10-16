from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from migrate_runtime_storage import migrate


class StorageMigrationTest(unittest.TestCase):
    def test_copy_verifies_hashes_keeps_source_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            source, destination = Path(directory) / "old", Path(directory) / "data"
            (source / "auth").mkdir(parents=True)
            original = source / "auth" / "demo.json"
            original.write_text("{}", encoding="utf-8")
            self.assertEqual(migrate(source, destination)["planned"], 1)
            self.assertFalse(destination.exists())
            self.assertEqual(migrate(source, destination, True)["copied"], 1)
            self.assertTrue(original.exists())
            self.assertEqual(migrate(source, destination, True)["unchanged"], 1)
            (destination / "auth" / "demo.json").write_text("conflict", encoding="utf-8")
            with self.assertRaises(ValueError):
                migrate(source, destination, True)
            self.assertEqual(original.read_text(encoding="utf-8"), "{}")


if __name__ == "__main__":
    unittest.main()
