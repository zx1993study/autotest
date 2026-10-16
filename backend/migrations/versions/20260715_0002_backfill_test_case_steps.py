"""Backfill formal test-case steps into the fixed steps_json column.

Revision ID: 20260715_0002
Revises: 20260710_0001
Create Date: 2026-07-15
"""

from __future__ import annotations

from collections.abc import Sequence
import json
from typing import Any

from alembic import op
import sqlalchemy as sa


revision: str = "20260715_0002"
down_revision: str | None = "20260710_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TEST_CASE_TABLES = (
    "api_test_cases",
    "web_test_cases",
    "app_test_cases",
    "miniapp_test_cases",
)


def upgrade() -> None:
    """Move legacy embedded steps into the execution contract column."""

    bind = op.get_bind()
    metadata = sa.MetaData()
    for table_name in TEST_CASE_TABLES:
        table = sa.Table(table_name, metadata, autoload_with=bind)
        rows = bind.execute(
            sa.select(table.c.id, table.c.data_json, table.c.steps_json).where(table.c.deleted.is_(False))
        ).mappings()
        for row in rows:
            if _list_dicts(row["steps_json"]):
                continue
            steps = _legacy_steps(row["data_json"])
            if steps:
                bind.execute(
                    table.update()
                    .where(table.c.id == row["id"])
                    .values(steps_json=steps)
                )


def downgrade() -> None:
    """Keep backfilled steps; removing them would destroy executable data."""


def _legacy_steps(value: Any) -> list[dict[str, Any]]:
    data = _json_object(value)
    steps = _list_dicts(data.get("steps"))
    if steps:
        return steps
    request = data.get("request")
    return _list_dicts(request.get("steps")) if isinstance(request, dict) else []


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


def _list_dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
