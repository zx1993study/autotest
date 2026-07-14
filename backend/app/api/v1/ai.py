from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.schemas.ai import WebAiGenerationRequest, WebPageAiGenerationRequest
from app.schemas.common import BatchDeleteRequest, ResourceCreate, ResourceListQuery, ResourceUpdate
from app.scheduler.jobs.ai_generation_jobs import (
    submit_saved_generation_job,
    submit_web_page_generation_job,
)
from app.services.ai_generation_service import AiGenerationService
from app.services.ai_model_service import AiModelResourceService
from app.services.ai_prompt_template_service import AiPromptTemplateService
from app.services.resource_service import ResourceService

router = APIRouter()
models_router = APIRouter(prefix="/ai/models", tags=["ai-models"])
prompts_router = APIRouter(prefix="/ai/prompt-templates", tags=["ai-prompt-templates"])
tasks_router = APIRouter(prefix="/ai/tasks", tags=["ai-tasks"])
generation_router = APIRouter(prefix="/ai", tags=["ai-generation"])


def get_ai_model_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> AiModelResourceService:
    """Provide AI model CRUD and model selection behavior."""

    return AiModelResourceService(repository)


def get_ai_generation_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> AiGenerationService:
    """Provide AI generation behavior for request-scoped operations."""

    return AiGenerationService(repository)


def get_prompt_template_option_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> AiPromptTemplateService:
    """Provide prompt template option behavior."""

    return AiPromptTemplateService(repository)


def get_prompt_template_resource_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> ResourceService:
    """Provide prompt template CRUD behavior."""

    return ResourceService("ai_prompt_templates", repository)


def get_generation_task_resource_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> ResourceService:
    """Provide AI generation task CRUD behavior."""

    return ResourceService("ai_generation_tasks", repository)


@models_router.get("")
def list_models(
    keyword: str | None = None,
    page: int = 1,
    pageSize: int = 20,
    service: AiModelResourceService = Depends(get_ai_model_service),
) -> dict[str, Any]:
    items, total = service.list(keyword, None, page, pageSize)
    return page_result(items, total, page, pageSize)


@models_router.get("/options")
def list_model_options(
    service: AiModelResourceService = Depends(get_ai_model_service),
) -> dict[str, Any]:
    items, _ = service.list(None, None, 1, 1000)
    return success(
        [
            {"id": item["id"], "name": item["name"], "model": item.get("data", {}).get("model")}
            for item in items
            if item.get("status") == "active"
        ]
    )


@models_router.get("/current")
def get_current_model(
    service: AiModelResourceService = Depends(get_ai_model_service),
) -> dict[str, Any]:
    return success(service.current_model_safe())


@models_router.post("")
def create_model(
    payload: ResourceCreate,
    service: AiModelResourceService = Depends(get_ai_model_service),
) -> dict[str, Any]:
    return success(service.create(payload.model_dump()))


@models_router.post("/{item_id:int}/set-current")
def set_current_model(
    item_id: int,
    service: AiModelResourceService = Depends(get_ai_model_service),
) -> dict[str, Any]:
    return success(service.set_current(item_id))


@models_router.post("/batch-delete")
def batch_delete_models(
    payload: BatchDeleteRequest,
    service: AiModelResourceService = Depends(get_ai_model_service),
) -> dict[str, Any]:
    return success(service.batch_delete(payload.ids))


@models_router.get("/{item_id:int}")
def get_model(
    item_id: int,
    service: AiModelResourceService = Depends(get_ai_model_service),
) -> dict[str, Any]:
    return success(service.get(item_id))


@models_router.put("/{item_id:int}")
def update_model(
    item_id: int,
    payload: ResourceUpdate,
    service: AiModelResourceService = Depends(get_ai_model_service),
) -> dict[str, Any]:
    return success(service.update(item_id, payload.model_dump(exclude_unset=True)))


@models_router.delete("/{item_id:int}")
def delete_model(
    item_id: int,
    service: AiModelResourceService = Depends(get_ai_model_service),
) -> dict[str, Any]:
    return success(service.delete(item_id))


@generation_router.post("/web-test-generation")
def generate_web_tests(
    payload: WebAiGenerationRequest,
    service: AiGenerationService = Depends(get_ai_generation_service),
) -> dict[str, Any]:
    return success(service.generate_web_tests(payload))


