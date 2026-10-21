"""Encrypt case passwords at rest and disclose them only to an owned active task."""
import os
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256

from cryptography.fernet import Fernet, InvalidToken

from app.core.exceptions import BusinessRuleError
from app.core.storage import storage_path
from app.services.agent_task_lease_service import AgentTaskLeaseService


class WebCaseSecretService:
    def __init__(self, repository=None):
        self.repository = repository

    @staticmethod
    def key_id():
        """Identify a shared encryption domain without disclosing its key."""
        try:
            key = storage_path('web-input-secrets', 'key').read_bytes()
            Fernet(key)
        except (OSError, ValueError):
            return ''
        return sha256(key).hexdigest()

    def _cipher(self, create=False):
        path = storage_path('web-input-secrets', 'key')
        if create:
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(descriptor, 'wb') as handle:
                    handle.write(Fernet.generate_key())
        try:
            return Fernet(path.read_bytes())
        except (OSError, ValueError) as exc:
            raise BusinessRuleError('密码加密密钥不可用，请检查持久化存储或恢复备份') from exc

    def protect(self, parameters, inputs, previous=None):
        keys = {p['key'] for p in parameters if p['type'] == 'password'}
        encrypted = {k: v for k, v in (previous or {}).items() if k in keys}
        for key in keys & inputs.keys():
            value = inputs.pop(key)
            if not isinstance(value, str) or len(value) > 2048:
                raise BusinessRuleError('密码须为不超过2048字符的文本')
            encrypted[key] = self._cipher(create=True).encrypt(value.encode()).decode()
        return encrypted

    def reveal(self, encrypted):
        if not encrypted:
            return {}
        try:
            cipher = self._cipher()
            return {k: cipher.decrypt(v.encode()).decode() for k, v in encrypted.items()}
        except (InvalidToken, UnicodeError, AttributeError) as exc:
            raise BusinessRuleError('密码解密失败，请重新编辑用例密码') from exc

    @staticmethod
    def public_case(case):
        result = deepcopy(case)
        data = result.get('data') or {}
        encrypted = data.pop('secret_inputs', {})
        data['secret_keys'] = list(encrypted)
        return result

    def task_inputs(self, task_id, node_key, lease_token):
        task = AgentTaskLeaseService(self.repository).owned_task(task_id, node_key, lease_token)
        data = task.get('data') or {}
        try:
            active = datetime.fromisoformat(data.get('lease_expires_at', '')) > datetime.now(UTC)
        except (ValueError, TypeError):
            active = False
        payload = data.get('payload') or {}
        if task.get('status') != 'running' or not active or data.get('cancel_requested') or payload.get('case_type') != 'WEB':
            raise BusinessRuleError('只能在有效租约内获取当前Web任务输入')
        return {str(c['id']): self.reveal(c.get('data', {}).get('secret_inputs')) for c in payload.get('cases', [])}
