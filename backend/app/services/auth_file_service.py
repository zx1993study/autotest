from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


AUTH_DIR = Path(__file__).resolve().parents[2] / "storage" / "auth"


class AuthFileService:
    def save_json(self, filename: str, payload: dict[str, Any]) -> str:
        safe_name = self.safe_filename(filename)
        AUTH_DIR.mkdir(parents=True, exist_ok=True)
        path = AUTH_DIR / safe_name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return safe_name

    def exists(self, filename: str) -> bool:
        """Return whether the sanitized auth JSON file already exists.

        Save paths are always normalized through ``safe_filename`` so callers
        can safely check user-provided or database-provided file names without
        leaking access outside the auth storage directory.
        """

        safe_name = self.safe_filename(filename)
        return (AUTH_DIR / safe_name).exists()

    def load_json(self, filename: str) -> dict[str, Any]:
        safe_name = self.safe_filename(filename)
        path = AUTH_DIR / safe_name
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def safe_filename(self, value: str) -> str:
        name = value.strip().replace("\\", "/").rsplit("/", 1)[-1]
        name = re.sub(r"[^0-9A-Za-z._-]+", "_", name)
        name = name.strip("._") or "auth"
        if not name.endswith(".json"):
            name = f"{name}.json"
        return name
