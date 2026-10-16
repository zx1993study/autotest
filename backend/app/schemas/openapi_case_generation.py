from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


OpenApiGenerationStrategy = Literal[
    "normal",
    "required",
    "boundary",
    "enum",
    "format",
    "type",
    "auth",
]


class OpenApiCaseGenerationRequest(BaseModel):
    """Select deterministic OpenAPI scenarios for preview or persistence."""

    project_id: int = Field(ge=1)
    snapshot_id: int | None = Field(default=None, ge=1)
    source_ids: list[int] = Field(default_factory=list, max_length=500)
    strategies: list[OpenApiGenerationStrategy] = Field(
        default_factory=lambda: ["normal", "required", "boundary", "enum", "format", "type", "auth"],
        min_length=1,
        max_length=7,
    )
    strategy_ids: list[int] = Field(default_factory=list, max_length=500)
    selected_fingerprints: list[str] | None = Field(default=None, max_length=1000)
    max_cases: int = Field(default=500, ge=1, le=1000)

    @field_validator("source_ids", "strategy_ids")
    @classmethod
    def dedupe_ids(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))

    @field_validator("strategies")
    @classmethod
    def dedupe_strategies(
        cls,
        value: list[OpenApiGenerationStrategy],
    ) -> list[OpenApiGenerationStrategy]:
        return list(dict.fromkeys(value))

    @field_validator("selected_fingerprints")
    @classmethod
    def validate_fingerprints(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = list(dict.fromkeys(str(item).strip().lower() for item in value if str(item).strip()))
        if any(len(item) != 64 or any(char not in "0123456789abcdef" for char in item) for item in normalized):
            raise ValueError("用例指纹格式无效")
        return normalized
