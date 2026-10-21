"""Construct legacy shapes only on newly-created allowlisted test tasks."""
from datetime import timedelta
import json
import sys
from uuid import UUID

from sqlalchemy import MetaData, String, cast, func, select, update
from app.core.database import engine


def canonical(value):
    return str(UUID(str(value)))


def id_match(column, value):
    return func.replace(cast(column, String), "-", "") == UUID(value).hex


def main():
    engine.echo = False
    plan = json.load(sys.stdin)
    assert plan["target"] == "http://14.103.229.153:15173"
    assert plan["prefix"].startswith("CASE_20261019_")
    allowed = {"8cf5d346-2a85-4ffc-ae03-a07e07e26e7c", "23aec9cd-977d-448a-a716-22546cec2e9c", "a6be1d21-7582-46d5-97c9-e6ecacb4b3ad"}
    metadata = MetaData()
    metadata.reflect(bind=engine, only=["todo_item", "beli_policy", "leave_request"])
    todo, policy, leaves = [metadata.tables[name] for name in ("todo_item", "beli_policy", "leave_request")]
    with engine.begin() as connection:
        row = connection.execute(select(todo).where(id_match(todo.c.id, plan["task_id"])).with_for_update()).mappings().one()
        assert row["title"].startswith(plan["prefix"] + " 历史夹具 ")
        assert canonical(row["creator_user_id"]) in allowed and canonical(row["assignee_user_id"]) in allowed
        assert row["source_id"] is None or canonical(row["source_id"]) == plan["project_id"]
        mode = plan["mode"]
        if mode == "missing_due":
            changes = {"due_at": None}
        elif mode == "missing_hours":
            changes = {"estimated_hours": None}
        elif mode == "missing_submit":
            assert row["status"].lower() in ("pending_review", "done")
            changes = {"submitted_at": None}
        elif mode == "predates_rule":
            assert row["status"].lower() == "done" and not row["estimated_hours"]
            current = connection.execute(select(policy)).mappings().one()
            assert current["hours_rule_starts_at"] is not None
            cutoff = current["hours_rule_starts_at"] - timedelta(days=1)
            changes = {"done_at": cutoff, "submitted_at": cutoff - timedelta(hours=1), "due_at": cutoff - timedelta(days=1)}
        elif mode == "historical_leave":
            leave = connection.execute(select(leaves).where(id_match(leaves.c.id, plan["leave_id"]))).mappings().one()
            assert canonical(leave["applicant_user_id"]) in allowed and leave["reason"].startswith(plan["prefix"] + " ")
            changes = {"link": {**(row["link"] or {}), "leave_id": plan["leave_id"]}}
        else:
            raise AssertionError("Unsupported fixture operation")
        result = connection.execute(update(todo).where(todo.c.id == row["id"]).values(**changes))
        assert result.rowcount == 1
        audit = {"task_id": plan["task_id"], "mode": mode, "database": engine.url.database,
            "before": {key: row[key] for key in changes}, "after": changes, "only_new_allowlisted_task": True}
    print(json.dumps(audit, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
