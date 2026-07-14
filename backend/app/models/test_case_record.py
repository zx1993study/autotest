from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TestCaseRecordMixin:
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    data_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    steps_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    assertions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    strategy_ids_json: Mapped[list[int]] = mapped_column(JSON, nullable=True, default=list)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ApiTestCaseRecord(TestCaseRecordMixin, Base):
    __tablename__ = "api_test_cases"


class WebTestCaseRecord(TestCaseRecordMixin, Base):
    __tablename__ = "web_test_cases"


class AppTestCaseRecord(TestCaseRecordMixin, Base):
    __tablename__ = "app_test_cases"


class MiniappTestCaseRecord(TestCaseRecordMixin, Base):
    __tablename__ = "miniapp_test_cases"
