"""Create execution plan case snapshots and run result tables.

Revision ID: 20260717_0004
Revises: 20260717_0003
Create Date: 2026-07-17
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260717_0004"
down_revision: str | None = "20260717_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create execution plan detail tables."""

    op.create_table(
        "execution_plan_cases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("case_type", sa.String(length=32), nullable=False),
        sa.Column("feature_id", sa.Integer(), nullable=True),
        sa.Column("feature_name", sa.String(length=128), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("case_name", sa.String(length=128), nullable=False),
        sa.Column("case_version", sa.String(length=64), nullable=True),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
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
    op.create_index("ix_execution_plan_cases_plan_id", "execution_plan_cases", ["plan_id"])
    op.create_index("ix_execution_plan_cases_feature_id", "execution_plan_cases", ["feature_id"])
    op.create_index("ix_execution_plan_cases_case_id", "execution_plan_cases", ["case_id"])
    op.create_index(
        "ix_execution_plan_cases_plan_type",
        "execution_plan_cases",
        ["plan_id", "case_type"],
    )
    op.create_index(
        "ix_execution_plan_cases_plan_feature",
        "execution_plan_cases",
        ["plan_id", "feature_id"],
    )

    op.create_table(
        "execution_plan_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("pass_rate", sa.Float(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
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
    op.create_index("ix_execution_plan_runs_plan_id", "execution_plan_runs", ["plan_id"])
    op.create_index(
        "ix_execution_plan_runs_plan_round",
        "execution_plan_runs",
        ["plan_id", "round_no"],
    )

    op.create_table(
        "execution_plan_run_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("plan_case_id", sa.Integer(), nullable=False),
        sa.Column("case_type", sa.String(length=32), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("report_record_id", sa.Integer(), nullable=True),
        sa.Column("artifact_json", sa.JSON(), nullable=False),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_execution_plan_run_items_run_id", "execution_plan_run_items", ["run_id"])
    op.create_index(
        "ix_execution_plan_run_items_plan_case_id",
        "execution_plan_run_items",
        ["plan_case_id"],
    )
    op.create_index("ix_execution_plan_run_items_case_id", "execution_plan_run_items", ["case_id"])
    op.create_index(
        "ix_execution_plan_run_items_report_record_id",
        "execution_plan_run_items",
        ["report_record_id"],
    )
    op.create_index(
        "ix_execution_plan_run_items_run_status",
        "execution_plan_run_items",
        ["run_id", "status"],
    )


def downgrade() -> None:
    """Drop execution plan detail tables."""

    op.drop_index("ix_execution_plan_run_items_run_status", table_name="execution_plan_run_items")
    op.drop_index("ix_execution_plan_run_items_report_record_id", table_name="execution_plan_run_items")
    op.drop_index("ix_execution_plan_run_items_case_id", table_name="execution_plan_run_items")
    op.drop_index("ix_execution_plan_run_items_plan_case_id", table_name="execution_plan_run_items")
    op.drop_index("ix_execution_plan_run_items_run_id", table_name="execution_plan_run_items")
    op.drop_table("execution_plan_run_items")

    op.drop_index("ix_execution_plan_runs_plan_round", table_name="execution_plan_runs")
    op.drop_index("ix_execution_plan_runs_plan_id", table_name="execution_plan_runs")
    op.drop_table("execution_plan_runs")

    op.drop_index("ix_execution_plan_cases_plan_feature", table_name="execution_plan_cases")
    op.drop_index("ix_execution_plan_cases_plan_type", table_name="execution_plan_cases")
    op.drop_index("ix_execution_plan_cases_case_id", table_name="execution_plan_cases")
    op.drop_index("ix_execution_plan_cases_feature_id", table_name="execution_plan_cases")
    op.drop_index("ix_execution_plan_cases_plan_id", table_name="execution_plan_cases")
    op.drop_table("execution_plan_cases")
