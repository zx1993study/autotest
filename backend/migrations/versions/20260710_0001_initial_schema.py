"""Create the initial generic resource and test case tables.

Revision ID: 20260710_0001
Revises:
Create Date: 2026-07-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260710_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_test_case_table(table_name: str) -> None:
    """Create one domain-specific test case table with a shared shape."""

    op.create_table(
        table_name,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("data_json", sa.JSON(), nullable=False),
        sa.Column("steps_json", sa.JSON(), nullable=False),
        sa.Column("assertions_json", sa.JSON(), nullable=False),
        sa.Column("strategy_ids_json", sa.JSON(), nullable=True),
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
    op.create_index(
        f"ix_{table_name}_project_id",
        table_name,
        ["project_id"],
        unique=False,
    )
    op.create_index(
        f"ix_{table_name}_source_id",
        table_name,
        ["source_id"],
        unique=False,
    )


def upgrade() -> None:
    """Apply the initial schema."""

    op.create_table(
        "resource_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("table_name", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("data_json", sa.JSON(), nullable=False),
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
    op.create_index(
        "ix_resource_records_project_id",
        "resource_records",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_resource_records_table_name",
        "resource_records",
        ["table_name"],
        unique=False,
    )
    op.create_index(
        "ix_resource_table_project_deleted",
        "resource_records",
        ["table_name", "project_id", "deleted"],
        unique=False,
    )

    for table_name in (
        "api_test_cases",
        "web_test_cases",
        "app_test_cases",
        "miniapp_test_cases",
    ):
        _create_test_case_table(table_name)


def downgrade() -> None:
    """Drop all tables created by the initial schema."""

    for table_name in (
        "miniapp_test_cases",
        "app_test_cases",
        "web_test_cases",
        "api_test_cases",
    ):
        op.drop_index(f"ix_{table_name}_source_id", table_name=table_name)
        op.drop_index(f"ix_{table_name}_project_id", table_name=table_name)
        op.drop_table(table_name)

    op.drop_index(
        "ix_resource_table_project_deleted",
        table_name="resource_records",
    )
    op.drop_index("ix_resource_records_table_name", table_name="resource_records")
    op.drop_index("ix_resource_records_project_id", table_name="resource_records")
    op.drop_table("resource_records")
