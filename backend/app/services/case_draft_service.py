from __future__ import annotations

from typing import Any

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.repositories.interfaces import ResourceRepository
from app.services.test_case_service import test_case_table


class CaseDraftService:
    def __init__(self, case_type: str, repository: ResourceRepository) -> None:
        self.case_type = case_type.upper()
        self.repository = repository
        self.case_table = test_case_table(self.case_type)

    def list(
        self,
        project_id: int | None,
        keyword: str | None,
        page: int,
        page_size: int,
        status: str | None = None,
        source_id: int | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        data_filters: dict[str, Any] = {"case_type": self.case_type}
        if status:
            data_filters["status"] = status
        if source_id is not None:
            data_filters["source_id"] = source_id
        rows, total = self.repository.list(
            "case_drafts",
            keyword,
            project_id,
            page,
            page_size,
            data_filters,
        )
        rows = [self._display_draft(item) for item in rows]
        return rows, total

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.repository.create("case_drafts", self._create_payload(payload))

    def create_many(self, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = [self._create_payload(payload) for payload in payloads]
        return self.repository.create_many("case_drafts", rows)

    def _create_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = dict(payload)
        payload["case_type"] = self.case_type
        payload.setdefault("status", "draft")
        case_json = self._without_request_wrapper(payload.get("case_json", {}))
        case_json["case_type"] = self.case_type
        assertions = self._list_value(payload.get("assertions")) or self._list_value(case_json.get("assertions"))
        strategy_ids = self._strategy_ids(payload.get("strategy_ids")) or self._strategy_ids(case_json.get("strategy_ids"))
        strategy_ids.extend(self._strategy_ids(case_json.get("strategies")))
        strategy_ids.extend(self._strategy_ids(case_json.get("strategy")))
        case_json = self._clean_case_json(case_json)
        if case_json:
            payload["case_json"] = case_json
        data = dict(payload.get("data") or case_json or payload.get("case_json", {}))
        data["case_type"] = self.case_type
        payload["data"] = self._clean_case_json(data)
        payload["assertions"] = assertions
        payload["strategy_ids"] = self._dedupe_ints(strategy_ids)
        return payload

    def update(self, draft_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        if "case_json" in payload:
            payload["case_json"] = self._without_request_wrapper(payload["case_json"])
            payload.setdefault("assertions", self._list_value(payload["case_json"].get("assertions")))
            payload.setdefault("strategy_ids", self._case_strategy_ids(payload["case_json"]))
            payload["case_json"] = self._clean_case_json(payload["case_json"])
            payload["case_json"]["case_type"] = self.case_type
        if "data" in payload:
            payload["data"] = self._without_request_wrapper(payload["data"])
            payload.setdefault("assertions", self._list_value(payload["data"].get("assertions")))
            payload.setdefault("strategy_ids", self._case_strategy_ids(payload["data"]))
            payload["data"] = self._clean_case_json(payload["data"])
            payload["data"]["case_type"] = self.case_type
        if "strategy_ids" in payload:
            payload["strategy_ids"] = self._dedupe_ints(self._strategy_ids(payload["strategy_ids"]))
        item = self.repository.update("case_drafts", draft_id, payload)
        if not item:
            raise ResourceNotFoundError("用例草稿不存在")
        return self._display_draft(item)

    def accept(self, draft_id: int) -> dict[str, Any]:
        draft = self.repository.get("case_drafts", draft_id)
        if not draft:
            raise ResourceNotFoundError("用例草稿不存在")
        if draft.get("status") != "draft":
            raise BusinessRuleError("只有草稿状态可以采纳")
        case_json = self._case_json(draft)
        case = self.repository.create(
            self.case_table,
            {
                "name": draft["name"],
                "project_id": draft.get("project_id"),
                "case_type": self.case_type,
                "source_id": draft.get("source_id"),
                "description": draft.get("description"),
                "status": "active",
                "data": case_json,
                "steps": self._steps(case_json),
                "assertions": self._draft_assertions(draft),
                "strategy_ids": self._draft_strategy_ids(draft),
            },
        )
        self.repository.update("case_drafts", draft_id, {"status": "accepted"})
        return case

    def reject(self, draft_id: int, comment: str | None) -> dict[str, Any]:
        return self.update(draft_id, {"status": "rejected", "review_comment": comment})

    def accept_many(self, ids: list[int]) -> dict[str, int]:
        count = 0
        skipped = 0
        for draft_id in set(ids):
            draft = self.repository.get("case_drafts", draft_id)
            if not draft or draft.get("status") != "draft":
                skipped += 1
                continue
            self.accept(draft_id)
            count += 1
        return {"accepted_count": count, "skipped_count": skipped}

    def delete(self, draft_id: int) -> bool:
        if not self.repository.delete("case_drafts", draft_id):
            raise ResourceNotFoundError("用例草稿不存在")
        return True

    def batch_delete(self, ids: list[int]) -> dict[str, int]:
        return {"deleted_count": self.repository.batch_delete("case_drafts", ids)}

    def _case_json(self, draft: dict[str, Any]) -> dict[str, Any]:
        value = draft.get("case_json") or draft.get("data") or {}
        case_json = self._without_request_wrapper(value)
        if case_json:
            case_json["case_type"] = self.case_type
        return self._clean_case_json(case_json)

    def _display_draft(self, draft: dict[str, Any]) -> dict[str, Any]:
        item = dict(draft)
        case_json = self._case_json(item)
        if case_json:
            item["case_json"] = case_json
            item["data"] = case_json
        item["assertions"] = self._draft_assertions(item)
        item["strategy_ids"] = self._draft_strategy_ids(item)
        return item

    def _steps(self, case_json: dict[str, Any]) -> list[dict[str, Any]]:
        steps = self._list_value(case_json.get("steps"))
        if steps:
            return steps
        request = case_json.get("request")
        if isinstance(request, dict):
            return self._list_value(request.get("steps"))
        return []

    def _without_request_wrapper(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        request = value.get("request")
        if not isinstance(request, dict):
            return value
        merged = {**request, **{key: item for key, item in value.items() if key != "request"}}
        return merged

    def _clean_case_json(self, value: dict[str, Any]) -> dict[str, Any]:
        return {
            key: item
            for key, item in value.items()
            if key not in {"assertions", "strategies", "strategy", "strategy_ids"}
        }

    def _draft_assertions(self, draft: dict[str, Any]) -> list[dict[str, Any]]:
        assertions = self._list_value(draft.get("assertions"))
        if assertions:
            return assertions
        data = draft.get("data") if isinstance(draft.get("data"), dict) else {}
        case_json = draft.get("case_json") if isinstance(draft.get("case_json"), dict) else {}
        return self._list_value(data.get("assertions") or case_json.get("assertions"))

    def _draft_strategy_ids(self, draft: dict[str, Any]) -> list[int]:
        ids = self._strategy_ids(draft.get("strategy_ids"))
        data = draft.get("data") if isinstance(draft.get("data"), dict) else {}
        case_json = draft.get("case_json") if isinstance(draft.get("case_json"), dict) else {}
        ids.extend(self._case_strategy_ids(data))
        ids.extend(self._case_strategy_ids(case_json))
        return self._dedupe_ints(ids)

    def _case_strategy_ids(self, case_json: dict[str, Any]) -> list[int]:
        ids = self._strategy_ids(case_json.get("strategy_ids"))
        ids.extend(self._strategy_ids(case_json.get("strategies")))
        ids.extend(self._strategy_ids(case_json.get("strategy")))
        return ids

    def _strategy_ids(self, value: Any) -> list[int]:
        values = value if isinstance(value, list) else [value]
        result: list[int] = []
        for item in values:
            if isinstance(item, dict):
                item = item.get("id")
            try:
                result.append(int(item))
            except (TypeError, ValueError):
                continue
        return result

    def _dedupe_ints(self, values: list[int]) -> list[int]:
        result: list[int] = []
        seen: set[int] = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    def _list_value(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    def _case_type(self, item: dict[str, Any]) -> str:
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        return str(item.get("case_type") or data.get("case_type") or "").upper()
