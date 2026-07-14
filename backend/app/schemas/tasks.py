from __future__ import annotations

from typing import Self

from pydantic import BaseModel, Field, model_validator


class OpenApiImportJobPayload(BaseModel):
    """Internal DTO for an OpenAPI import job payload.

    The HTTP layer validates upload and URL inputs, while the scheduler layer
    receives this DTO so job execution does not depend on FastAPI request types.
    """

    raw: bytes | None = None
    url: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def validate_single_source(self) -> Self:
        """Ensure the job has exactly one import source."""

        has_raw = self.raw is not None
        has_url = bool(self.url)
        if has_raw == has_url:
            raise ValueError("OpenAPI import job requires exactly one source")
        return self
