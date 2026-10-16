from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent_app.auth.cache import AuthSnapshotCache


class AuthSnapshotCacheTest(unittest.TestCase):
    def test_load_valid_snapshot_and_drop_expired_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = AuthSnapshotCache(Path(temp_dir))
            expires_at = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat(timespec="seconds")
            cache.save(1, "snapshot_1", {"snapshot_id": "snapshot_1", "expires_at": expires_at, "cookies": []})

            cached = cache.load_valid(1, "snapshot_1")

            self.assertIsNotNone(cached)
            self.assertEqual(cached["snapshot_id"], "snapshot_1")

            expired_at = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat(timespec="seconds")
            cache.save(1, "snapshot_2", {"snapshot_id": "snapshot_2", "expires_at": expired_at})

            self.assertIsNone(cache.load_valid(1, "snapshot_2"))


if __name__ == "__main__":
    unittest.main()
