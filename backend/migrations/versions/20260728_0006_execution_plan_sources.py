"""Persist API and Web source selections for execution plans.

Revision ID: 20260728_0006
Revises: 20260728_0005
Create Date: 2026-07-28
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260728_0006"
down_revision: str | None = "20260728_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable JSON selections without invalidating existing plans."""

    op.add_column(
        "execution_plans",
        sa.Column("api_ids_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "execution_plans",
        sa.Column("web_feature_ids_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Remove source selections from execution plans."""

    op.drop_column("execution_plans", "web_feature_ids_json")
    op.drop_column("execution_plans", "api_ids_json")
