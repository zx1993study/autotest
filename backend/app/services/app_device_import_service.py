from datetime import UTC, datetime
from urllib.parse import urlsplit

from app.core.exceptions import BusinessRuleError

DEVICE_FIELDS = ("platform", "udid", "device_name", "device_form_factor", "platform_version", "product_type", "model", "manufacturer", "connection_type", "wda_url", "wda_status", "node_key", "source", "connection_status")


class AppDeviceImportService:
    def __init__(self, repository):
        self.repository = repository

    def import_discovered(self, payload):
        rows = self._all_devices()
        created, updated, skipped = [], [], []
        for item in payload.items:
            data = {key: item[key] for key in DEVICE_FIELDS if item.get(key) is not None}
            if not data.get("udid") or not data.get("platform"):
                skipped.append({"reason": "缺少平台或 UDID"})
                continue
            self._validate_url(data.get("wda_url"))
            data["tags"] = payload.tags if payload.tags is not None else item.get("tags", "")
            if data.get("connection_status") == "online":
                data["last_seen_at"] = datetime.now(UTC).isoformat()
            existing = self._match(rows, data)
            if existing and not payload.update_existing:
                skipped.append({"existing_id": existing["id"], "reason": "设备已存在"})
            elif existing:
                old_data = existing.get("data") or {}
                if old_data.get("node_key") and old_data["node_key"] != data.get("node_key"):
                    raise BusinessRuleError("设备已绑定其他执行节点，请先修改绑定")
                values = {"status": "active", "data": {**old_data, **data}}
                if payload.project_id is not None:
                    values["project_id"] = payload.project_id
                updated.append(self.repository.update("app_devices", existing["id"], values))
            else:
                row = self.repository.create("app_devices", {"name": item.get("name") or data.get("device_name") or data["udid"], "project_id": payload.project_id, "status": "active", "data": data})
                created.append(row)
                rows.append(row)
        return {"created_count": len(created), "updated_count": len(updated), "skipped_count": len(skipped), "created": created, "updated": updated, "skipped": skipped}

    def _all_devices(self):
        rows, page = [], 1
        while True:
            items, total = self.repository.list("app_devices", page=page, page_size=200)
            rows.extend(items)
            if len(rows) >= total or not items:
                return rows
            page += 1

    @staticmethod
    def _match(rows, data):
        for row in rows:
            saved = row.get("data") or {}
            if saved.get("platform") == data["platform"] and saved.get("udid") == data["udid"]:
                return row
            if data.get("wda_url") and saved.get("node_key") == data.get("node_key") and str(saved.get("wda_url") or "").rstrip("/") == data["wda_url"].rstrip("/"):
                return row
        return None

    @staticmethod
    def _validate_url(url):
        if not url:
            return
        parsed = urlsplit(str(url))
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise BusinessRuleError("WDA 地址无效")
