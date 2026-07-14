from __future__ import annotations

import json
from pathlib import Path
from typing import Any


AI_TASK_DETAIL_DIR = Path(__file__).resolve().parents[2] / "storage" / "ai-task-details"


class AiTaskDetailFileService:
    """Persist full AI generation task details in one stable JSON file.

    The task row keeps only a lightweight summary so list queries stay small.
    The full detail uses ``task-{task_id}.json`` and is overwritten on every
    execution; this guarantees a task never accumulates duplicate detail files.
    """

    def __init__(self, storage_dir: Path | None = None) -> None:
        self.storage_dir = storage_dir or AI_TASK_DETAIL_DIR

    def save_result(self, task_id: int, result: dict[str, Any]) -> str:
        """Write the complete task detail and return its stable filename."""

        filename = self.filename_for_task(task_id)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        target = self.storage_dir / filename
        temp_target = target.with_suffix(".json.tmp")
        temp_target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_target.replace(target)
        return filename

    def load_result(self, filename: str) -> dict[str, Any]:
        """Load a previously saved task detail file.

        Invalid or missing files return an empty dict so callers can fall back
        to the summary stored in the task row.
        """

        safe_name = self.safe_filename(filename)
        if not safe_name:
            return {}
        path = self.storage_dir / safe_name
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def filename_for_task(self, task_id: int) -> str:
        """Return the deterministic detail filename for one task."""

        return f"task-{int(task_id)}.json"

    def safe_filename(self, filename: str) -> str:
        """Normalize a stored filename so callers cannot escape the directory."""

        name = filename.strip().replace("\\", "/").rsplit("/", 1)[-1]
        stem = name.removeprefix("task-").removesuffix(".json")
        if not name.startswith("task-") or not name.endswith(".json") or not stem.isdigit():
            return ""
        return name
