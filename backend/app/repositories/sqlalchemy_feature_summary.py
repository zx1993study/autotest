from sqlalchemy import Integer, cast, func
from sqlalchemy.orm import Session, aliased

from app.models.resource_record import ResourceRecord
from app.models.test_case_record import WebTestCaseRecord
from app.schemas.list_summaries import AppFeatureSummary, WebFeatureCounts


def app_feature_summaries(db: Session, feature_ids: list[int]) -> dict[int, AppFeatureSummary]:
    summaries = {key: {"scenario_count": 0, "last_run": None} for key in feature_ids}
    if not feature_ids:
        return summaries
    feature = aliased(ResourceRecord)
    scene = ResourceRecord
    feature_id = cast(scene.data_json["data"]["feature_id"].as_string(), Integer)
    rows = db.query(feature_id, scene.data_json["data"]["last_run"], scene.updated_at, scene.id).join(
        feature, feature.id == feature_id,
    ).filter(
        feature.id.in_(feature_ids), feature.table_name == "app_features", feature.deleted.is_(False),
        scene.table_name == "app_feature_scenarios", scene.deleted.is_(False),
        scene.project_id.is_not_distinct_from(feature.project_id),
    )
    latest_keys = {}
    for key, last_run, updated_at, scene_id in rows.yield_per(500):
        summary = summaries[key]
        summary["scenario_count"] += 1
        if isinstance(last_run, dict):
            order = (str(last_run.get("updated_at") or last_run.get("created_at") or ""), str(updated_at), scene_id)
            if key not in latest_keys or order > latest_keys[key]:
                latest_keys[key] = order
                summary["last_run"] = last_run
    return summaries


def web_feature_counts(db: Session, feature_ids: list[int]) -> dict[int, WebFeatureCounts]:
    counts = {key: {"element_count": 0, "case_count": 0} for key in feature_ids}
    if not feature_ids:
        return counts
    feature = aliased(ResourceRecord)
    element = ResourceRecord
    feature_id = cast(element.data_json["data"]["page_id"].as_string(), Integer)
    element_rows = db.query(feature_id, func.count(element.id)).join(feature, feature.id == feature_id).filter(
        feature.id.in_(feature_ids), feature.table_name == "web_pages", feature.deleted.is_(False),
        element.table_name == "web_elements", element.deleted.is_(False),
        element.project_id.is_not_distinct_from(feature.project_id),
    ).group_by(feature_id)
    for key, count in element_rows.all():
        counts[key]["element_count"] = count
    case = WebTestCaseRecord
    case_rows = db.query(case.source_id, func.count(case.id)).join(feature, feature.id == case.source_id).filter(
        feature.id.in_(feature_ids), feature.table_name == "web_pages", feature.deleted.is_(False),
        case.deleted.is_(False), case.project_id.is_not_distinct_from(feature.project_id),
    ).group_by(case.source_id)
    for key, count in case_rows.all():
        counts[key]["case_count"] = count
    return counts
