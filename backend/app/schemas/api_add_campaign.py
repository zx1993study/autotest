from pydantic import BaseModel, Field

from app.core.types import JsonObject


class ApiAddInputProfile(BaseModel):
    """Verified inputs for one add endpoint; contains no connection credentials."""

    source_id: int = Field(ge=1)
    table_name: str = Field(min_length=1, max_length=64)
    params: JsonObject
    unique_text_fields: list[str] = Field(default_factory=list)
    required_fields: list[str] = Field(default_factory=list)
    rejection_messages: dict[str, list[str]] = Field(default_factory=dict)
    field_constraints: dict[str, JsonObject] = Field(default_factory=dict)
    excluded_fields: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ApiAddCampaignRequest(BaseModel):
    project_id: int = Field(ge=1)
    snapshot_id: int = Field(ge=1)
    campaign_key: str = Field(min_length=1, max_length=128)
    profiles: list[ApiAddInputProfile] = Field(min_length=1, max_length=100)
