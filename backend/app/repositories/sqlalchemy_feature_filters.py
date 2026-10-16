from sqlalchemy import Integer, case, cast, func, or_
from sqlalchemy.orm import aliased

from app.models.resource_record import ResourceRecord
from app.models.test_case_record import WebTestCaseRecord


def _device_number(db, record, field: str):
    value = record.data_json["data"][field].as_string()
    path = f'$."data"."{field}"'
    if db.get_bind().dialect.name == "sqlite":
        kind = func.json_type(record.data_json, path)
    else:
        kind = func.lower(func.json_type(func.json_extract(record.data_json, path)))
    integer_text = value.regexp_match(r"^[ \t\n\r]*[+-]?[0-9]+[ \t\n\r]*$")
    return case(
        (kind.in_(["integer", "real", "double", "decimal"]), cast(value, Integer)),
        (kind.in_(["text", "string"]) & integer_text, cast(value, Integer)),
        (kind == "true", 1), (kind == "false", 0),
        (kind == "boolean", case((func.lower(value).in_(["true", "1"]), 1), else_=0)),
        else_=None,
    )


def app_device_filter(db, table: str, device_id: int):
    record = ResourceRecord
    if table == "app_feature_scenarios":
        device = _device_number(db, record, "device_id")
        return or_(device == device_id, device.is_(None), device <= 0)
    scene = aliased(ResourceRecord)
    matching_scene = db.query(scene.id).filter(
        scene.table_name == "app_feature_scenarios", scene.deleted.is_(False),
        scene.project_id.is_not_distinct_from(record.project_id),
        cast(scene.data_json["data"]["feature_id"].as_string(), Integer) == record.id,
        _device_number(db, scene, "device_id") == device_id,
    ).correlate(record).exists()
    return or_(_device_number(db, record, "default_device_id") == device_id, matching_scene)


def web_script_status(db):
    record = ResourceRecord
    stored = record.data_json["data"]["script_status"].as_string()
    has_case = db.query(WebTestCaseRecord.id).filter(
        WebTestCaseRecord.source_id == record.id, WebTestCaseRecord.deleted.is_(False),
        WebTestCaseRecord.project_id.is_not_distinct_from(record.project_id),
    ).correlate(record).exists()
    return case((stored.is_not(None) & (stored != ""), stored), (has_case, "legacy"), else_="missing")
