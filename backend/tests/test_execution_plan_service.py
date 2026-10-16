from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import unittest

from app.enums.business import ExecutionPlanStatusEnum, ExecutionPlanTestTypeEnum
from app.models.execution_plan import ExecutionPlan, ExecutionPlanCase, ExecutionPlanRun, ExecutionPlanRunItem
from app.schemas.execution import (
    ExecutionPlanCreate,
    ExecutionPlanFeatureAddRequest,
    ExecutionPlanManualFeatureCreate,
    ExecutionPlanRunRequest,
    ExecutionPlanUpdate,
)
from app.services.execution_plan_run_service import ExecutionPlanRunService
from app.services.execution_plan_service import ExecutionPlanService


@dataclass
class FakeCase:
    id: int
    name: str
    project_id: int
    source_id: int
    description: str = ""
    status: str = "active"
    data_json: dict[str, object] = field(default_factory=dict)
    steps_json: list[dict[str, object]] = field(default_factory=list)
    assertions_json: list[dict[str, object]] = field(default_factory=list)
    strategy_ids_json: list[int] = field(default_factory=list)
    updated_at: datetime = datetime(2026, 7, 17, 9, 0, 0)


class FakeExecutionPlanRepository:
    """In-memory repository for execution plan service tests."""

    def __init__(self) -> None:
        self.rows: dict[int, ExecutionPlan] = {}
        self.plan_cases: dict[int, ExecutionPlanCase] = {}
        self.runs: dict[int, ExecutionPlanRun] = {}
        self.run_items: dict[int, ExecutionPlanRunItem] = {}
        self.test_cases: dict[str, list[FakeCase]] = {"WEB": [], "API": [], "APP": []}
        self.feature_map: dict[tuple[str, int], str] = {}
        self.next_id = 1
        self.next_plan_case_id = 1
        self.next_run_id = 1
        self.next_run_item_id = 1

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
        del keyword, project_id, test_type, status
        rows = list(self.rows.values())
        start = (page - 1) * page_size
        return rows[start : start + page_size], len(rows)

    def get(self, plan_id: int) -> ExecutionPlan | None:
        row = self.rows.get(plan_id)
        return row if row and not row.deleted else None

    def create(self, data: dict[str, object]) -> ExecutionPlan:
        now = datetime(2026, 7, 17, 10, 0, 0)
        row = ExecutionPlan(
            id=self.next_id,
            name=str(data["name"]),
            project_id=data.get("project_id"),
            test_rounds=int(data["test_rounds"]),
            test_type=str(data["test_type"]),
            description=data.get("description"),
            status=str(data.get("status") or ExecutionPlanStatusEnum.ACTIVE.code),
            deleted=False,
            created_at=now,
            updated_at=now,
        )
        self.rows[self.next_id] = row
        self.next_id += 1
        return row

    def update(self, plan_id: int, data: dict[str, object]) -> ExecutionPlan | None:
        row = self.get(plan_id)
        if row is None:
            return None
        for key, value in data.items():
            setattr(row, key, value)
        row.updated_at = datetime(2026, 7, 17, 11, 0, 0)
        return row

    def delete(self, plan_id: int) -> bool:
        row = self.get(plan_id)
        if row is None:
            return False
        row.deleted = True
        return True

    def batch_delete(self, plan_ids: list[int]) -> int:
        return sum(1 for plan_id in set(plan_ids) if self.delete(plan_id))

    def list_test_cases(self, case_type: str, project_id: int | None) -> list[object]:
        rows = self.test_cases.get(case_type, [])
        return [row for row in rows if project_id is None or row.project_id == project_id]

    def feature_names(self, case_type: str, feature_ids: set[int]) -> dict[int, str]:
        return {
            feature_id: self.feature_map.get((case_type, feature_id), "")
            for feature_id in feature_ids
        }

    def create_plan_cases(self, rows: list[dict[str, object]]) -> list[ExecutionPlanCase]:
        result: list[ExecutionPlanCase] = []
        now = datetime(2026, 7, 17, 10, 0, 0)
        for row in rows:
            item = ExecutionPlanCase(
                id=self.next_plan_case_id,
                plan_id=int(row["plan_id"]),
                case_type=str(row["case_type"]),
                feature_id=row.get("feature_id"),
                feature_name=str(row.get("feature_name") or "-"),
                case_id=int(row["case_id"]),
                case_name=str(row.get("case_name") or "-"),
                case_version=row.get("case_version"),
                snapshot_json=row.get("snapshot_json") if isinstance(row.get("snapshot_json"), dict) else {},
                sort_order=int(row.get("sort_order") or 0),
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            self.plan_cases[item.id] = item
            self.next_plan_case_id += 1
            result.append(item)
        return result

    def mark_plan_feature_cases_selected(self, plan_id: int, case_type: str, feature_ids: set[int]) -> int:
        count = 0
        for item in self.plan_cases.values():
            if item.plan_id != plan_id or item.case_type != case_type or item.feature_id not in feature_ids or item.deleted:
                continue
            if item.snapshot_json.get("plan_feature_selected") is True:
                continue
            item.snapshot_json = {**item.snapshot_json, "plan_feature_selected": True}
            count += 1
        return count

    def list_plan_cases(self, plan_id: int) -> list[ExecutionPlanCase]:
        return [
            item
            for item in sorted(self.plan_cases.values(), key=lambda row: (row.case_type, row.sort_order, row.id))
            if item.plan_id == plan_id and not item.deleted
        ]

    def delete_plan_cases(self, plan_id: int) -> int:
        count = 0
        for item in self.plan_cases.values():
            if item.plan_id == plan_id and not item.deleted:
                item.deleted = True
                count += 1
        return count

    def list_runs(self, plan_id: int) -> list[ExecutionPlanRun]:
        return [
            item
            for item in sorted(self.runs.values(), key=lambda row: (row.round_no, row.id), reverse=True)
            if item.plan_id == plan_id
        ]

    def latest_run(self, plan_id: int) -> ExecutionPlanRun | None:
        rows = self.list_runs(plan_id)
        return rows[0] if rows else None

    def list_run_items(self, run_id: int) -> list[ExecutionPlanRunItem]:
        return [
            item
            for item in sorted(self.run_items.values(), key=lambda row: row.id)
            if item.run_id == run_id
        ]

    def create_run(self, data: dict[str, object]) -> ExecutionPlanRun:
        now = datetime(2026, 7, 17, 12, 0, 0)
        row = ExecutionPlanRun(
            id=self.next_run_id,
            plan_id=int(data["plan_id"]),
            round_no=int(data["round_no"]),
            status=str(data.get("status") or "queued"),
            total_count=int(data.get("total_count") or 0),
            success_count=int(data.get("success_count") or 0),
            failed_count=int(data.get("failed_count") or 0),
            pass_rate=float(data.get("pass_rate") or 0.0),
            started_at=data.get("started_at") if isinstance(data.get("started_at"), datetime) else None,
            ended_at=data.get("ended_at") if isinstance(data.get("ended_at"), datetime) else None,
            created_at=now,
            updated_at=now,
        )
        self.runs[row.id] = row
        self.next_run_id += 1
        return row

    def update_run(self, run_id: int, data: dict[str, object]) -> ExecutionPlanRun | None:
        row = self.runs.get(run_id)
        if row is None:
            return None
        for key, value in data.items():
            setattr(row, key, value)
        row.updated_at = datetime(2026, 7, 17, 12, 1, 0)
        return row

    def create_run_items(self, rows: list[dict[str, object]]) -> list[ExecutionPlanRunItem]:
        result: list[ExecutionPlanRunItem] = []
        now = datetime(2026, 7, 17, 12, 1, 0)
        for row in rows:
            item = ExecutionPlanRunItem(
                id=self.next_run_item_id,
                run_id=int(row["run_id"]),
                plan_case_id=int(row["plan_case_id"]),
                case_type=str(row["case_type"]),
                case_id=int(row["case_id"]),
                status=str(row.get("status") or "queued"),
                duration_ms=row.get("duration_ms") if isinstance(row.get("duration_ms"), int) else None,
                error_message=row.get("error_message") if isinstance(row.get("error_message"), str) else None,
                report_record_id=row.get("report_record_id") if isinstance(row.get("report_record_id"), int) else None,
                artifact_json=row.get("artifact_json") if isinstance(row.get("artifact_json"), dict) else {},
                executed_at=row.get("executed_at") if isinstance(row.get("executed_at"), datetime) else None,
                created_at=now,
            )
            self.run_items[item.id] = item
            self.next_run_item_id += 1
            result.append(item)
        return result


class FakeDispatcher:
    """Return successful execution records without invoking browser or HTTP clients."""

    def execute(self, case_type: str, payload: dict[str, object]) -> dict[str, object]:
        records = []
        for case_id in payload.get("case_ids", []):
            records.append(
                {
                    "id": int(case_id) + 100,
                    "name": f"{case_type} record",
                    "status": "success",
                    "description": "执行通过",
                    "data": {
                        "case_id": int(case_id),
                        "case_type": case_type,
                        "duration_ms": 128,
                        "mode": payload.get("mode"),
                    },
                }
            )
        return {
            "total": len(records),
            "success_count": len(records),
            "failed_count": 0,
            "queued_count": 0,
            "records": records,
        }


class ExecutionPlanServiceTest(unittest.TestCase):
    def test_create_complete_and_copy_plan(self) -> None:
        repository = FakeExecutionPlanRepository()
        service = ExecutionPlanService(repository)

        created = service.create(
            ExecutionPlanCreate(
                name="仓库查询",
                test_rounds=2,
                test_type=ExecutionPlanTestTypeEnum.WEB,
            )
        )
        completed = service.complete(created.id)
        copied = service.copy(created.id)

        self.assertEqual(created.test_type, ExecutionPlanTestTypeEnum.WEB.code)
        self.assertEqual(completed.status, ExecutionPlanStatusEnum.DONE.code)
        self.assertEqual(copied.status, ExecutionPlanStatusEnum.ACTIVE.code)
        self.assertEqual(copied.test_rounds, 2)
        self.assertTrue(copied.name.endswith(" - 副本"))

    def test_update_ignores_hidden_empty_project_and_description(self) -> None:
        repository = FakeExecutionPlanRepository()
        service = ExecutionPlanService(repository)
        created = service.create(
            ExecutionPlanCreate(
                name="仓库查询",
                project_id=8,
                test_rounds=2,
                test_type=ExecutionPlanTestTypeEnum.WEB,
                description="保留备注",
            )
        )

        updated = service.update(
            created.id,
            ExecutionPlanUpdate(
                name="仓库新增",
                project_id=None,
                test_rounds=3,
                test_type=ExecutionPlanTestTypeEnum.WEB,
                description=None,
            ),
        )

        self.assertEqual(updated.project_id, 8)
        self.assertEqual(updated.description, "保留备注")
        self.assertEqual(updated.test_rounds, 3)

    def test_created_all_plan_starts_without_case_snapshots(self) -> None:
        repository = FakeExecutionPlanRepository()
        repository.test_cases["WEB"].append(FakeCase(id=1, name="Web 查询", project_id=8, source_id=11))
        repository.test_cases["API"].append(FakeCase(id=2, name="API 查询", project_id=8, source_id=12))
        repository.test_cases["APP"].append(FakeCase(id=3, name="App 查询", project_id=8, source_id=13))
        service = ExecutionPlanService(repository)

        created = service.create(
            ExecutionPlanCreate(
                name="仓库全链路",
                project_id=8,
                test_rounds=1,
                test_type=ExecutionPlanTestTypeEnum.ALL,
            )
        )
        detail = service.detail(created.id)

        self.assertEqual(detail.summary.case_count, 0)
        self.assertEqual(detail.summary.feature_count, 0)
        self.assertEqual([group.case_type for group in detail.groups], ["WEB", "API", "APP"])
        self.assertTrue(all(not group.features for group in detail.groups))

    def test_legacy_full_snapshots_are_hidden_until_feature_is_added(self) -> None:
        repository = FakeExecutionPlanRepository()
        service = ExecutionPlanService(repository)
        created = service.create(
            ExecutionPlanCreate(
                name="仓库页面测试",
                project_id=8,
                test_rounds=1,
                test_type=ExecutionPlanTestTypeEnum.WEB,
            )
        )
        repository.create_plan_cases(
            [
                {
                    "plan_id": created.id,
                    "case_type": "WEB",
                    "feature_id": 11,
                    "feature_name": "仓库查询",
                    "case_id": 101,
                    "case_name": "查询用例",
                    "snapshot_json": {"case_type": "WEB", "source_id": 11},
                    "sort_order": 1,
                },
                {
                    "plan_id": created.id,
                    "case_type": "WEB",
                    "feature_id": 12,
                    "feature_name": "仓库新增",
                    "case_id": 102,
                    "case_name": "新增用例",
                    "snapshot_json": {"case_type": "WEB", "source_id": 12},
                    "sort_order": 2,
                },
            ]
        )

        empty_detail = service.detail(created.id)
        selected_detail = service.add_features(
            created.id,
            ExecutionPlanFeatureAddRequest(case_type="WEB", feature_ids=[11]),
        )

        self.assertEqual(empty_detail.summary.case_count, 0)
        self.assertEqual(selected_detail.summary.case_count, 1)
        self.assertEqual(selected_detail.groups[0].features[0].feature_id, 11)
        self.assertEqual(selected_detail.groups[0].features[0].cases[0].case_snapshot.case_id, 101)

    def test_add_api_features_snapshots_related_cases_once(self) -> None:
        repository = FakeExecutionPlanRepository()
        service = ExecutionPlanService(repository)
        created = service.create(
            ExecutionPlanCreate(
                name="仓库接口测试",
                project_id=8,
                test_rounds=1,
                test_type=ExecutionPlanTestTypeEnum.API,
            )
        )
        repository.test_cases["API"].append(FakeCase(id=21, name="API 查询", project_id=8, source_id=120))
        repository.test_cases["API"].append(FakeCase(id=22, name="API 新增", project_id=8, source_id=121))
        repository.feature_map[("API", 120)] = "仓库查询接口"

        first_detail = service.add_features(
            created.id,
            ExecutionPlanFeatureAddRequest(case_type="API", feature_ids=[120]),
        )
        second_detail = service.add_features(
            created.id,
            ExecutionPlanFeatureAddRequest(case_type="API", feature_ids=[120]),
        )

        self.assertEqual(first_detail.summary.case_count, 1)
        self.assertEqual(second_detail.summary.case_count, 1)
        self.assertEqual(second_detail.groups[0].features[0].feature_name, "仓库查询接口")
        self.assertEqual(second_detail.groups[0].features[0].cases[0].case_snapshot.case_id, 21)

    def test_run_plan_persists_run_and_run_items(self) -> None:
        repository = FakeExecutionPlanRepository()
        repository.test_cases["WEB"].append(FakeCase(id=10, name="Web 查询", project_id=8, source_id=11))
        repository.feature_map[("WEB", 11)] = "仓库页面"
        plan_service = ExecutionPlanService(repository)
        run_service = ExecutionPlanRunService(repository, repository, FakeDispatcher())
        created = plan_service.create(
            ExecutionPlanCreate(
                name="仓库页面测试",
                project_id=8,
                test_rounds=1,
                test_type=ExecutionPlanTestTypeEnum.WEB,
            )
        )
        plan_service.add_features(
            created.id,
            ExecutionPlanFeatureAddRequest(case_type="WEB", feature_ids=[11]),
        )

        detail = run_service.run(created.id, ExecutionPlanRunRequest())

        self.assertEqual(detail.summary.run_count, 1)
        self.assertEqual(detail.summary.success_count, 1)
        self.assertEqual(detail.latest_run.status, "success")
        latest_case = detail.groups[0].features[0].cases[0]
        self.assertEqual(latest_case.latest_result.status, "success")
        self.assertEqual(latest_case.latest_result.report_record_id, 110)

    def test_hidden_legacy_runs_do_not_consume_selected_feature_rounds(self) -> None:
        repository = FakeExecutionPlanRepository()
        repository.test_cases["WEB"].append(FakeCase(id=20, name="Web 新增", project_id=8, source_id=12))
        repository.feature_map[("WEB", 12)] = "仓库新增"
        plan_service = ExecutionPlanService(repository)
        run_service = ExecutionPlanRunService(repository, repository, FakeDispatcher())
        created = plan_service.create(
            ExecutionPlanCreate(
                name="仓库页面测试",
                project_id=8,
                test_rounds=1,
                test_type=ExecutionPlanTestTypeEnum.WEB,
            )
        )
        hidden_case = repository.create_plan_cases(
            [
                {
                    "plan_id": created.id,
                    "case_type": "WEB",
                    "feature_id": 11,
                    "feature_name": "旧仓库查询",
                    "case_id": 10,
                    "case_name": "旧查询用例",
                    "snapshot_json": {"case_type": "WEB", "source_id": 11},
                    "sort_order": 1,
                }
            ]
        )[0]
        old_run = repository.create_run(
            {
                "plan_id": created.id,
                "round_no": 1,
                "status": "success",
                "total_count": 1,
            }
        )
        repository.create_run_items(
            [
                {
                    "run_id": old_run.id,
                    "plan_case_id": hidden_case.id,
                    "case_type": "WEB",
                    "case_id": hidden_case.case_id,
                    "status": "success",
                    "report_record_id": 110,
                }
            ]
        )

        selected_detail = plan_service.add_features(
            created.id,
            ExecutionPlanFeatureAddRequest(case_type="WEB", feature_ids=[12]),
        )
        executed_detail = run_service.run(created.id, ExecutionPlanRunRequest())

        self.assertEqual(selected_detail.summary.run_count, 0)
        self.assertIsNone(selected_detail.latest_run)
        self.assertEqual(executed_detail.summary.run_count, 1)
        self.assertEqual(executed_detail.latest_run.round_no, 1)
        self.assertEqual(executed_detail.groups[0].features[0].cases[0].latest_result.status, "success")

    def test_manual_feature_is_skipped_when_plan_runs(self) -> None:
        repository = FakeExecutionPlanRepository()
        repository.test_cases["WEB"].append(FakeCase(id=10, name="Web 查询", project_id=8, source_id=11))
        repository.feature_map[("WEB", 11)] = "仓库页面"
        plan_service = ExecutionPlanService(repository)
        run_service = ExecutionPlanRunService(repository, repository, FakeDispatcher())
        created = plan_service.create(
            ExecutionPlanCreate(
                name="仓库页面测试",
                project_id=8,
                test_rounds=1,
                test_type=ExecutionPlanTestTypeEnum.WEB,
            )
        )
        plan_service.add_features(
            created.id,
            ExecutionPlanFeatureAddRequest(case_type="WEB", feature_ids=[11]),
        )
        plan_service.add_manual_feature(
            created.id,
            ExecutionPlanManualFeatureCreate(feature_name="人工核对数据权限", description="人工确认数据范围"),
        )

        detail = run_service.run(created.id, ExecutionPlanRunRequest())
        manual_group = next(group for group in detail.groups if group.case_type == "MANUAL")
        manual_result = manual_group.features[0].cases[0].latest_result

        self.assertEqual(detail.summary.case_count, 2)
        self.assertEqual(detail.summary.success_count, 1)
        self.assertEqual(manual_result.status, "skipped")


if __name__ == "__main__":
    unittest.main()
