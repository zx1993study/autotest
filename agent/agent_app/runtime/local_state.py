from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path


def runtime_path(node_key: str) -> Path:
    root = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "AutotestAgent" / "runtime"
    return root / f"{hashlib.sha256(node_key.encode()).hexdigest()[:24]}.json"


def write_state(config, status, task_id=None):
    path = runtime_path(config.node_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps({"pid": os.getpid(), "status": status, "current_task_id": task_id, "updated_at": time.time()}), encoding="utf-8")
    temp.replace(path)


def read_state(config_path):
    try:
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
        path = runtime_path(str(config["node_key"]))
        from agent_app.utils.file_lease import FileLease

        probe = FileLease(path.with_suffix(".lock"))
        if probe.acquire():
            probe.release()
            return {}
        state = json.loads(path.read_text(encoding="utf-8"))
        return state
    except (OSError, ValueError, KeyError):
        pass
    return {}
