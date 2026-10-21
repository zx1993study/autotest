from datetime import datetime

import pytest
from sqlalchemy import select

from app.models.resource_record import ResourceRecord
from app.schemas.api_report import ApiReportQuery

pytest_plugins = ("tests.test_api_reports",)


def add_record(db, number, kind="api", *, project=10, case_id=100, flow=88, scenes=None, **values):
    data = {"case_type": "API", "case_id": case_id} if kind == "api" else {"flow_id": flow, "results": scenes}
    record = ResourceRecord(id=number, table_name="execution_records" if kind == "api" else "api_flow_runs",
                            project_id=project, name="Same test point", status="success",
                            data_json={"data": data}, created_at=datetime(2026, 10, 21, 8), **values)
    db.add(record)
    db.commit()


def scene(number, status="success", name="Same scenario"):
    return {"scenario_id": number, "name": name, "status": status}


def test_api_latest_is_selected_before_status_search_count_and_pagination(reports):
    _, service, db = reports
    add_record(db, 200, case_id=101)
    rows, total = service.list(ApiReportQuery(project_id=10, kind="api", page_size=100))
    assert total == 26
    assert next(row for row in rows if row["case_id"] == 101)["record_id"] == 200
    rows, total = service.list(ApiReportQuery(project_id=10, status="failed"))
    assert total == 12 and 2 not in [row["record_id"] for row in rows]
    _, total = service.list(ApiReportQuery(project_id=10, keyword="warehouseType = 1"))
    assert total == 10  # 10..19 remain; the renamed latest record replaces old test point 1.
    pages = [service.list(ApiReportQuery(project_id=10, page=page, page_size=10))[0] for page in range(1, 4)]
    assert [len(rows) for rows in pages] == [10, 10, 8]
    assert len({row["key"] for rows in pages for row in rows}) == 28
    assert db.scalar(select(ResourceRecord.id).where(ResourceRecord.id == 2)) == 2


def test_scenes_use_stable_ids_and_do_not_merge_names_or_other_flows_or_projects(reports):
    _, service, db = reports
    add_record(db, 200, "flow", scenes=[scene(101), scene(102), scene(103)])
    add_record(db, 201, "flow", flow=89, scenes=[scene(101)])
    add_record(db, 202, "flow", project=20, scenes=[scene(101)])
    rows, total = service.list(ApiReportQuery(project_id=10, kind="flow", page_size=100))
    assert total == 4
    assert [(row["record_id"], row["scenario_id"]) for row in rows] == [(201, 101), (200, 101), (200, 102), (200, 103)]
    assert service.list(ApiReportQuery(project_id=10, kind="flow", status="failed"))[1] == 0
    assert service.list(ApiReportQuery(kind="flow"))[1] == 5


@pytest.mark.parametrize("case_id", [None, 0, -1])
def test_missing_case_identity_keeps_unknown_records_separate(reports, case_id):
    _, service, db = reports
    add_record(db, 200, case_id=case_id)
    add_record(db, 201, case_id=case_id)
    rows, total = service.list(ApiReportQuery(project_id=10, kind="api", page_size=100))
    assert total == 28
    assert {200, 201}.issubset({row["record_id"] for row in rows})


def test_missing_scene_identity_keeps_unknown_rows_in_same_batch_separate(reports):
    _, service, db = reports
    add_record(db, 200, "flow", scenes=[scene(None), scene(None)])
    rows, total = service.list(ApiReportQuery(project_id=10, kind="flow", page_size=100))
    assert total == 4 and len({row["key"] for row in rows}) == 4


def test_recency_uses_creation_time_then_record_id_not_completion_or_status(reports):
    _, service, db = reports
    add_record(db, 200)
    add_record(db, 201)
    add_record(db, 202, deleted=True)
    row = db.get(ResourceRecord, 201)
    row.status = "running"
    db.commit()
    rows, _ = service.list(ApiReportQuery(project_id=10, kind="api"))
    assert rows[0]["record_id"] == 201 and rows[0]["passed"] is None
    row.created_at = datetime(2026, 10, 20, 8)
    db.commit()
    rows, _ = service.list(ApiReportQuery(project_id=10, kind="api"))
    assert rows[0]["record_id"] == 200


def test_legacy_case_id_and_project_namespace_are_supported(reports):
    _, service, db = reports
    add_record(db, 200)
    add_record(db, 201, project=20)
    row = db.get(ResourceRecord, 200)
    row.data_json = {"case_type": "API", "case_id": 100, "data": {}}
    db.commit()
    rows, _ = service.list(ApiReportQuery(kind="api", page_size=100))
    assert {row["record_id"] for row in rows if row["case_id"] == 100} == {200, 201}
