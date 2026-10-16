from __future__ import annotations

import hashlib
import re
import uuid

from app.core.exceptions import BusinessRuleError
from app.core.storage import storage_path


class AgentArtifactService:
    def __init__(self, repository) -> None:
        self.repository = repository

    async def save_video(self, task_id, node_key, digest, stream):
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise BusinessRuleError("Invalid artifact digest")
        task = self.repository.get("agent_tasks", task_id)
        if not task or (task.get("data") or {}).get("claimed_by") != node_key:
            raise BusinessRuleError("Task belongs to another node")
        root = storage_path("app-recordings")
        root.mkdir(parents=True, exist_ok=True)
        filename = f"agent_{task_id}_{digest}.mp4"
        target = root / filename
        temp = root / f".{uuid.uuid4().hex}.upload"
        hashed, size = hashlib.sha256(), 0
        try:
            with temp.open("wb") as file:
                async for chunk in stream:
                    size += len(chunk)
                    if size > 200 * 1024 * 1024:
                        raise BusinessRuleError("Video exceeds 200 MiB")
                    hashed.update(chunk)
                    file.write(chunk)
            if size < 12 or hashed.hexdigest() != digest:
                raise BusinessRuleError("Artifact checksum failed")
            with temp.open("rb") as file:
                header = file.read(12)
                task_data = task.get("data") or {}
                web_task = task_data.get("task_type") == "web_replay" or (task_data.get("task_type") == "case_execution" and task_data.get("payload", {}).get("case_type") == "WEB")
                if header[:4] == b"\x1aE\xdf\xa3" and web_task:
                    filename = f"agent_{task_id}_{digest}.webm"
                    target = root / filename
                elif header[4:8] != b"ftyp":
                    raise BusinessRuleError("Artifact is not a supported recording")
            temp.replace(target)
            return {"video_file": filename, "video_url": f"/api/v1/app-recordings/{filename}"}
        finally:
            temp.unlink(missing_ok=True)
