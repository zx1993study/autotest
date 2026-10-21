from sqlalchemy import Integer, and_, cast, func, select
from sqlalchemy.orm import Session

from app.models.resource_record import ResourceRecord
from app.models.test_case_record import WebTestCaseRecord
from app.schemas.web_execution_summary import WebExecutionSnapshot, WebExecutionSummaryQuery


def web_execution_snapshots(db: Session, query: WebExecutionSummaryQuery) -> list[WebExecutionSnapshot]:
    feature = ResourceRecord
    case = WebTestCaseRecord
    page_id = cast(feature.data_json["data"]["page_group_id"].as_string(), Integer)
    identity = {"page": page_id, "feature": feature.id, "case": case.id}[query.scope]
    cases = select(
        case.id.label("case_id"), case.source_id.label("feature_id"), page_id.label("page_id"),
    ).join(feature, feature.id == case.source_id).where(
        case.deleted.is_(False), case.project_id == query.project_id,
        feature.table_name == "web_pages", feature.deleted.is_(False),
        feature.project_id == query.project_id, identity.in_(set(query.ids)),
    ).cte("summary_cases")

    record = ResourceRecord
    data = record.data_json["data"]
    record_case_id = cast(func.coalesce(data["case_id"].as_string(), record.data_json["case_id"].as_string()), Integer)
    # Rank only matching cases and project; never transfer execution payloads or images.
    ranked = select(
        record_case_id.label("case_id"), record.id.label("record_id"), record.status,
        data["business_result"].as_string().label("business_result"),
        data["assertion_count"].as_integer().label("assertion_count"),
        record.created_at.label("executed_at"),
        func.row_number().over(partition_by=record_case_id,
                               order_by=[record.created_at.desc(), record.id.desc()]).label("latest_rank"),
    ).join(cases, cases.c.case_id == record_case_id).where(
        record.table_name == "execution_records", record.deleted.is_(False),
        record.project_id == query.project_id,
        func.coalesce(data["case_type"].as_string(), record.data_json["case_type"].as_string()) == "WEB",
    ).subquery("latest_web_executions")
    statement = select(
        cases.c.case_id, cases.c.feature_id, cases.c.page_id, ranked.c.record_id,
        ranked.c.status, ranked.c.business_result, ranked.c.assertion_count, ranked.c.executed_at,
    ).select_from(cases).outerjoin(ranked, and_(
        ranked.c.case_id == cases.c.case_id, ranked.c.latest_rank == 1,
    ))
    return [dict(row) for row in db.execute(statement).mappings()]
