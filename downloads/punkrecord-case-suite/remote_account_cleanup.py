"""Audit and transactionally remove only the explicit inactive test allowlist."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID

from sqlalchemy import MetaData, select, func, cast, String, delete
from app.core.database import engine


OWNERS = {
    "users": "id", "user_role": "user_id", "org_membership": "user_id",
    "beli_account": "user_id", "beli_ledger": "user_id", "beli_task_reward": "user_id",
    "beli_order": "user_id", "todo_item": "assignee_user_id", "leave_request": "applicant_user_id",
    "notification_log": "recipient_user_id", "audit_log": "user_id", "agent_token": "user_id",
    "meeting_record": "created_by", "project": "owner_user_id",
    "kb_document": "uploaded_by", "kb_conversation": "user_id", "file_metadata": "uploaded_by",
}
CHILDREN = {
    "project_stage": ("project_id", "project"), "project_member": ("project_id", "project"),
    "meeting_transcript_segment": ("meeting_id", "meeting_record"),
    "kb_document_chunk": ("document_id", "kb_document"), "kb_message": ("conversation_id", "kb_conversation"),
}


def canonical(value):
    return str(UUID(str(value)))


def serialized(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def collect(connection, metadata, manifest, lock=False):
    users = metadata.tables["users"]
    allow = {u["id"]: u for u in manifest["delete"]}
    keep = {u["id"]: u for u in manifest["keep"]}
    expected_keep = manifest.get("expected_keep_count", 3)
    assert expected_keep in (3, 4)
    assert len(allow) == len(manifest["delete"]) and len(keep) == expected_keep and not allow.keys() & keep.keys()
    stmt = select(users).where(func.replace(cast(users.c.id, String), "-", "").in_([k.replace("-", "") for k in [*allow, *keep]]))
    if lock:
        stmt = stmt.with_for_update()
    found = {canonical(r["id"]): dict(r) for r in connection.execute(stmt).mappings()}
    for key, expected in {**allow, **keep}.items():
        if key not in found:
            assert key not in keep, f"Retained account missing: {expected['username']}"
            continue
        row = found[key]
        assert row["username"] == expected["username"] and row["display_name"] == expected["display_name"], "Account identity changed"
        if key in allow:
            assert row["status"].lower() == "inactive", f"Refusing active user {expected['username']}"
    rows = {"users": {str(r["id"]): r for k, r in found.items() if k in allow}}
    user_keys = set(rows["users"])
    changed = True
    while changed:
        changed = False
        for table in metadata.tables.values():
            for fk in table.foreign_keys:
                parent = fk.column.table.name
                if parent not in rows or fk.column.name != "id" or not rows[parent]:
                    continue
                query = select(table).where(fk.parent.in_(list(rows[parent])))
                if lock:
                    query = query.with_for_update()
                selected = [dict(r) for r in connection.execute(query).mappings()]
                for row in selected:
                    key = str(row["id"])
                    if table.name == "users":
                        assert key in user_keys, "An outside user reports to a candidate; refusing cleanup"
                    if key not in rows.setdefault(table.name, {}):
                        rows[table.name][key] = row
                        changed = True
    rows = {k: v for k, v in rows.items() if v}
    for name, selected in rows.items():
        if name in OWNERS:
            for row in selected.values():
                assert str(row[OWNERS[name]]) in user_keys, f"Outside owner in {name}; refusing cleanup"
                if name == "todo_item":
                    assert str(row["creator_user_id"]) in user_keys, "Outside task creator"
        elif name in CHILDREN:
            field, parent = CHILDREN[name]
            assert all(str(r[field]) in rows.get(parent, {}) for r in selected.values()), f"Outside parent in {name}"
        else:
            raise AssertionError(f"Unexpected dependent table {name}; manual review required")
    stable = {name: [records[k] for k in sorted(records)] for name, records in sorted(rows.items())}
    digest = hashlib.sha256(serialized(stable).encode()).hexdigest()
    counts = {name: len(records) for name, records in stable.items()}
    return stable, {"database": engine.url.database, "counts": counts, "digest": digest,
                    "delete_usernames": sorted(r["username"] for r in rows.get("users", {}).values()),
                    "keep_usernames": sorted(u["username"] for u in keep.values()),
                    "already_missing_users": sorted(allow.keys() - found.keys())}


def apply(connection, metadata, rows):
    for table in reversed(metadata.sorted_tables):
        if table.name not in rows or table.name == "users":
            continue
        keys = [r["id"] for r in rows[table.name]]
        removed = connection.execute(delete(table).where(table.c.id.in_(keys)))
        assert removed.rowcount == len(keys), f"Unexpected delete count in {table.name}"
    users = metadata.tables["users"]
    remaining = {str(r["id"]): r for r in rows.get("users", [])}
    while remaining:
        parents = {str(r["manager_user_id"]) for r in remaining.values() if r.get("manager_user_id")}
        leaves = [key for key in remaining if key not in parents]
        assert leaves, "Unexpected reporting cycle"
        for key in leaves:
            removed = connection.execute(delete(users).where(users.c.id == remaining[key]["id"]))
            assert removed.rowcount == 1
            del remaining[key]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("audit", "apply"))
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--expected-digest")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    assert manifest["target"] == "http://14.103.229.153:15173"
    assert engine.url.database == manifest["expected_database"] == "punkrecord_local"
    engine.echo = False
    metadata = MetaData()
    metadata.reflect(engine)
    with engine.begin() as connection:
        rows, plan = collect(connection, metadata, manifest, args.mode == "apply")
        if args.mode == "apply":
            assert args.expected_digest and plan["digest"] == args.expected_digest, "Plan changed; audit again"
            backup_dir = Path("/home/xiaox/data/punkrecord-test-cleanup")
            backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(backup_dir, 0o700)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = backup_dir / (stamp + "-" + plan["digest"][:12] + ".json")
            fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as output:
                output.write(serialized({"plan": plan, "manifest": manifest, "rows": rows}))
                output.flush()
                os.fsync(output.fileno())
            before = connection.scalar(select(func.count()).select_from(metadata.tables["users"]))
            apply(connection, metadata, rows)
            after = connection.scalar(select(func.count()).select_from(metadata.tables["users"]))
            assert before - after == len(rows.get("users", []))
            for expected in manifest["keep"]:
                count = connection.scalar(select(func.count()).select_from(metadata.tables["users"]).where(
                    metadata.tables["users"].c.username == expected["username"]))
                assert count == 1
            plan.update(status="deleted", backup=str(backup), users_before=before, users_after=after)
        else:
            plan["status"] = "audit_only"
    print(json.dumps(plan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
