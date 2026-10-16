from __future__ import annotations

import time
from typing import Any

from app.core.exceptions import BusinessRuleError
from app.repositories.interfaces import ResourceRepository
from app.services.ai_secret_service import AiSecretService
from app.services.resource_service import ResourceService
from app.utils.model_api_request import model_protocol


class AiModelResourceService(ResourceService):
    def __init__(self, repository: ResourceRepository) -> None:
        super().__init__("ai_models", repository)
        self.secret_service = AiSecretService()

    def list(
        self,
        keyword: str | None,
        project_id: int | None,
        page: int,
        page_size: int,
        data_filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        items, total = super().list(keyword, project_id, page, page_size, data_filters)
        return [self._hide_secret(item) for item in items], total

    def get(self, item_id: int) -> dict[str, Any]:
        return self._hide_secret(super().get(item_id))

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        item = super().create(self._prepare_payload(payload))
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        if data.get("is_current") is True:
            item = self.set_current(item["id"])
        return self._hide_secret(item)

    def update(self, item_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        item = super().update(item_id, self._prepare_payload(payload, item_id))
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        if data.get("is_current") is True:
            item = self.set_current(item_id)
        return self._hide_secret(item)

    def active_model(self, model_id: int | None = None) -> dict[str, Any]:
        if model_id:
            model = super().get(model_id)
            if model.get("status") != "active":
                raise BusinessRuleError("AI模型未启用")
            return model

        current = self.current_model(include_fallback=True)
        if current:
            return current
        raise BusinessRuleError("请先配置并启用AI模型")

    def current_model(self, include_fallback: bool = True) -> dict[str, Any] | None:
        models, _ = super().list(None, None, 1, 1000)
        active_models = [model for model in models if model.get("status") == "active"]
        for model in active_models:
            data = model.get("data") if isinstance(model.get("data"), dict) else {}
            if data.get("is_current") is True:
                return model
        return active_models[0] if include_fallback and active_models else None

    def current_model_safe(self) -> dict[str, Any] | None:
        model = self.current_model(include_fallback=True)
        return self._hide_secret(model) if model else None

    def set_current(self, item_id: int) -> dict[str, Any]:
        target = super().get(item_id)
        if target.get("status") != "active":
            raise BusinessRuleError("只能将启用状态的模型设为当前模型")

        models, _ = super().list(None, None, 1, 1000)
        for model in models:
            data = dict(model.get("data") or {})
            if model["id"] == item_id:
                data["is_current"] = True
            elif data.get("is_current") is True:
                data["is_current"] = False
            else:
                continue
            super().update(model["id"], {"data": data})

        return super().get(item_id)

    def api_key(self, model: dict[str, Any]) -> str:
        data = model.get("data") if isinstance(model.get("data"), dict) else {}
        return self.secret_service.load_api_key(str(data.get("api_key_file") or ""))

    def _prepare_payload(self, payload: dict[str, Any], item_id: int | None = None) -> dict[str, Any]:
        copied = dict(payload)
        data = dict(copied.get("data") or {})
        try:
            model_protocol(data)
        except ValueError as exc:
            raise BusinessRuleError("不支持的 AI 调用协议") from exc
        api_key = data.pop("api_key", None)
        if isinstance(api_key, str) and api_key.strip():
            secret_name = self._secret_name(copied, item_id)
            data["api_key_file"] = self.secret_service.save_api_key(secret_name, api_key.strip())
        copied["data"] = data
        copied.setdefault("status", "active")
        return copied

    def _secret_name(self, payload: dict[str, Any], item_id: int | None) -> str:
        model_name = str(payload.get("name") or f"model-{item_id or 'new'}")
        return f"{model_name}-{int(time.time())}.json"

    def _hide_secret(self, item: dict[str, Any] | None) -> dict[str, Any] | None:
        if not item:
            return None
        copied = dict(item)
        data = dict(copied.get("data") or {})
        data.pop("api_key", None)
        copied["data"] = data
        return copied
