"""Shared Web automation runtime used by the backend and local Agent."""

from web_automation.compiler import ExecutionPlanCompiler
from web_automation.models import (
    MANIFEST_VERSION,
    RESULT_VERSION,
    CompiledCase,
    ExecutionPlan,
    RunConfig,
)

__all__ = [
    "MANIFEST_VERSION",
    "RESULT_VERSION",
    "CompiledCase",
    "ExecutionPlan",
    "ExecutionPlanCompiler",
    "RunConfig",
]

