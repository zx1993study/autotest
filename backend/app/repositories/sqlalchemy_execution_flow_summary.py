"""Batch flow-list metadata without loading execution evidence or sorting JSON."""

from sqlalchemy import Integer, cast
from sqlalchemy.orm import Session

from app.models.resource_record import ResourceRecord
from app.schemas.execution_flow import ExecutionFlowSummary


def execution_flow_summaries(db: Session, flow_ids: list[int]) -> dict[int, ExecutionFlowSummary]:
    summaries: dict[int, ExecutionFlowSummary] = {
        flow_id: {"scenario_count": 0, "latest_status": None} for flow_id in flow_ids
    }
    if not summaries:
        return summaries
    record = ResourceRecord
    flow_id = cast(record.data_json["data"]["flow_id"].as_string(), Integer)
    rows = db.query(
        record.table_name, flow_id.label("flow_id"), record.id, record.status, record.updated_at,
    ).filter(
        record.table_name.in_(("api_flow_scenarios", "api_flow_runs")),
        record.deleted.is_(False), flow_id.in_(flow_ids),
    )
    latest_keys = {}
    # Reduce only scalar metadata; JSON ordering can exhaust MySQL's sort memory.
    for row in rows.yield_per(500):
        summary = summaries[row.flow_id]
        if row.table_name == "api_flow_scenarios":
            summary["scenario_count"] += 1
            continue
        key = (row.updated_at, row.id)
        if row.flow_id not in latest_keys or key > latest_keys[row.flow_id]:
            latest_keys[row.flow_id] = key
            summary["latest_status"] = row.status
    return summaries
