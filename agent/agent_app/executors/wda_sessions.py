from __future__ import annotations

import hashlib
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from agent_app.utils.file_lease import FileLease


class WdaSessionPool:
    def __init__(self, artifacts_dir: Path, client_factory=None) -> None:
        self.artifacts_dir = artifacts_dir
        self.client_factory = client_factory
        self.sessions: dict[tuple[str, str, str], Any] = {}
        self.locks: dict[str, threading.Lock] = {}
        self.guard = threading.Lock()

    @contextmanager
    def connect(self, device: dict[str, Any], bundle_id: str, current_screen: bool = True):
        data = device.get("data", device)
        url = str(data.get("wda_url") or data.get("wdaUrl") or "").rstrip("/")
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Device must have a valid WDA URL without credentials")
        udid = str(data.get("udid") or data.get("serial") or url)
        key = (udid, url, bundle_id)
        with self.guard:
            lock = self.locks.setdefault(udid, threading.Lock())
        digest = hashlib.sha256(udid.encode()).hexdigest()
        shared_locks = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "AutotestAgent" / "device-locks"
        with lock, FileLease(shared_locks / f"device-{digest}.lock"):
            session, reused = self._healthy_session(key, url, bundle_id, current_screen)
            try:
                yield session, reused
            except Exception:
                # Never replay a possibly completed action when the session breaks.
                for cached_key, cached in list(self.sessions.items()):
                    if cached is session:
                        self.sessions.pop(cached_key, None)
                raise

    def bind(self, device, bundle_id, session):
        data = device.get('data', device)
        url = str(data.get('wda_url') or data.get('wdaUrl') or '').rstrip('/')
        udid = str(data.get('udid') or data.get('serial') or url)
        with self.guard:
            for key, cached in list(self.sessions.items()):
                if cached is session:
                    self.sessions.pop(key, None)
            self.sessions[(udid,url,bundle_id)] = session

    def _healthy_session(self, key, url, bundle_id, current_screen):
        session = self.sessions.get(key)
        if session is not None:
            try:
                session.window_size()
                if not current_screen and bundle_id:
                    session.app_launch(bundle_id)
                return session, True
            except Exception:  # noqa: BLE001 - recreate invalid SDK sessions before any new action.
                self.sessions.pop(key, None)
        if self.client_factory is None:
            import wda

            client = wda.Client(url)
        else:
            client = self.client_factory(url)
        client.unregister_callback()
        session = client.session(None if current_screen else bundle_id or None)
        session.unregister_callback()
        self.sessions[key] = session
        return session, False
