from pydantic import BaseModel, ConfigDict, Field, field_validator


class SeedKnowledgeRequest(BaseModel):
    """Input DTO for provisioning system-managed test principles."""

    project_id: int = Field(ge=1)
    overwrite: bool = False


class KnowledgePlanGenerationRequest(BaseModel):
    """Validated input for generating one execution plan from a requirement."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": 10,
                "plan_name": "仓库新增页面测试计划",
                "requirement_title": "仓库新增页面",
                "requirement_document": "支持填写仓库名称、仓库地址并选择管理员后保存。",
                "principle_ids": [101, 102, 103],
                "test_rounds": 1,
            }
        }
    )

    project_id: int = Field(ge=1)
    plan_name: str = Field(min_length=1, max_length=128)
    requirement_title: str = Field(min_length=1, max_length=128)
    requirement_document: str = Field(min_length=10, max_length=30000)
    principle_ids: list[int] = Field(min_length=1, max_length=50)
    test_rounds: int = Field(default=1, ge=1, le=10000)

    @field_validator("plan_name", "requirement_title", "requirement_document", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        """Trim human-entered text before length and business validation."""

        return value.strip() if isinstance(value, str) else value

    @field_validator("principle_ids")
    @classmethod
    def unique_principle_ids(cls, value: list[int]) -> list[int]:
        """Reject non-positive identifiers and remove duplicate selections."""

        normalized = list(dict.fromkeys(value))
        if any(item <= 0 for item in normalized):
            raise ValueError("测试原则 ID 必须为正整数")
        return normalized


class KnowledgePlanGenerationOut(BaseModel):
    """Result returned after a requirement-based plan is persisted."""

    plan_id: int
    generated_case_count: int
