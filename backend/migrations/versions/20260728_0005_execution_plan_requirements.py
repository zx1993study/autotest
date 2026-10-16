"""Persist source requirements and generation metadata on execution plans.

Revision ID: 20260728_0005
Revises: 20260717_0004
Create Date: 2026-07-28
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260728_0005"
down_revision: str | None = "20260717_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable source fields so existing plans remain valid."""

    op.add_column(
        "execution_plans",
        sa.Column("requirement_title", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "execution_plans",
        sa.Column("requirement_document", sa.Text(), nullable=True),
    )
    op.add_column(
        "execution_plans",
        sa.Column("generation_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Remove requirement-based generation fields."""

    op.drop_column("execution_plans", "generation_json")
    op.drop_column("execution_plans", "requirement_document")
    op.drop_column("execution_plans", "requirement_title")
