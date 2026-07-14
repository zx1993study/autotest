from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


AI_SECRET_DIR = Path(__file__).resolve().parents[2] / "storage" / "ai-secrets"


class AiSecretService:
    def save_api_key(self, name: str, api_key: str) -> str:
        safe_name = self.safe_filename(name)
        AI_SECRET_DIR.mkdir(parents=True, exist_ok=True)
        path = AI_SECRET_DIR / safe_name
        path.write_text(
            json.dumps({"api_key": api_key}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return safe_name

    def load_api_key(self, filename: str | None) -> str:
        if not filename:
            return ""
        path = AI_SECRET_DIR / self.safe_filename(filename)
        if not path.exists():
            return ""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return ""
        if not isinstance(data, dict):
            return ""
        value = data.get("api_key")
        return value if isinstance(value, str) else ""

    def safe_filename(self, value: str) -> str:
        name = value.strip().replace("\\", "/").rsplit("/", 1)[-1]
        name = re.sub(r"[^0-9A-Za-z._-]+", "_", name)
        name = name.strip("._") or "ai-model"
        if not name.endswith(".json"):
            name = f"{name}.json"
        return name
