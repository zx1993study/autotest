from sqlalchemy import (
    Integer,
    String,
    case,
    cast,
    func,
    literal,
    or_,
    select,
    true,
    union_all,
)
from sqlalchemy.dialects.mysql import CHAR

from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_api_report_scenes import scene_columns
from app.schemas.api_report import ApiReportQuery


def present(*values):
    return func.coalesce(*(func.nullif(value, "") for value in values))


def base_filters(kind, query):
    record = ResourceRecord
    filters = [record.table_name == kind, record.deleted.is_(False)]
    if query.project_id is not None:
        filters.append(record.project_id == query.project_id)
    return filters


def api_rows(query):
    record = ResourceRecord
    data = record.data_json["data"]
    summary = data["report"]
    return select(
        literal("api").label("kind"), record.id.label("record_id"), record.project_id,
        literal(None).label("flow_id"),
        cast(present(data["case_id"].as_string(), record.data_json["case_id"].as_string()), Integer).label("case_id"),
        literal(None).label("scenario_id"), literal(0).label("scene_index"),
        present(summary["api_path"].as_string(), data["request"]["path"].as_string(), literal("未记录接口路径")).label("source_name"),
        present(data["request"]["method"].as_string(), literal("-")).label("method"),
        present(summary["field_name"].as_string(), literal("未记录字段")).label("field_or_scene"),
        present(summary["test_point"].as_string(), record.name).label("test_point"),
        record.status.label("status"), record.created_at.label("executed_at"),
    ).where(*base_filters("execution_records", query), or_(
        data["case_type"].as_string() == "API", record.data_json["case_type"].as_string() == "API",
    ))


def flow_rows(db, query):
    record = ResourceRecord
    data = record.data_json["data"]
    source, scene = scene_columns(db, record.data_json)
    return select(
        literal("flow").label("kind"), record.id.label("record_id"), record.project_id,
        data["flow_id"].as_integer().label("flow_id"), literal(None).label("case_id"),
        scene["scenario_id"].label("scenario_id"),
        scene["scene_index"].label("scene_index"),
        present(data["flow_name"].as_string(), scene["flow_name"], record.name).label("source_name"),
        literal("").label("method"), present(scene["scene_name"], literal("未记录场景名称")).label("field_or_scene"),
        present(scene["test_point"], scene["scene_description"], scene["scene_name"], record.name).label("test_point"),
        present(scene["scene_status"], record.status).label("status"), record.created_at.label("executed_at"),
    ).select_from(record).join(source, true()).where(*base_filters("api_flow_runs", query))


def report_statement(db, query):
    branches = []
    if query.kind != "flow":
        branches.append(api_rows(query))
    if query.kind != "api":
        branches.append(flow_rows(db, query))
    if db.get_bind().dialect.name == "mysql":
        branches = [normalize_mysql_text(statement) for statement in branches]
    rows = (union_all(*branches) if len(branches) > 1 else branches[0]).subquery("api_reports")
    rows = latest_rows(rows)
    filters = []
    if query.status:
        filters.append(rows.c.status == query.status)
    if query.keyword:
        keyword = query.keyword.strip()
        filters.append(or_(*(cast(rows.c[key], String).contains(keyword, autoescape=True)
                             for key in ("source_name", "field_or_scene", "test_point"))))
    return select(rows).where(*filters)


def latest_rows(rows):
    identity = func.coalesce(rows.c.case_id, rows.c.scenario_id)
    known = identity > 0
    ranked = select(*rows.c, func.row_number().over(
        partition_by=[rows.c.kind, rows.c.project_id, rows.c.flow_id,
                      case((known, identity)),
                      case((known, 0), else_=rows.c.record_id),
                      case((known, 0), else_=rows.c.scene_index)],
        order_by=[rows.c.executed_at.desc(), rows.c.record_id.desc(), rows.c.scene_index.asc()],
    ).label("latest_rank")).subquery("ranked_reports")
    return select(*(ranked.c[value.key] for value in rows.c)).where(
        ranked.c.latest_rank == 1,
    ).subquery("latest_reports")


def normalize_mysql_text(statement):
    names = {"kind", "source_name", "method", "field_or_scene", "test_point", "status"}
    return statement.with_only_columns(*(
        cast(value, CHAR(charset="utf8mb4")).collate("utf8mb4_unicode_ci").label(value.key)
        if value.key in names else value for value in statement.selected_columns
    ))


def list_api_reports(db, query: ApiReportQuery):
    statement = report_statement(db, query)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = statement.subquery("filtered_reports")
    page = select(rows).order_by(rows.c.record_id.desc(), rows.c.scene_index.asc()).offset(
        (query.page - 1) * query.page_size,
    ).limit(query.page_size)
    return [dict(row) for row in db.execute(page).mappings()], total
