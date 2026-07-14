"""Backward-compatible enum exports.

New code should import from :mod:`app.enums`. This module remains temporarily
so existing modules can migrate without a flag-day import rewrite.
"""

from app.enums.business import (
    CaseTypeEnum as ResourceKind,
    ExecutionModeEnum as ExecutionMode,
    ResourceStatusEnum as CaseStatus,
)

__all__ = ["CaseStatus", "ExecutionMode", "ResourceKind"]
