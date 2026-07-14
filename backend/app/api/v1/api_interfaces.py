from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import get_resource_repository
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.schemas.common import (
    BatchDeleteRequest,
    ImportPayload,
    ImportUrlPayload,
    ResourceCreate,
    ResourceListQuery,
    ResourceUpdate,
)
from app.schemas.tasks import OpenApiImportJobPayload
from app.scheduler.jobs.openapi_import_jobs import submit_openapi_import_job
from app.services.api_testing_service import ApiTestingService
from app.services.openapi_import_task_service import OpenApiImportTaskService
from app.services.resource_service import ResourceService

router = APIRouter(prefix="/api-testing/interfaces", tags=["api-interfaces"])


def get_api_interface_resource_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> ResourceService:
    """Provide API interface CRUD behavior."""

    return ResourceService("api_interfaces", repository)


def get_api_testing_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> ApiTestingService:
    """Provide API interface import and option behavior."""

    return ApiTestingService(repository)


def get_openapi_import_task_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> OpenApiImportTaskService:
    """Provide asynchronous OpenAPI import task behavior."""

    return OpenApiImportTaskService(repository)


@router.post("/import")
def import_apis(
    payload: ImportPayload,
    service: ApiTestingService = Depends(get_api_testing_service),
) -> dict[str, object]:
    try:
        return success(service.import_openapi(payload.project_id, payload.content, payload.overwrite))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/import-file")
async def import_openapi_file(
    project_id: int = Form(...),
    overwrite: bool = Form(True),
    file: UploadFile = File(...),
    service: OpenApiImportTaskService = Depends(get_openapi_import_task_service),
) -> dict[str, Any]:
    filename = file.filename or ""
    if not filename.lower().endswith(".json"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请上传 OpenAPI JSON 文件")
    raw = await file.read()
    try:
        task = service.create_file_task(project_id, filename, overwrite)
        submit_openapi_import_job(int(task["id"]), OpenApiImportJobPayload(raw=raw))
        return success(service.get_task(int(task["id"])))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/import-url")
def import_openapi_url(
    payload: ImportUrlPayload,
    service: OpenApiImportTaskService = Depends(get_openapi_import_task_service),
) -> dict[str, Any]:
    try:
        task = service.create_url_task(payload.project_id, payload.url, payload.overwrite)
        submit_openapi_import_job(int(task["id"]), OpenApiImportJobPayload(url=payload.url))
        return success(service.get_task(int(task["id"])))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/import-tasks/{task_id:int}")
def get_import_task(
    task_id: int,
    service: OpenApiImportTaskService = Depends(get_openapi_import_task_service),
) -> dict[str, Any]:
    try:
        return success(service.get_task(task_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/options")
def list_interface_options(
    project_id: int | None = None,
    service: ApiTestingService = Depends(get_api_testing_service),
) -> dict[str, Any]:
    return success(service.list_interface_options(project_id))


@router.get("")
def list_api_interfaces(
    query: ResourceListQuery = Depends(),
    service: ResourceService = Depends(get_api_interface_resource_service),
) -> dict[str, object]:
    items, total = service.list(
        query.keyword,
        query.project_id,
        query.page,
        query.page_size,
        query.data_filters(),
    )
    return page_result(items, total, query.page, query.page_size)


@router.post("")
def create_api_interface(
    payload: ResourceCreate,
    service: ResourceService = Depends(get_api_interface_resource_service),
) -> dict[str, object]:
    return success(service.create(payload.model_dump()))


@router.post("/batch-delete")
def batch_delete_api_interfaces(
    payload: BatchDeleteRequest,
    service: ResourceService = Depends(get_api_interface_resource_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@router.get("/{item_id:int}")
def get_api_interface(
    item_id: int,
    service: ResourceService = Depends(get_api_interface_resource_service),
) -> dict[str, object]:
    return success(service.get(item_id))


@router.put("/{item_id:int}")
def update_api_interface(
    item_id: int,
    payload: ResourceUpdate,
    service: ResourceService = Depends(get_api_interface_resource_service),
) -> dict[str, object]:
    return success(service.update(item_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{item_id:int}")
def delete_api_interface(
    item_id: int,
    service: ResourceService = Depends(get_api_interface_resource_service),
) -> dict[str, object]:
    return success(service.delete(item_id))
