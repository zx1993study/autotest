from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuthSnapshotCache:
    """Persist task-scoped auth snapshots for the current execution only."""

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir

    def load_valid(self, task_id: int, snapshot_id: str) -> dict[str, Any] | None:
        """Return a cached snapshot when it exists and has not expired."""

        path = self._path(task_id, snapshot_id)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        if self._expired(payload.get("expires_at")):
            self.delete(task_id, snapshot_id)
            return None
        return payload

    def save(self, task_id: int, snapshot_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Write the snapshot to disk so executors do not hold globals."""

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(task_id, snapshot_id)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    def delete(self, task_id: int, snapshot_id: str) -> None:
        """Remove a local snapshot after the task finishes."""

        try:
            self._path(task_id, snapshot_id).unlink()
        except FileNotFoundError:
            return

    def _path(self, task_id: int, snapshot_id: str) -> Path:
        safe_snapshot_id = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in snapshot_id)
        return self.cache_dir / f"task_{task_id}_{safe_snapshot_id}.json"

    def _expired(self, value: Any) -> bool:
        if not value:
            return False
        try:
            expires_at = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return True
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at < datetime.now(timezone.utc)
