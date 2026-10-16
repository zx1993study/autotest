from __future__ import annotations

import json
from pathlib import Path


class ResultOutbox:
    """Persist completed work before networking so reconnection never replays it."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True, mode=0o700)

    def save(self, task_id: int, report: dict) -> None:
        target = self.path / f"{int(task_id)}.json"
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        temp.replace(target)

    def drain(self, task_api) -> int:
        sent = 0
        for path in sorted(self.path.glob("*.json")):
            report = json.loads(path.read_text(encoding="utf-8-sig"))
            task_id = int(path.stem)
            task_api.prepare_artifacts(task_id, report)
            task_api.report(task_id, **report)
            path.unlink()
            sent += 1
        return sent
