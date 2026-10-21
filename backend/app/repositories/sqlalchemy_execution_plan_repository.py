from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.execution_plan import (
    ExecutionPlan,
    ExecutionPlanCase,
    ExecutionPlanRun,
    ExecutionPlanRunItem,
)
from app.models.resource_record import ResourceRecord
from app.models.test_case_record import (
    ApiTestCaseRecord,
    AppTestCaseRecord,
    WebTestCaseRecord,
)
from app.repositories.interfaces import ExecutionPlanRepository

CASE_MODELS = {
    "API": ApiTestCaseRecord,
    "WEB": WebTestCaseRecord,
    "APP": AppTestCaseRecord,
}

FEATURE_TABLES = {
    "API": "api_interfaces",
    "WEB": "web_pages",
    "APP": "app_features",
}
PLAN_FEATURE_SELECTED_FLAG = "plan_feature_selected"
GENERATED_PLAN_ID_KEY = "generated_plan_id"


class SqlAlchemyExecutionPlanRepository(ExecutionPlanRepository):
    """SQLAlchemy implementation for execution plan persistence."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        *,
        keyword: str | None,
        project_id: int | None,
        test_type: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[ExecutionPlan], int]:
        query = self.db.query(ExecutionPlan).filter(ExecutionPlan.deleted.is_(False))
        if project_id is not None:
            query = query.filter(ExecutionPlan.project_id == project_id)
        if test_type:
            query = query.filter(ExecutionPlan.test_type == test_type)
        if status:
            query = query.filter(ExecutionPlan.status == status)
        if keyword:
            pattern = f"%{keyword}%"
            query = query.filter(or_(ExecutionPlan.name.like(pattern), ExecutionPlan.description.like(pattern)))
        total = query.count()
        rows = (
            query.order_by(ExecutionPlan.updated_at.desc(), ExecutionPlan.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    def get(self, plan_id: int) -> ExecutionPlan | None:
        return (
            self.db.query(ExecutionPlan)
            .filter(ExecutionPlan.id == plan_id, ExecutionPlan.deleted.is_(False))
            .first()
        )

    def create(self, data: dict[str, object]) -> ExecutionPlan:
        row = ExecutionPlan(
            name=str(data["name"]),
            project_id=self._optional_int(data.get("project_id")),
            test_rounds=int(data["test_rounds"]),
            test_type=str(data["test_type"]),
            description=self._optional_text(data.get("description")),
            requirement_title=self._optional_text(data.get("requirement_title")),
            requirement_document=self._optional_text(data.get("requirement_document")),
            generation_json=self._dict_value(data.get("generation_json")),
            api_ids_json=self._int_list(data.get("api_ids_json")),
            web_feature_ids_json=self._int_list(data.get("web_feature_ids_json")),
            status=str(data.get("status") or "active"),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update(self, plan_id: int, data: dict[str, object]) -> ExecutionPlan | None:
        row = self.get(plan_id)
        if row is None:
            return None
        if "name" in data and data["name"] is not None:
            row.name = str(data["name"])
        if "project_id" in data:
            row.project_id = self._optional_int(data["project_id"])
        if "test_rounds" in data and data["test_rounds"] is not None:
            row.test_rounds = int(data["test_rounds"])
        if "test_type" in data and data["test_type"] is not None:
            row.test_type = str(data["test_type"])
        if "description" in data:
            row.description = self._optional_text(data["description"])
        if "requirement_title" in data:
            row.requirement_title = self._optional_text(data["requirement_title"])
        if "requirement_document" in data:
            row.requirement_document = self._optional_text(
                data["requirement_document"]
            )
        if "generation_json" in data:
            row.generation_json = self._dict_value(data["generation_json"])
        if "api_ids_json" in data:
            row.api_ids_json = self._int_list(data["api_ids_json"])
        if "web_feature_ids_json" in data:
            row.web_feature_ids_json = self._int_list(data["web_feature_ids_json"])
        if "status" in data and data["status"] is not None:
            row.status = str(data["status"])
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete(self, plan_id: int) -> bool:
        row = self.get(plan_id)
        if row is None:
            return False
        row.deleted = True
        self.db.commit()
        return True

    def batch_delete(self, plan_ids: list[int]) -> int:
        from app.repositories.sqlalchemy_batch_deletion import soft_delete_ids

        return soft_delete_ids(self.db, ExecutionPlan, plan_ids)

    def list_test_cases(self, case_type: str, project_id: int | None) -> list[object]:
        model = CASE_MODELS[case_type]
        query = self.db.query(model).filter(model.deleted.is_(False), model.status == "active")
        if project_id is not None:
            query = query.filter(model.project_id == project_id)
        return query.order_by(model.source_id.asc(), model.id.asc()).all()

    def feature_names(self, case_type: str, feature_ids: set[int]) -> dict[int, str]:
        table_name = FEATURE_TABLES[case_type]
        if not feature_ids:
            return {}
        rows = (
            self.db.query(ResourceRecord.id, ResourceRecord.name)
            .filter(
                ResourceRecord.table_name == table_name,
                ResourceRecord.id.in_(feature_ids),
                ResourceRecord.deleted.is_(False),
            )
            .all()
        )
        return {int(row.id): str(row.name or "") for row in rows}

    def create_plan_cases(self, rows: list[dict[str, object]]) -> list[ExecutionPlanCase]:
        records = [
            ExecutionPlanCase(
                plan_id=int(row["plan_id"]),
                case_type=str(row["case_type"]),
                feature_id=self._optional_int(row.get("feature_id")),
                feature_name=str(row.get("feature_name") or "-"),
                case_id=int(row["case_id"]),
                case_name=str(row.get("case_name") or "-"),
                case_version=self._optional_text(row.get("case_version")),
                snapshot_json=self._dict_value(row.get("snapshot_json")),
                sort_order=int(row.get("sort_order") or 0),
            )
            for row in rows
        ]
        if not records:
            return []
        self.db.add_all(records)
        self.db.commit()
        for record in records:
            self.db.refresh(record)
        return records

    def mark_plan_feature_cases_selected(self, plan_id: int, case_type: str, feature_ids: set[int]) -> int:
        """Mark existing snapshot rows as explicitly selected by the plan detail.

        Old plans may already contain auto-generated full snapshots. When the
        user adds a feature now, we mark only that feature's rows instead of
        creating duplicates, so detail rendering can ignore legacy full rows.
        """

        if not feature_ids:
            return 0
        rows = (
            self.db.query(ExecutionPlanCase)
            .filter(
                ExecutionPlanCase.plan_id == plan_id,
                ExecutionPlanCase.case_type == case_type,
                ExecutionPlanCase.feature_id.in_(feature_ids),
                ExecutionPlanCase.deleted.is_(False),
            )
            .all()
        )
        changed_count = 0
        for row in rows:
            snapshot = self._dict_value(row.snapshot_json)
            if snapshot.get(PLAN_FEATURE_SELECTED_FLAG) is True:
                continue
            row.snapshot_json = {**snapshot, PLAN_FEATURE_SELECTED_FLAG: True}
            changed_count += 1
        if changed_count:
            self.db.commit()
        return changed_count

    def replace_plan_feature_selection(
        self,
        plan_id: int,
        case_type: str,
        feature_ids: set[int],
    ) -> int:
        """Synchronize active snapshot visibility with the configured sources."""

        rows = (
            self.db.query(ExecutionPlanCase)
            .filter(
                ExecutionPlanCase.plan_id == plan_id,
                ExecutionPlanCase.case_type == case_type,
                ExecutionPlanCase.deleted.is_(False),
            )
            .all()
        )
        changed_count = 0
        for row in rows:
            selected = row.feature_id in feature_ids
            snapshot = self._dict_value(row.snapshot_json)
            if snapshot.get(PLAN_FEATURE_SELECTED_FLAG) is selected:
                continue
            row.snapshot_json = {**snapshot, PLAN_FEATURE_SELECTED_FLAG: selected}
            changed_count += 1
        if changed_count:
            self.db.commit()
        return changed_count

    def delete_generated_plan_cases(self, plan_id: int) -> int:
        """Soft-delete only snapshots generated for this plan."""

        rows = self.list_plan_cases(plan_id)
        deleted_count = 0
        for row in rows:
            snapshot = self._dict_value(row.snapshot_json)
            data = self._dict_value(snapshot.get("data"))
            if self._optional_int(data.get(GENERATED_PLAN_ID_KEY)) != plan_id:
                continue
            row.deleted = True
            deleted_count += 1
        if deleted_count:
            self.db.commit()
        return deleted_count

    def list_plan_cases(self, plan_id: int) -> list[ExecutionPlanCase]:
        return (
            self.db.query(ExecutionPlanCase)
            .filter(ExecutionPlanCase.plan_id == plan_id, ExecutionPlanCase.deleted.is_(False))
            .order_by(
                ExecutionPlanCase.case_type.asc(),
                ExecutionPlanCase.sort_order.asc(),
                ExecutionPlanCase.id.asc(),
            )
            .all()
        )

    def delete_plan_cases(self, plan_id: int) -> int:
        count = (
            self.db.query(ExecutionPlanCase)
            .filter(ExecutionPlanCase.plan_id == plan_id, ExecutionPlanCase.deleted.is_(False))
            .update({ExecutionPlanCase.deleted: True}, synchronize_session=False)
        )
        self.db.commit()
        return int(count)

    def list_runs(self, plan_id: int) -> list[ExecutionPlanRun]:
        return (
            self.db.query(ExecutionPlanRun)
            .filter(ExecutionPlanRun.plan_id == plan_id)
            .order_by(ExecutionPlanRun.round_no.desc(), ExecutionPlanRun.id.desc())
            .all()
        )

    def latest_run(self, plan_id: int) -> ExecutionPlanRun | None:
        return (
            self.db.query(ExecutionPlanRun)
            .filter(ExecutionPlanRun.plan_id == plan_id)
            .order_by(ExecutionPlanRun.round_no.desc(), ExecutionPlanRun.id.desc())
            .first()
        )

    def list_run_items(self, run_id: int) -> list[ExecutionPlanRunItem]:
        return (
            self.db.query(ExecutionPlanRunItem)
            .filter(ExecutionPlanRunItem.run_id == run_id)
            .order_by(ExecutionPlanRunItem.id.asc())
            .all()
        )

    def create_run(self, data: dict[str, object]) -> ExecutionPlanRun:
        row = ExecutionPlanRun(
            plan_id=int(data["plan_id"]),
            round_no=int(data["round_no"]),
            status=str(data.get("status") or "queued"),
            total_count=int(data.get("total_count") or 0),
            success_count=int(data.get("success_count") or 0),
            failed_count=int(data.get("failed_count") or 0),
            pass_rate=float(data.get("pass_rate") or 0.0),
            started_at=self._optional_datetime(data.get("started_at")),
            ended_at=self._optional_datetime(data.get("ended_at")),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_run(self, run_id: int, data: dict[str, object]) -> ExecutionPlanRun | None:
        row = self.db.query(ExecutionPlanRun).filter(ExecutionPlanRun.id == run_id).first()
        if row is None:
            return None
        if "status" in data and data["status"] is not None:
            row.status = str(data["status"])
        if "total_count" in data and data["total_count"] is not None:
            row.total_count = int(data["total_count"])
        if "success_count" in data and data["success_count"] is not None:
            row.success_count = int(data["success_count"])
        if "failed_count" in data and data["failed_count"] is not None:
            row.failed_count = int(data["failed_count"])
        if "pass_rate" in data and data["pass_rate"] is not None:
            row.pass_rate = float(data["pass_rate"])
        if "started_at" in data:
            row.started_at = self._optional_datetime(data["started_at"])
        if "ended_at" in data:
            row.ended_at = self._optional_datetime(data["ended_at"])
        self.db.commit()
        self.db.refresh(row)
        return row

    def create_run_items(self, rows: list[dict[str, object]]) -> list[ExecutionPlanRunItem]:
        records = [
            ExecutionPlanRunItem(
                run_id=int(row["run_id"]),
                plan_case_id=int(row["plan_case_id"]),
                case_type=str(row["case_type"]),
                case_id=int(row["case_id"]),
                status=str(row.get("status") or "queued"),
                duration_ms=self._optional_int(row.get("duration_ms")),
                error_message=self._optional_text(row.get("error_message")),
                report_record_id=self._optional_int(row.get("report_record_id")),
                artifact_json=self._dict_value(row.get("artifact_json")),
                executed_at=self._optional_datetime(row.get("executed_at")),
            )
            for row in rows
        ]
        if not records:
            return []
        self.db.add_all(records)
        self.db.commit()
        for record in records:
            self.db.refresh(record)
        return records

    def _optional_int(self, value: object) -> int | None:
        if value is None or value == "":
            return None
        return int(value)

    def _optional_text(self, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _dict_value(self, value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {}

    def _int_list(self, value: object) -> list[int]:
        if not isinstance(value, list):
            return []
        result: list[int] = []
        for item in value:
            parsed = self._optional_int(item)
            if parsed is not None and parsed not in result:
                result.append(parsed)
        return result

    def _optional_datetime(self, value: object) -> datetime | None:
        return value if isinstance(value, datetime) else None
