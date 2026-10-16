from datetime import date, datetime, time

from sqlalchemy import Integer, String, case, cast, func
from sqlalchemy.orm import Session

from app.models.resource_record import ResourceRecord
from app.models.test_case_record import (
    ApiTestCaseRecord,
    AppTestCaseRecord,
    MiniappTestCaseRecord,
    WebTestCaseRecord,
)
from app.schemas.report_statistics import ReportStatisticsAggregate

CASE_MODELS = (ApiTestCaseRecord, WebTestCaseRecord, AppTestCaseRecord, MiniappTestCaseRecord)


def case_type_expression():
    record = ResourceRecord
    value = func.upper(func.coalesce(
        func.nullif(func.trim(record.data_json["case_type"].as_string()), ""),
        func.nullif(func.trim(record.data_json["data"]["case_type"].as_string()), ""), "UNKNOWN",
    ))
    return value


def duration_expression(db: Session):
    record = ResourceRecord
    value = record.data_json["data"]["duration_ms"]
    text = value.as_string()
    if db.get_bind().dialect.name == "mysql":
        kind = func.lower(func.json_type(value))
    else:
        kind = func.lower(func.json_type(record.data_json, "$.data.duration_ms"))
    numeric = cast(text, Integer)
    integer_text = cast(text, String).regexp_match(r"^[ \t\n\r]*[+-]?[0-9]+[ \t\n\r]*$")
    return case(
        (kind.in_(["integer", "real", "double", "decimal"]), numeric),
        ((kind.in_(["string", "text"])) & integer_text, numeric),
        (kind == "true", 1), (kind == "false", 0),
        (kind == "boolean", case((text.in_(["true", "1"]), 1), else_=0)),
        else_=None,
    )


def case_counts(db: Session, project_id: int | None):
    result = {}
    for model in CASE_MODELS:
        query = db.query(model.status, func.count(model.id)).filter(model.deleted.is_(False))
        if project_id is not None:
            query = query.filter(model.project_id == project_id)
        result[model.__tablename__] = {str(status or "unknown"): count for status, count in query.group_by(model.status)}
    return result


def execution_groups(db: Session, filters):
    record = ResourceRecord
    status = func.coalesce(func.nullif(func.lower(func.trim(record.status)), ""), "unknown")
    case_type = case_type_expression()
    duration = duration_expression(db)
    rows = db.query(
        status, case_type, func.count(record.id),
        func.coalesce(func.sum(case((duration >= 0, duration), else_=0)), 0),
        func.count(case((duration >= 0, 1), else_=None)),
    ).filter(*filters).group_by(status, case_type).all()
    return [{"status": state, "case_type": kind, "total": count,
             "duration_sum": int(total), "duration_count": measured} for state, kind, count, total, measured in rows]


def recent_records(db: Session, filters):
    record = ResourceRecord
    ids = [row.id for row in db.query(record.id).filter(*filters).order_by(record.updated_at.desc(), record.id.desc()).limit(8)]
    if not ids:
        return []
    rows = db.query(
        record.id, record.name, record.status, record.description, record.created_at, record.updated_at,
        case_type_expression(), record.data_json["data"]["duration_ms"], record.data_json["data"]["error"],
    ).filter(*filters, record.id.in_(ids))
    by_id = {key: {"id": key, "name": name, "status": status, "description": description,
                  "created_at": created_at.isoformat() if created_at else "",
                  "updated_at": updated_at.isoformat() if updated_at else "",
                  "data": {"case_type": kind, "duration_ms": duration, "error": error}}
             for key, name, status, description, created_at, updated_at, kind, duration, error in rows}
    return [by_id[key] for key in ids if key in by_id]


def report_statistics(db: Session, project_id: int | None, start: date, end: date) -> ReportStatisticsAggregate:
    record = ResourceRecord
    filters = [record.table_name == "execution_records", record.deleted.is_(False)]
    if project_id is not None:
        filters.append(record.project_id == project_id)
    at = func.coalesce(record.updated_at, record.created_at)
    day = func.date(at)
    status = func.coalesce(func.nullif(func.lower(func.trim(record.status)), ""), "unknown")
    trend = db.query(day, status, func.count(record.id)).filter(
        *filters, at >= datetime.combine(start, time.min), at < datetime.combine(end, time.min),
    ).group_by(day, status).all()
    return {
        "case_counts": case_counts(db, project_id),
        "execution_groups": execution_groups(db, filters),
        "trend": [{"date": str(day), "status": state, "total": total} for day, state, total in trend],
        "recent_records": recent_records(db, filters),
    }
