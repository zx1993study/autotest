from typing import Any

from app.repositories.interfaces import ResourceRepository
from app.services.case_draft_service import CaseDraftService


class TestGenerationService:
    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def generate_api_drafts(
        self,
        project_id: int,
        source_ids: list[int],
        strategy: str,
    ) -> dict[str, int]:
        interfaces = self._items("api_interfaces", project_id, source_ids)
        fields = self._items("api_fields", project_id, [])
        count = 0
        for item in interfaces:
            item_fields = [
                field for field in fields if field.get("data", {}).get("interface_id") == item["id"]
            ]
            for case_json in self._api_case_jsons(item, item_fields, strategy):
                self._create_draft("API", project_id, item["id"], case_json)
                count += 1
        return {"draft_count": count}

    def generate_asset_drafts(
        self,
        case_type: str,
        asset_table: str,
        element_table: str,
        project_id: int,
        source_ids: list[int],
        strategy: str,
    ) -> dict[str, int]:
        assets = self._items(asset_table, project_id, source_ids)
        elements = self._items(element_table, project_id, [])
        count = 0
        for asset in assets:
            asset_elements = [
                item for item in elements if item.get("data", {}).get("page_id") == asset["id"]
            ]
            for case_json in self._ui_case_jsons(case_type, asset, asset_elements, strategy):
                self._create_draft(case_type, project_id, asset["id"], case_json)
                count += 1
        return {"draft_count": count}

    def _items(
        self,
        table: str,
        project_id: int,
        ids: list[int],
    ) -> list[dict[str, Any]]:
        items, _ = self.repository.list(table, project_id=project_id, page_size=10000)
        if ids:
            allowed = set(ids)
            items = [item for item in items if item["id"] in allowed]
        return items

    def _create_draft(
        self,
        case_type: str,
        project_id: int,
        source_id: int,
        case_json: dict[str, Any],
    ) -> None:
        CaseDraftService(case_type, self.repository).create(
            {
                "name": case_json["name"],
                "project_id": project_id,
                "case_type": case_type,
                "source_id": source_id,
                "status": "draft",
                "case_json": case_json,
                "data": case_json,
            }
        )

    def _api_case_jsons(
        self,
        interface: dict[str, Any],
        fields: list[dict[str, Any]],
        strategy: str,
    ) -> list[dict[str, Any]]:
        method = interface.get("data", {}).get("method", "GET")
        path = interface.get("data", {}).get("path", interface["name"])
        base = {
            "method": method,
            "path": path,
            "headers": {},
            "query": {},
            "body": {},
        }
        for field in fields:
            data = field.get("data", {})
            location = data.get("location", "body")
            value = data.get("example") or self._normal_value(data)
            if location in {"query", "header"}:
                base[f"{location}s" if location == "header" else location][data["name"]] = value
            elif location == "body":
                base["body"][data["name"]] = value
        cases = [
            self._case_json("API", f"[正常] {method} {path}", "normal", base, 200),
        ]
        if strategy in {"basic", "full"}:
            for field in fields:
                data = field.get("data", {})
                if not data.get("required"):
                    continue
                request = self._without_field(base, data)
                cases.append(
                    self._case_json(
                        "API",
                        f"[缺失必填] {data.get('name')}",
                        "required_missing",
                        request,
                        400,
                    )
                )
        if strategy == "full":
            for field in fields:
                data = field.get("data", {})
                request = self._replace_field(base, data, self._invalid_value(data))
                cases.append(
                    self._case_json("API", f"[异常] {data.get('name')}", "invalid", request, 400)
                )
        return cases

    def _ui_case_jsons(
        self,
        case_type: str,
        asset: dict[str, Any],
        elements: list[dict[str, Any]],
        strategy: str,
    ) -> list[dict[str, Any]]:
        steps = []
        for element in elements:
            data = element.get("data", {})
            element_type = str(data.get("element_type") or data.get("type") or "").lower()
            action = data.get("action") or self._ui_action_for_type(element_type)
            steps.append(
                {
                    "element_id": element["id"],
                    "name": element["name"],
                    "action": action,
                    "value": self._ui_default_value(element, action),
                    "locator": data.get("locator"),
                    "locator_type": data.get("locator_type"),
                    "locator_method": data.get("locator_method") or data.get("locator_type"),
                    "locator_args": data.get("locator_args"),
                    "role": data.get("role"),
                    "role_name": data.get("role_name"),
                    "resource_id": data.get("resource_id"),
                    "css": data.get("css"),
                    "text": data.get("text"),
                    "content_desc": data.get("content_desc"),
                    "xpath": data.get("xpath"),
                    "platform": data.get("platform"),
                    "element_type": data.get("element_type") or data.get("type"),
                }
            )
        cases = [self._case_json(case_type, f"[正常流程] {asset['name']}", "normal", {"steps": steps}, 0)]
        if strategy in {"basic", "full"}:
            required = [item for item in elements if item.get("data", {}).get("required")]
            for element in required:
                data = element.get("data", {})
                error_steps = [self._required_empty_step(step, element["id"]) for step in steps]
                cases.append(
                    self._case_json(
                        case_type,
                        f"[必填为空] {element['name']}",
                        "required_empty",
                        {"steps": error_steps, "focus": data.get("locator")},
                        0,
                    )
                )
        return cases

    def _required_empty_step(self, step: dict[str, Any], element_id: int) -> dict[str, Any]:
        copied = dict(step)
        if copied.get("element_id") == element_id and copied.get("action") == "fill":
            copied["value"] = ""
            copied["empty_target"] = True
        return copied

    def _ui_default_value(self, element: dict[str, Any], action: str) -> Any:
        data = element.get("data", {})
        value = data.get("default_value")
        if value not in (None, ""):
            return value
        value = data.get("example")
        if value not in (None, ""):
            return value
        if action != "fill":
            return None
        text = " ".join(
            str(item or "").lower()
            for item in (
                element.get("name"),
                data.get("name"),
                data.get("label"),
                data.get("placeholder"),
                data.get("locator"),
                data.get("locator_args"),
                data.get("role_name"),
            )
        )
        if any(marker in text for marker in ("password", "passwd", "pwd", "密码", "口令")):
            return "123456"
        if any(marker in text for marker in ("phone", "mobile", "手机号", "手机")):
            return "13800138000"
        if any(marker in text for marker in ("email", "mail", "邮箱")):
            return "test@example.com"
        if any(marker in text for marker in ("username", "user name", "account", "login", "账号", "账户", "用户名")):
            return "test_user"
        return "test"

    def _ui_action_for_type(self, element_type: str) -> str:
        if element_type in {"input", "textarea", "text"}:
            return "fill"
        if element_type in {"select", "dropdown"}:
            return "select"
        if element_type == "multi_select":
            return "multi_select"
        if element_type in {"checkbox", "radio"}:
            return "check"
        return "click"

    def _case_json(
        self,
        case_type: str,
        name: str,
        category: str,
        request: dict[str, Any],
        expected_status: int,
    ) -> dict[str, Any]:
        return {
            "name": name,
            "case_type": case_type,
            "category": category,
            **request,
            "assertions": [{"type": "status", "expected": expected_status}],
        }

    def _without_field(self, request: dict[str, Any], field: dict[str, Any]) -> dict[str, Any]:
        copied = {
            "method": request["method"],
            "path": request["path"],
            "headers": dict(request["headers"]),
            "query": dict(request["query"]),
            "body": dict(request["body"]),
        }
        location = field.get("location", "body")
        if location == "query":
            copied["query"].pop(field["name"], None)
        elif location == "header":
            copied["headers"].pop(field["name"], None)
        else:
            copied["body"].pop(field["name"], None)
        return copied

    def _replace_field(
        self,
        request: dict[str, Any],
        field: dict[str, Any],
        value: Any,
    ) -> dict[str, Any]:
        copied = self._without_field(request, {"name": "__none__", "location": "body"})
        location = field.get("location", "body")
        if location == "query":
            copied["query"][field["name"]] = value
        elif location == "header":
            copied["headers"][field["name"]] = value
        else:
            copied["body"][field["name"]] = value
        return copied

    def _normal_value(self, field: dict[str, Any]) -> Any:
        data_type = field.get("field_type") or field.get("type", "string")
        if data_type in {"integer", "number"}:
            return 1
        if data_type == "boolean":
            return True
        return "test"

    def _invalid_value(self, field: dict[str, Any]) -> Any:
        data_type = field.get("field_type") or field.get("type", "string")
        if data_type in {"integer", "number"}:
            return "not-a-number"
        if data_type == "boolean":
            return "not-a-boolean"
        return ""
