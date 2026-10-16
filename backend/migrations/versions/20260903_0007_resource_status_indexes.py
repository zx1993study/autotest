"""Add status-oriented indexes for generic resources.

Revision ID: 20260903_0007
Revises: 20260728_0006
Create Date: 2026-09-03
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260903_0007"
down_revision: str | None = "20260728_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_resource_table_status_deleted",
        "resource_records",
        ["table_name", "status", "deleted"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_resource_table_status_deleted", table_name="resource_records")
