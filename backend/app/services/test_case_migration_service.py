from __future__ import annotations

from typing import Any

from app.repositories.interfaces import ResourceRepository
from app.services.test_case_service import TEST_CASE_TABLES


class TestCaseMigrationService:
    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def migrate_legacy_test_cases(self) -> dict[str, int]:
        legacy_rows, _ = self.repository.list("test_cases", page=1, page_size=10000)
        migrated: dict[str, int] = {case_type: 0 for case_type in TEST_CASE_TABLES}
        for row in legacy_rows:
            case_type = self._case_type(row)
            target_table = TEST_CASE_TABLES.get(case_type)
            if not target_table or self._already_migrated(target_table, row):
                continue
            payload = self._payload(row, case_type)
            self.repository.create(target_table, payload)
            migrated[case_type] += 1
        return migrated

    def _already_migrated(self, target_table: str, legacy_case: dict[str, Any]) -> bool:
        rows, _ = self.repository.list(
            target_table,
            project_id=legacy_case.get("project_id"),
            page=1,
            page_size=10000,
        )
        legacy_id = str(legacy_case.get("id"))
        for row in rows:
            data = row.get("data") if isinstance(row.get("data"), dict) else {}
            if str(data.get("legacy_case_id") or "") == legacy_id:
                return True
        return False

    def _payload(self, row: dict[str, Any], case_type: str) -> dict[str, Any]:
        data = dict(row.get("data") or {})
        data["case_type"] = case_type
        data["legacy_case_id"] = row.get("id")
        payload = {
            "name": row.get("name"),
            "project_id": row.get("project_id"),
            "description": row.get("description"),
            "status": row.get("status") or "active",
            "case_type": case_type,
            "source_id": row.get("source_id"),
            "data": data,
            "steps": self._list_value(row.get("steps") or data.get("steps")),
            "assertions": self._list_value(row.get("assertions") or data.get("assertions")),
        }
        return payload

    def _case_type(self, row: dict[str, Any]) -> str:
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        return str(row.get("case_type") or data.get("case_type") or "").upper()

    def _list_value(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]
