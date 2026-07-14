from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.resource_record import ResourceRecord
from app.models.test_case_record import ApiTestCaseRecord, AppTestCaseRecord, MiniappTestCaseRecord, WebTestCaseRecord
from app.repositories.interfaces import ResourceRepository


COLUMN_KEYS = {
    "id",
    "table_name",
    "name",
    "project_id",
    "description",
    "status",
    "created_at",
    "updated_at",
    "deleted",
}

TEST_CASE_RECORDS = {
    "api_test_cases": (ApiTestCaseRecord, "API"),
    "web_test_cases": (WebTestCaseRecord, "WEB"),
    "app_test_cases": (AppTestCaseRecord, "APP"),
    "miniapp_test_cases": (MiniappTestCaseRecord, "MINIAPP"),
}


class SqlAlchemyResourceRepository(ResourceRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        table: str,
        keyword: str | None = None,
        project_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        data_filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        if table in TEST_CASE_RECORDS:
            return self._list_test_cases(table, keyword, project_id, page, page_size, data_filters)
        query = self.db.query(ResourceRecord).filter(
            ResourceRecord.table_name == table,
            ResourceRecord.deleted.is_(False),
        )
        if project_id is not None:
            query = query.filter(ResourceRecord.project_id == project_id)
        if keyword:
            pattern = f"%{keyword}%"
            query = query.filter(
                or_(
                    ResourceRecord.name.like(pattern),
                    ResourceRecord.description.like(pattern),
                )
            )
        for key, value in (data_filters or {}).items():
            if value is None or value == "":
                continue
            if key == "status":
                query = query.filter(ResourceRecord.status == str(value))
                continue
            if key in {"path", "api_path"}:
                query = query.filter(ResourceRecord.data_json["data"][key].as_string().like(f"%{value}%"))
                continue
            query = query.filter(self._json_value_filter(ResourceRecord.data_json["data"][key], value))
        total = query.count()
        order_by = (
            (ResourceRecord.id.asc(),)
            if table == "web_elements"
            else (ResourceRecord.updated_at.desc(), ResourceRecord.id.desc())
        )
        rows = (
            query.order_by(*order_by)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return [self._to_dict(row) for row in rows], total

    def get(self, table: str, item_id: int) -> dict[str, Any] | None:
        if table in TEST_CASE_RECORDS:
            return self._get_test_case(table, item_id)
        row = (
            self.db.query(ResourceRecord)
            .filter(
                ResourceRecord.table_name == table,
                ResourceRecord.id == item_id,
                ResourceRecord.deleted.is_(False),
            )
            .first()
        )
        return self._to_dict(row) if row else None

    def create(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        if table in TEST_CASE_RECORDS:
            return self._create_test_case(table, data)
        payload = dict(data)
        row = ResourceRecord(
            table_name=table,
            name=str(payload.get("name") or "Untitled"),
            project_id=payload.get("project_id"),
            description=payload.get("description"),
            status=str(payload.get("status") or "active"),
            data_json=self._extra_payload(payload),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_dict(row)

    def create_many(self, table: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if table in TEST_CASE_RECORDS:
            return [self._create_test_case(table, row) for row in rows]
        records = []
        for data in rows:
            payload = dict(data)
            records.append(
                ResourceRecord(
                    table_name=table,
                    name=str(payload.get("name") or "Untitled"),
                    project_id=payload.get("project_id"),
                    description=payload.get("description"),
                    status=str(payload.get("status") or "active"),
                    data_json=self._extra_payload(payload),
                )
            )
        if not records:
            return []
        self.db.add_all(records)
        self.db.flush()
        result = [self._to_dict(row) for row in records]
        self.db.commit()
        return result

    def update(self, table: str, item_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        if table in TEST_CASE_RECORDS:
            return self._update_test_case(table, item_id, data)
        row = (
            self.db.query(ResourceRecord)
            .filter(
                ResourceRecord.table_name == table,
                ResourceRecord.id == item_id,
                ResourceRecord.deleted.is_(False),
            )
            .first()
        )
        if not row:
            return None
        payload = {key: value for key, value in data.items() if value is not None}
        if "name" in payload:
            row.name = str(payload["name"])
        if "project_id" in payload:
            row.project_id = payload["project_id"]
        if "description" in payload:
            row.description = payload["description"]
        if "status" in payload:
            row.status = str(payload["status"])
        extra = dict(row.data_json or {})
        extra.update(self._extra_payload(payload))
        row.data_json = extra
        self.db.commit()
        self.db.refresh(row)
        return self._to_dict(row)

    def delete(self, table: str, item_id: int) -> bool:
        if table in TEST_CASE_RECORDS:
            return self._delete_test_case(table, item_id)
        row = (
            self.db.query(ResourceRecord)
            .filter(
                ResourceRecord.table_name == table,
                ResourceRecord.id == item_id,
                ResourceRecord.deleted.is_(False),
            )
            .first()
        )
        if not row:
            return False
        row.deleted = True
        self.db.commit()
        return True

    def batch_delete(self, table: str, ids: list[int]) -> int:
        count = 0
        for item_id in set(ids):
            if self.delete(table, item_id):
                count += 1
        return count

    def delete_by_project(self, table: str, project_id: int) -> int:
        if table in TEST_CASE_RECORDS:
            model, _ = TEST_CASE_RECORDS[table]
            count = (
                self.db.query(model)
                .filter(model.project_id == project_id, model.deleted.is_(False))
                .update({model.deleted: True}, synchronize_session=False)
            )
            self.db.commit()
            return int(count)
        count = (
            self.db.query(ResourceRecord)
            .filter(
                ResourceRecord.table_name == table,
                ResourceRecord.project_id == project_id,
                ResourceRecord.deleted.is_(False),
            )
            .update({ResourceRecord.deleted: True}, synchronize_session=False)
        )
        self.db.commit()
        return int(count)

    def _extra_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in payload.items() if key not in COLUMN_KEYS}

    def _to_dict(self, row: ResourceRecord) -> dict[str, Any]:
        payload = dict(row.data_json or {})
        item: dict[str, Any] = {
            "id": row.id,
            "name": row.name,
            "project_id": row.project_id,
            "description": row.description,
            "status": row.status,
            "data": payload.get("data", {}),
            "created_at": self._format_time(row.created_at),
            "updated_at": self._format_time(row.updated_at),
            "deleted": row.deleted,
        }
        for key, value in payload.items():
            if key not in item:
                item[key] = value
        return item

    def _format_time(self, value: datetime | None) -> str:
        if value is None:
            return ""
        return value.isoformat(timespec="seconds")

    def _json_value_filter(self, accessor: Any, value: Any) -> Any:
        if isinstance(value, int) and not isinstance(value, bool):
            return or_(accessor.as_integer() == value, accessor.as_string() == str(value))
        return accessor.as_string() == str(value)

    def _list_test_cases(
        self,
        table: str,
        keyword: str | None,
        project_id: int | None,
        page: int,
        page_size: int,
        data_filters: dict[str, Any] | None,
    ) -> tuple[list[dict[str, Any]], int]:
        model, _ = TEST_CASE_RECORDS[table]
        query = self.db.query(model).filter(model.deleted.is_(False))
        if project_id is not None:
            query = query.filter(model.project_id == project_id)
        if keyword:
            pattern = f"%{keyword}%"
            query = query.filter(or_(model.name.like(pattern), model.description.like(pattern)))
        for key, value in (data_filters or {}).items():
            if value is None or value == "":
                continue
            if key == "source_id":
                query = query.filter(model.source_id == int(value))
            elif key == "status":
                query = query.filter(model.status == str(value))
            else:
                query = query.filter(self._json_value_filter(model.data_json[key], value))
        total = query.count()
        rows = (
            query.order_by(model.updated_at.desc(), model.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return [self._test_case_to_dict(table, row) for row in rows], total

    def _get_test_case(self, table: str, item_id: int) -> dict[str, Any] | None:
        model, _ = TEST_CASE_RECORDS[table]
        row = self.db.query(model).filter(model.id == item_id, model.deleted.is_(False)).first()
        return self._test_case_to_dict(table, row) if row else None

    def _create_test_case(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        model, case_type = TEST_CASE_RECORDS[table]
        payload = dict(data)
        data_json = self._clean_case_data(payload.get("data") or {})
        data_json["case_type"] = case_type
        row = model(
            name=str(payload.get("name") or "Untitled"),
            project_id=payload.get("project_id"),
            source_id=payload.get("source_id"),
            description=payload.get("description"),
            status=str(payload.get("status") or "active"),
            data_json=data_json,
            steps_json=self._list_payload(payload.get("steps") or data_json.get("steps")),
            assertions_json=self._list_payload(payload.get("assertions") or data_json.get("assertions")),
            strategy_ids_json=self._int_list_payload(payload.get("strategy_ids") or data_json.get("strategy_ids")),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._test_case_to_dict(table, row)

    def _update_test_case(self, table: str, item_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        model, case_type = TEST_CASE_RECORDS[table]
        row = self.db.query(model).filter(model.id == item_id, model.deleted.is_(False)).first()
        if not row:
            return None
        payload = {key: value for key, value in data.items() if value is not None}
        if "name" in payload:
            row.name = str(payload["name"])
        if "project_id" in payload:
            row.project_id = payload["project_id"]
        if "source_id" in payload:
            row.source_id = payload["source_id"]
        if "description" in payload:
            row.description = payload["description"]
        if "status" in payload:
            row.status = str(payload["status"])
        if "data" in payload:
            data_json = self._clean_case_data(payload["data"] or {})
            data_json["case_type"] = case_type
            row.data_json = data_json
        if "steps" in payload:
            row.steps_json = self._list_payload(payload["steps"])
        if "assertions" in payload:
            row.assertions_json = self._list_payload(payload["assertions"])
        if "strategy_ids" in payload:
            row.strategy_ids_json = self._int_list_payload(payload["strategy_ids"])
        self.db.commit()
        self.db.refresh(row)
        return self._test_case_to_dict(table, row)

    def _delete_test_case(self, table: str, item_id: int) -> bool:
        model, _ = TEST_CASE_RECORDS[table]
        row = self.db.query(model).filter(model.id == item_id, model.deleted.is_(False)).first()
        if not row:
            return False
        row.deleted = True
        self.db.commit()
        return True

    def _test_case_to_dict(self, table: str, row: Any) -> dict[str, Any]:
        _, case_type = TEST_CASE_RECORDS[table]
        data = self._clean_case_data(row.data_json or {})
        data["case_type"] = case_type
        strategy_ids = self._int_list_payload(getattr(row, "strategy_ids_json", []) or [])
        return {
            "id": row.id,
            "name": row.name,
            "project_id": row.project_id,
            "source_id": row.source_id,
            "description": row.description,
            "status": row.status,
            "case_type": case_type,
            "data": data,
            "steps": self._list_payload(row.steps_json),
            "assertions": self._list_payload(row.assertions_json),
            "strategy_ids": strategy_ids,
            "created_at": self._format_time(row.created_at),
            "updated_at": self._format_time(row.updated_at),
            "deleted": row.deleted,
        }

    def _list_payload(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    def _int_list_payload(self, value: Any) -> list[int]:
        if not isinstance(value, list):
            return []
        result: list[int] = []
        for item in value:
            try:
                result.append(int(item))
            except (TypeError, ValueError):
                continue
        return result

    def _clean_case_data(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        return {
            key: item
            for key, item in value.items()
            if key not in {"assertions", "strategies", "strategy", "strategy_ids"}
        }
