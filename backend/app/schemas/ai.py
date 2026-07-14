from __future__ import annotations

from pydantic import BaseModel, Field


class WebAiGenerationRequest(BaseModel):
    project_id: int = Field(gt=0)
    page_id: int = Field(gt=0)
    model_id: int | None = None
    prompt_template_id: int | None = None
    strategy_ids: list[int] = Field(default_factory=list)
    user_prompt: str | None = None
    dry_run: bool = False
    save_elements: bool = True
    save_case_drafts: bool = True
    include_existing_elements: bool = True
    include_strategies: bool = True
    dom_snapshot: str | None = None


class WebPageAiGenerationRequest(BaseModel):
    project_id: int = Field(gt=0)
    model_id: int | None = None
    prompt_template_id: int | None = None
    login_case_id: int | None = None
    user_prompt: str | None = None
    dry_run: bool = False
    overwrite_existing: bool = False
    include_existing_pages: bool = True
    include_api_interfaces: bool = True
    include_knowledge: bool = True
    discover_after_login: bool = True
    discovery_max_pages: int = Field(default=30, ge=1, le=100)
    discovery_timeout_ms: int = Field(default=15000, ge=3000, le=120000)
    discovery_wait_ms: int = Field(default=1000, ge=0, le=10000)
    discovery_headless: bool = True


class WebFunctionElementGenerationRequest(BaseModel):
    project_id: int = Field(gt=0)
    model_id: int | None = None
    prompt_template_id: int | None = None
    login_case_id: int | None = None
    user_prompt: str | None = None
    scan_scope: str = "single"
    page_id: int | None = None
    page_ids: list[int] = Field(default_factory=list)
    operation_timeout_sec: int = Field(default=120, ge=10, le=600)
    headless: bool = True
    scan_instruction: str | None = None
    existing_element_strategy: str = "update"
