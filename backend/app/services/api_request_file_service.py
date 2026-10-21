import hashlib
import os
import tempfile

from fastapi import HTTPException

from app.core.storage import storage_path
from app.repositories.interfaces import ResourceRepository
from app.schemas.api_request_file import MAX_API_FILE_SIZE, ApiRequestFile


class ApiRequestFileService:
    """Own API request fixtures independently of execution evidence."""

    def __init__(self, repository: ResourceRepository):
        self.repository = repository

    def _root(self, project_id: int):
        if not self.repository.get("projects", project_id):
            raise HTTPException(404, "项目不存在")
        return storage_path("api-request-files", str(project_id))

    def save(self, project_id: int, filename: str, content_type: str, content: bytes) -> dict:
        reference = ApiRequestFile(filename=filename, content_type=content_type,
                                   sha256=hashlib.sha256(content).hexdigest(), size=len(content))
        root = self._root(project_id)
        root.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(prefix=".upload-", dir=root)
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(content)
            os.replace(temporary, root / reference.sha256)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return reference.model_dump()

    def read(self, project_id: int, reference: ApiRequestFile) -> bytes:
        root = self._root(project_id).resolve()
        path = root / reference.sha256
        if path.is_symlink() or path.resolve().parent != root:
            raise ValueError("API 请求文件引用无效")
        if not path.is_file() or path.stat().st_size != reference.size:
            raise ValueError("API 请求文件不存在或大小已变化，请重新上传")
        with path.open("rb") as stream:
            content = stream.read(MAX_API_FILE_SIZE + 1)
        if len(content) != reference.size or hashlib.sha256(content).hexdigest() != reference.sha256:
            raise ValueError("API 请求文件校验失败，请重新上传")
        return content
