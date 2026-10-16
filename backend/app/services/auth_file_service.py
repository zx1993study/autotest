from __future__ import annotations

import json
import os
import re
import tempfile
from contextlib import contextmanager
from threading import RLock
from typing import Any

from app.core.storage import storage_path

AUTH_DIR = storage_path("auth")
_WRITE_LOCK = RLock()


class AuthFileService:
    def save_json(self, filename: str, payload: dict[str, Any]) -> str:
        safe_name = self.safe_filename(filename)
        with _WRITE_LOCK:
            self._replace_bytes(safe_name, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
        return safe_name

    @contextmanager
    def replace_json(self, filename: str, payload: dict[str, Any]):
        safe_name = self.safe_filename(filename)
        with _WRITE_LOCK:
            path = AUTH_DIR / safe_name
            previous = path.read_bytes() if path.exists() else None
            self.save_json(safe_name, payload)
            try:
                yield safe_name
            except Exception:
                if previous is None:
                    path.unlink(missing_ok=True)
                else:
                    self._replace_bytes(safe_name, previous)
                raise

    def _replace_bytes(self, filename: str, content: bytes) -> None:
        AUTH_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temporary = tempfile.mkstemp(prefix=".auth-", dir=AUTH_DIR)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, AUTH_DIR / filename)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

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
            data = json.loads(path.read_text(encoding="utf-8-sig"))
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
