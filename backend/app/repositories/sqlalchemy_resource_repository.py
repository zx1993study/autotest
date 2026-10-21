from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Integer, and_, cast, or_
from sqlalchemy import update as sql_update
from sqlalchemy.orm import Session, aliased

from app.models.resource_record import ResourceRecord
from app.models.test_case_record import (
    ApiTestCaseRecord,
    AppTestCaseRecord,
    MiniappTestCaseRecord,
    WebTestCaseRecord,
)
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

ID_DESC_RESOURCE_TABLES = {
    "execution_flows",
    "api_flow_scenarios",
    "api_flow_runs",
    "api_interfaces",
    "api_fields",
    "case_drafts",
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
        if keyword and table == "system_users":
            from app.repositories.sqlalchemy_user_filters import user_keyword_filter

            query = query.filter(user_keyword_filter(keyword))
        elif keyword:
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
            if key == "device_id" and table in {"app_features", "app_feature_scenarios"}:
                from app.repositories.sqlalchemy_feature_filters import (
                    app_device_filter,
                )

                query = query.filter(app_device_filter(self.db, table, int(value)))
                continue
            if key == "script_status" and table == "web_pages":
                from app.repositories.sqlalchemy_feature_filters import (
                    web_script_status,
                )

                query = query.filter(web_script_status(self.db) == value)
                continue
            if table == "case_drafts" and key == "source_id":
                query = query.filter(self._json_value_filter(ResourceRecord.data_json[key], value))
                continue
            if key in {"path", "api_path"}:
                query = query.filter(ResourceRecord.data_json["data"][key].as_string().like(f"%{value}%"))
                continue
            if key == "module" and value == "__ungrouped__":
                module_value = ResourceRecord.data_json["data"]["module"].as_string()
                query = query.filter(or_(module_value.is_(None), module_value == ""))
                continue
            query = query.filter(self._json_value_filter(ResourceRecord.data_json["data"][key], value))
        id_query = query.with_entities(ResourceRecord.id)
        total = id_query.count()
        if table == "web_elements":
            order_by = (ResourceRecord.id.asc(),)
        elif table in ID_DESC_RESOURCE_TABLES:
            order_by = (ResourceRecord.id.desc(),)
        else:
            order_by = (ResourceRecord.updated_at.desc(), ResourceRecord.id.desc())
        # DISTINCT prevents MySQL from merging JSON filters back into the sorted query.
        matching_ids = id_query.distinct().subquery("matching_resources")
        page_query = self.db.query(ResourceRecord.id).join(
            matching_ids, ResourceRecord.id == matching_ids.c.id,
        )
        page_ids = [row.id for row in (
            page_query.order_by(*order_by)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )]
        if not page_ids:
            return [], total
        rows = query.filter(ResourceRecord.id.in_(page_ids)).all()
        rows_by_id = {row.id: row for row in rows}
        return [self._to_dict(rows_by_id[item_id]) for item_id in page_ids if item_id in rows_by_id], total

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

    def get_many(self, table: str, item_ids: list[int]) -> list[dict[str, Any]]:
        if not item_ids:
            return []
        if table in TEST_CASE_RECORDS:
            model, _ = TEST_CASE_RECORDS[table]
            rows = self.db.query(model).filter(model.id.in_(set(item_ids)), model.deleted.is_(False)).all()
            return [self._test_case_to_dict(table, row) for row in rows]
        rows = self.db.query(ResourceRecord).filter(
            ResourceRecord.table_name == table, ResourceRecord.deleted.is_(False),
            ResourceRecord.id.in_(set(item_ids)),
        ).all()
        return [self._to_dict(row) for row in rows]

    def latest_execution_records(self, case_type: str, case_ids: list[int], project_id: int | None = None) -> list[dict[str, Any]]:
        if not case_ids:
            return []
        record = ResourceRecord
        newer = aliased(ResourceRecord)
        case_id = cast(record.data_json["data"]["case_id"].as_string(), Integer)
        newer_case_id = cast(newer.data_json["data"]["case_id"].as_string(), Integer)
        has_newer = self.db.query(newer.id).filter(
            newer.table_name == "execution_records", newer.deleted.is_(False),
            newer.data_json["data"]["case_type"].as_string() == case_type,
            newer_case_id == case_id,
            newer.project_id.is_not_distinct_from(record.project_id),
            or_(newer.created_at > record.created_at, and_(newer.created_at == record.created_at, newer.id > record.id)),
        ).correlate(record).exists()
        query = self.db.query(record).filter(
            record.table_name == "execution_records", record.deleted.is_(False),
            record.data_json["data"]["case_type"].as_string() == case_type,
            case_id.in_(case_ids), ~has_newer,
        )
        if project_id is not None:
            query = query.filter(record.project_id == project_id)
        return [self._to_dict(row) for row in query.all()]

    def execution_flow_summaries(self, flow_ids):
        from app.repositories.sqlalchemy_execution_flow_summary import (
            execution_flow_summaries,
        )

        return execution_flow_summaries(self.db, flow_ids)

    def api_report_rows(self, query):
        from app.repositories.sqlalchemy_api_report import list_api_reports

        return list_api_reports(self.db, query)

    def app_feature_summaries(self, feature_ids):
        from app.repositories.sqlalchemy_feature_summary import app_feature_summaries

        return app_feature_summaries(self.db, feature_ids)

    def web_feature_counts(self, feature_ids):
        from app.repositories.sqlalchemy_feature_summary import web_feature_counts

        return web_feature_counts(self.db, feature_ids)

    def web_execution_snapshots(self, query):
        from app.repositories.sqlalchemy_web_execution_summary import web_execution_snapshots

        return web_execution_snapshots(self.db, query)

    def report_statistics(self, project_id, start, end):
        from app.repositories.sqlalchemy_report_statistics import report_statistics

        return report_statistics(self.db, project_id, start, end)

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

    def update_if_status(self, table: str, item_id: int, expected: str, data: dict[str, Any]) -> dict[str, Any] | None:
        current = self.get(table, item_id)
        if current is None:
            return None
        extra = {key: value for key, value in current.items() if key not in COLUMN_KEYS}
        extra.update(self._extra_payload(data))
        statement = sql_update(ResourceRecord).where(
            ResourceRecord.table_name == table, ResourceRecord.id == item_id,
            ResourceRecord.status == expected, ResourceRecord.deleted.is_(False),
        ).values(status=str(data.get("status") or expected), data_json=extra)
        changed = self.db.execute(statement, execution_options={"synchronize_session": False}).rowcount
        self.db.commit()
        self.db.expire_all()
        return self.get(table, item_id) if changed else None

    def patch_running_agent_task(self, task_id, node_key, patch, expected=None):
        try:
            row = self.db.query(ResourceRecord).filter(
                ResourceRecord.table_name == "agent_tasks", ResourceRecord.id == task_id,
                ResourceRecord.deleted.is_(False),
            ).populate_existing().with_for_update().first()
            extra = dict(row.data_json or {}) if row else {}
            current = extra.get("data") or {}
            if not row or row.status != "running" or current.get("claimed_by") != node_key:
                self.db.rollback()
                return None
            if expected is not None and any(current.get(key, {}) != value for key, value in expected.items()):
                self.db.rollback()
                return None
            extra["data"] = {**current, **patch}
            row.data_json = extra
            self.db.commit()
            self.db.refresh(row)
            return self._to_dict(row)
        except Exception:
            self.db.rollback()
            raise

    def resolve_app_connection(self, task_id, node_key, transition):
        from app.repositories.sqlalchemy_app_connection_repository import (
            resolve_app_connection,
        )

        return resolve_app_connection(self, task_id, node_key, transition)

    def complete_agent_task(self, task_id, node_key, status, data, records):
        try:
            row = self.db.query(ResourceRecord).filter(
                ResourceRecord.table_name == "agent_tasks", ResourceRecord.id == task_id,
                ResourceRecord.deleted.is_(False),
            ).populate_existing().with_for_update().first()
            if row is None:
                self.db.rollback()
                return None
            existing = dict(row.data_json or {})
            task_data = existing.get("data") or {}
            if task_data.get("claimed_by") != node_key:
                raise ValueError("Task belongs to another node")
            if row.status in {"success", "failed", "canceled"}:
                result = self._to_dict(row)
                self.db.rollback()
                return result
            if row.status != "running":
                raise ValueError("Task is not running")
            acquired = self.db.execute(sql_update(ResourceRecord).where(ResourceRecord.id == task_id, ResourceRecord.status == "running").values(status="reporting"), execution_options={"synchronize_session": False}).rowcount
            if not acquired:
                self.db.rollback()
                return self.get("agent_tasks", task_id)
            saved = []
            for record in records:
                item = ResourceRecord(table_name="execution_records", name=str(record.get("name") or "Agent execution"), project_id=record.get("project_id"), description=record.get("description"), status=str(record.get("status") or "failed"), data_json=self._extra_payload(record))
                self.db.add(item)
                saved.append(item)
            self.db.flush()
            existing["data"] = {**task_data, **data, "saved_records": [self._to_dict(item) for item in saved]}
            row.data_json = existing
            row.status = status
            row.description = str(data.get("error") or "")
            self.db.commit()
            self.db.refresh(row)
            return self._to_dict(row)
        except Exception:
            self.db.rollback()
            raise

    def update_many(
        self,
        table: str,
        rows: list[tuple[int, dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        if table in TEST_CASE_RECORDS:
            return [
                updated
                for item_id, data in rows
                if (updated := self._update_test_case(table, item_id, data)) is not None
            ]
        updates = {item_id: data for item_id, data in rows}
        if not updates:
            return []
        records = (
            self.db.query(ResourceRecord)
            .filter(
                ResourceRecord.table_name == table,
                ResourceRecord.id.in_(updates),
                ResourceRecord.deleted.is_(False),
            )
            .all()
        )
        records_by_id = {record.id: record for record in records}
        ordered_records = []
        for item_id, data in rows:
            record = records_by_id.get(item_id)
            if record is None:
                continue
            payload = {key: value for key, value in data.items() if value is not None}
            if "name" in payload:
                record.name = str(payload["name"])
            if "project_id" in payload:
                record.project_id = payload["project_id"]
            if "description" in payload:
                record.description = payload["description"]
            if "status" in payload:
                record.status = str(payload["status"])
            extra = dict(record.data_json or {})
            extra.update(self._extra_payload(payload))
            record.data_json = extra
            ordered_records.append(record)
        self.db.flush()
        result = [self._to_dict(record) for record in ordered_records]
        self.db.commit()
        return result

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
        from app.repositories.sqlalchemy_batch_deletion import soft_delete_ids

        if table in TEST_CASE_RECORDS:
            model, _ = TEST_CASE_RECORDS[table]
            return soft_delete_ids(self.db, model, ids)
        return soft_delete_ids(self.db, ResourceRecord, ids, (ResourceRecord.table_name == table,))

    def batch_delete_with_children(self, table, ids, child_table, parent_key):
        from app.repositories.sqlalchemy_batch_deletion import soft_delete_with_children

        return soft_delete_with_children(self.db, table, ids, child_table, parent_key)

    def get_related(self, table, parent_key, parent_ids, statuses=None):
        from app.repositories.sqlalchemy_batch_deletion import (
            id_batches,
            related_id_filter,
        )

        rows = []
        for batch in id_batches(parent_ids):
            query = self.db.query(ResourceRecord).filter(
                ResourceRecord.table_name == table, ResourceRecord.deleted.is_(False),
                related_id_filter(parent_key, batch),
            )
            if statuses is not None:
                query = query.filter(ResourceRecord.status.in_(statuses))
            rows.extend(self._to_dict(row) for row in query.all())
        return rows

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
            query.order_by(model.id.desc())
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