@generation_router.post("/web-page-generation")
def generate_web_pages(
    payload: WebPageAiGenerationRequest,
    service: AiGenerationService = Depends(get_ai_generation_service),
) -> dict[str, Any]:
    if payload.dry_run:
        return success(service.generate_web_pages(payload))
    submitted = service.submit_web_pages(payload)
    submit_web_page_generation_job(int(submitted["task_id"]), payload)
    return success(submitted)


@prompts_router.get("/options")
def list_prompt_template_options(
    template_type: str | None = None,
    service: AiPromptTemplateService = Depends(get_prompt_template_option_service),
) -> dict[str, Any]:
    return success(service.list_options(template_type))


@prompts_router.get("")
def list_prompt_templates(
    query: ResourceListQuery = Depends(),
    service: ResourceService = Depends(get_prompt_template_resource_service),
) -> dict[str, object]:
    items, total = service.list(
        query.keyword,
        query.project_id,
        query.page,
        query.page_size,
        query.data_filters(),
    )
    return page_result(items, total, query.page, query.page_size)


@prompts_router.post("")
def create_prompt_template(
    payload: ResourceCreate,
    service: ResourceService = Depends(get_prompt_template_resource_service),
) -> dict[str, object]:
    return success(service.create(payload.model_dump()))


@prompts_router.post("/batch-delete")
def batch_delete_prompt_templates(
    payload: BatchDeleteRequest,
    service: ResourceService = Depends(get_prompt_template_resource_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@prompts_router.get("/{item_id:int}")
def get_prompt_template(
    item_id: int,
    service: ResourceService = Depends(get_prompt_template_resource_service),
) -> dict[str, object]:
    return success(service.get(item_id))


@prompts_router.put("/{item_id:int}")
def update_prompt_template(
    item_id: int,
    payload: ResourceUpdate,
    service: ResourceService = Depends(get_prompt_template_resource_service),
) -> dict[str, object]:
    return success(service.update(item_id, payload.model_dump(exclude_unset=True)))


@prompts_router.delete("/{item_id:int}")
def delete_prompt_template(
    item_id: int,
    service: ResourceService = Depends(get_prompt_template_resource_service),
) -> dict[str, object]:
    return success(service.delete(item_id))


@tasks_router.post("/{task_id:int}/execute")
def execute_generation_task(
    task_id: int,
    service: AiGenerationService = Depends(get_ai_generation_service),
) -> dict[str, Any]:
    submitted = service.submit_saved_task(task_id)
    if submitted.get("status") == "queued":
        submit_saved_generation_job(task_id)
    return success(submitted)


@tasks_router.get("")
def list_generation_tasks(
    query: ResourceListQuery = Depends(),
    service: ResourceService = Depends(get_generation_task_resource_service),
) -> dict[str, object]:
    items, total = service.list(
        query.keyword,
        query.project_id,
        query.page,
        query.page_size,
        query.data_filters(),
    )
    return page_result(items, total, query.page, query.page_size)


@tasks_router.post("")
def create_generation_task(
    payload: ResourceCreate,
    service: ResourceService = Depends(get_generation_task_resource_service),
) -> dict[str, object]:
    return success(service.create(payload.model_dump()))


@tasks_router.post("/batch-delete")
def batch_delete_generation_tasks(
    payload: BatchDeleteRequest,
    service: ResourceService = Depends(get_generation_task_resource_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@tasks_router.get("/{item_id:int}")
def get_generation_task(
    item_id: int,
    service: AiGenerationService = Depends(get_ai_generation_service),
) -> dict[str, object]:
    return success(service.get_generation_task_detail(item_id))


@tasks_router.put("/{item_id:int}")
def update_generation_task(
    item_id: int,
    payload: ResourceUpdate,
    service: ResourceService = Depends(get_generation_task_resource_service),
) -> dict[str, object]:
    return success(service.update(item_id, payload.model_dump(exclude_unset=True)))


@tasks_router.delete("/{item_id:int}")
def delete_generation_task(
    item_id: int,
    service: ResourceService = Depends(get_generation_task_resource_service),
) -> dict[str, object]:
    return success(service.delete(item_id))

router.include_router(models_router)
router.include_router(prompts_router)
router.include_router(tasks_router)
router.include_router(generation_router)
