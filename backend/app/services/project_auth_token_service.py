"""Encrypt project tokens at rest; keep encryption keys outside the database."""
from __future__ import annotations

import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.exceptions import BusinessRuleError
from app.core.storage import storage_path
from app.services.auth_file_service import AuthFileService

TOKEN_KEYS = ("token", "access_token", "accessToken", "value")
TOKEN_SECRET_KEYS = (*TOKEN_KEYS, "token_encrypted")


class ProjectAuthTokenService:
    def _cipher(self, create: bool = False) -> Fernet:
        configured = os.environ.get("PROJECT_AUTH_ENCRYPTION_KEY", "").strip()
        path = storage_path("project-auth-secrets", "key")
        if not configured and create:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            try:
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(Fernet.generate_key())
        try:
            return Fernet(configured.encode() if configured else path.read_bytes())
        except (OSError, ValueError) as exc:
            raise BusinessRuleError("Token 加密密钥不可用，请检查持久化存储或恢复备份") from exc

    def encrypt(self, token: str) -> str:
        return self._cipher(create=True).encrypt(token.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        try:
            return self._cipher().decrypt(encrypted.encode()).decode()
        except (InvalidToken, UnicodeError, AttributeError, TypeError) as exc:
            raise BusinessRuleError("Token 解密失败，请检查共享密钥或重新保存鉴权") from exc

    @staticmethod
    def public_auth(auth: dict[str, Any]) -> dict[str, Any]:
        result = dict(auth)
        data = dict(result.get("data") or {})
        data["token_saved"] = bool(any(data.get(key) for key in TOKEN_SECRET_KEYS) or data.get("token_file"))
        data["token_storage"] = "database" if data.get("token_encrypted") else ("file" if data.get("token_file") else "")
        data["token_storage_label"] = {"database": "数据库（加密）", "file": "旧鉴权文件"}.get(data["token_storage"], "")
        for key in TOKEN_SECRET_KEYS:
            data.pop(key, None)
        result["data"] = data
        return result

    @staticmethod
    def remove_unused_file(repository, filename: str) -> None:
        ProjectAuthTokenService.remove_unused_files(repository, {filename})

    @staticmethod
    def remove_unused_files(repository, filenames: set[str]) -> None:
        files = AuthFileService()
        unused = {files.safe_filename(filename) for filename in filenames if filename}
        if not unused:
            return
        page = 1
        while True:
            rows, total = repository.list("project_auth", page=page, page_size=200)
            for row in rows:
                other = (row.get("data") or {}).get("token_file")
                if other:
                    unused.discard(files.safe_filename(str(other)))
            if not unused:
                return
            if page * 200 >= total:
                break
            page += 1
        for filename in unused:
            files.delete_json(filename)
