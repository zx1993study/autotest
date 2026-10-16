from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExecutionPlan(Base):
    """Execution plan persisted in its own table.

    The plan has graduated out of ``resource_records`` because its lifecycle
    actions and reporting fields are now business concepts rather than generic
    JSON payload.
    """

    __tablename__ = "execution_plans"
    __table_args__ = (
        Index("ix_execution_plans_project_deleted", "project_id", "deleted"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    test_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    test_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirement_title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    requirement_document: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    api_ids_json: Mapped[list[int] | None] = mapped_column(JSON, nullable=True, default=list)
    web_feature_ids_json: Mapped[list[int] | None] = mapped_column(JSON, nullable=True, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ExecutionPlanCase(Base):
    """Immutable case snapshot included by an execution plan."""

    __tablename__ = "execution_plan_cases"
    __table_args__ = (
        Index("ix_execution_plan_cases_plan_type", "plan_id", "case_type"),
        Index("ix_execution_plan_cases_plan_feature", "plan_id", "feature_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    case_type: Mapped[str] = mapped_column(String(32), nullable=False)
    feature_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    feature_name: Mapped[str] = mapped_column(String(128), nullable=False)
    case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    case_name: Mapped[str] = mapped_column(String(128), nullable=False)
    case_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ExecutionPlanRun(Base):
    """One execution batch for a plan."""

    __tablename__ = "execution_plan_runs"
    __table_args__ = (
        Index("ix_execution_plan_runs_plan_round", "plan_id", "round_no"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    round_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pass_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ExecutionPlanRunItem(Base):
    """Execution result for one plan case in one run."""

    __tablename__ = "execution_plan_run_items"
    __table_args__ = (
        Index("ix_execution_plan_run_items_run_status", "run_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    plan_case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    case_type: Mapped[str] = mapped_column(String(32), nullable=False)
    case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_record_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    artifact_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
