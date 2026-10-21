from pydantic import BaseModel, ConfigDict, Field

MAX_API_FILE_SIZE = 10 * 1024 * 1024


class ApiRequestFile(BaseModel):
    """Immutable, project-scoped upload reference; never a local file path."""

    model_config = ConfigDict(extra="forbid")

    field: str = Field(default="file", pattern=r"^[A-Za-z_][A-Za-z0-9_.-]{0,63}$")
    filename: str = Field(min_length=1, max_length=200, pattern=r'^[^/\\\r\n\x00]+$')
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size: int = Field(ge=1, le=MAX_API_FILE_SIZE)
    content_type: str = Field(default="application/octet-stream", max_length=150,
                              pattern=r"^[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+$")
