import hashlib
import json
import os
import time
from urllib.parse import urlsplit


class WebLoginCache:
    """Node/project/origin-scoped login state, never included in reports."""

    def __init__(self, config, payload):
        discovery = payload.get("discovery") or {}
        location = urlsplit(payload["target_url"])
        self.origin = f"{location.scheme}://{location.netloc}"
        scope = f"{config.server_url}|{config.node_key}|{discovery.get('project_id')}|{discovery.get('auth_id')}|{self.origin}"
        self.path = config.artifacts_dir / "auth" / "web-login" / f"{hashlib.sha256(scope.encode()).hexdigest()}.json"

    def load(self):
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            if time.time() - value["saved_at"] < 3600 and isinstance(value.get("storage_state"), dict):
                return value
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return {}

    async def save(self, page):
        if await page.evaluate("location.origin") != self.origin:
            return
        state = await page.context.storage_state()
        session = await page.evaluate("Object.fromEntries(Object.entries(sessionStorage))")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as file:
            os.chmod(temporary, 0o600)
            json.dump({"saved_at": time.time(), "storage_state": state, "session_storage": session, "origin": self.origin}, file)
        temporary.replace(self.path)

    async def restore_session(self, page, cached):
        values = cached.get("session_storage") or {}
        if not values:
            return
        await page.context.add_init_script("if(location.origin === " + json.dumps(self.origin) + ") { for(const [k,v] of Object.entries(" + json.dumps(values) + ")) sessionStorage.setItem(k,v); }")
