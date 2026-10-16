"""Create dedicated execution plans table.

Revision ID: 20260717_0003
Revises: 20260715_0002
Create Date: 2026-07-17
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
import json
from typing import Any

from alembic import op
import sqlalchemy as sa


revision: str = "20260717_0003"
down_revision: str | None = "20260715_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


VALID_TEST_TYPES = {"API", "WEB", "APP", "MINIAPP"}


def upgrade() -> None:
    """Create the table and migrate legacy generic resource records."""

    op.create_table(
        "execution_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("test_rounds", sa.Integer(), nullable=False),
        sa.Column("test_type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_execution_plans_project_id", "execution_plans", ["project_id"])
    op.create_index(
        "ix_execution_plans_project_deleted",
        "execution_plans",
        ["project_id", "deleted"],
    )

    bind = op.get_bind()
    metadata = sa.MetaData()
    resource_table = sa.Table("resource_records", metadata, autoload_with=bind)
    execution_plan_table = sa.Table("execution_plans", metadata, autoload_with=bind)
    rows = bind.execute(
        sa.select(
            resource_table.c.name,
            resource_table.c.project_id,
            resource_table.c.description,
            resource_table.c.status,
            resource_table.c.data_json,
            resource_table.c.created_at,
            resource_table.c.updated_at,
        ).where(
            resource_table.c.table_name == "execution_plans",
            resource_table.c.deleted.is_(False),
        )
    ).mappings()
    for row in rows:
        data = _json_object(_json_object(row["data_json"]).get("data"))
        bind.execute(
            execution_plan_table.insert().values(
                name=str(row["name"] or "执行计划"),
                project_id=row["project_id"],
                test_rounds=_positive_int(data.get("test_rounds"), default=1),
                test_type=_test_type(data.get("test_type") or data.get("case_type")),
                description=row["description"],
                status=_status(row["status"]),
                deleted=False,
                created_at=_datetime_or_none(row["created_at"]),
                updated_at=_datetime_or_none(row["updated_at"]),
            )
        )
    bind.execute(
        resource_table.update()
        .where(resource_table.c.table_name == "execution_plans")
        .values(deleted=True)
    )


def downgrade() -> None:
    """Drop the dedicated table and unhide legacy generic records."""

    bind = op.get_bind()
    metadata = sa.MetaData()
    resource_table = sa.Table("resource_records", metadata, autoload_with=bind)
    bind.execute(
        resource_table.update()
        .where(resource_table.c.table_name == "execution_plans")
        .values(deleted=False)
    )
    op.drop_index("ix_execution_plans_project_deleted", table_name="execution_plans")
    op.drop_index("ix_execution_plans_project_id", table_name="execution_plans")
    op.drop_table("execution_plans")


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _test_type(value: Any) -> str:
    normalized = str(value or "").strip().upper()
    return normalized if normalized in VALID_TEST_TYPES else "WEB"


def _status(value: Any) -> str:
    normalized = str(value or "").strip()
    return "done" if normalized == "done" else "active"


def _datetime_or_none(value: Any) -> datetime | None:
    return value if isinstance(value, datetime) else None
