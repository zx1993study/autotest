"""Typed, expression-free assertions for filtered JSON collections."""

from typing import Any, Literal

from jsonpointer import JsonPointer, JsonPointerException
from pydantic import BaseModel, Field, field_validator, model_validator


class QueryFieldRule(BaseModel):
    paths: list[str] = Field(min_length=1, max_length=20)
    operator: Literal["eq", "contains", "tokens", "date_ge", "date_le"]
    expected: Any

    @field_validator("paths")
    @classmethod
    def validate_paths(cls, paths):
        try:
            for path in paths:
                JsonPointer(path)
        except JsonPointerException as exc:
            raise ValueError("Invalid query rule JSON Pointer") from exc
        return paths


class QueryResultAssertion(BaseModel):
    type: Literal["json_query_result"] = "json_query_result"
    path: str
    collection: bool = Field(default=True, strict=True)
    min_items: int = Field(default=1, ge=0, strict=True)
    max_items: int | None = Field(default=None, ge=0, strict=True)
    rules: list[QueryFieldRule] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.max_items is not None and self.max_items < self.min_items:
            raise ValueError("Query result maximum is less than minimum")
        try:
            JsonPointer(self.path)
        except JsonPointerException as exc:
            raise ValueError("Invalid query result JSON Pointer") from exc
        return self
