from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from uuid import uuid4


def window_path(config):
    scope = hashlib.sha256(f"{config.server_url}|{config.node_key}".encode()).hexdigest()[:24]
    return Path(os.getenv("LOCALAPPDATA") or Path.home()) / "AutotestAgent/windows" / f"{scope}.json"


def read_window(config):
    try:
        data = json.loads(window_path(config).read_text(encoding="utf-8"))
        if time.time() - data["updated_at"] < 15:
            return data
    except (OSError, ValueError, KeyError):
        pass
    return {}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=True), encoding="utf-8")
    temporary.replace(path)


def request_local_show(config):
    current = read_window(config)
    if (current.get("window") or {}).get("status") != "open":
        raise ValueError("\u6ca1\u6709\u8fd0\u884c\u4e2d\u7684\u4efb\u52a1\u6d4f\u89c8\u5668")
    write_json(window_path(config).with_suffix(".show"), {
        "id": uuid4().hex, "window_id": current["window"]["window_id"], "created_at": time.time(),
    })
