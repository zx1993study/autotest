from pydantic import BaseModel, ConfigDict, Field


class ApiModuleSaveRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    project_id: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
