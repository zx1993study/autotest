from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import get_resource_repository
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.schemas.common import (
    BatchDeleteRequest,
    ResourceCreate,
    ResourceListQuery,
    ResourceUpdate,
)
from app.schemas.testing import ScanRequest
from app.services.ui_testing_service import UiTestingService
from app.services.web_codegen_service import (
    WebCodegenService,
    resolve_codegen_target_url,
)
from app.services.web_page_service import WebPageResourceService

router = APIRouter(prefix="/web-testing/pages", tags=["web-pages"])
codegen_service = WebCodegenService()

# Compatibility export for existing tests and callers during the module move.
_codegen_target_url = resolve_codegen_target_url


def get_web_page_resource_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> WebPageResourceService:
    """Provide web page CRUD and option behavior."""

    return WebPageResourceService(repository)


def get_web_page_scan_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> UiTestingService:
    """Provide web page scan and script parsing behavior."""

    return UiTestingService("web_pages", "web_elements", repository)


@router.get("/options")
def list_page_options(
    project_id: int | None = None,
    service: WebPageResourceService = Depends(get_web_page_resource_service),
) -> dict[str, Any]:
    return success(service.list_options(project_id))


@router.post("/scan")
def scan_page(
    payload: ScanRequest,
    service: UiTestingService = Depends(get_web_page_scan_service),
) -> dict[str, object]:
    return success(
        service.scan_elements(
            payload.project_id,
            payload.page_id,
            payload.target_url,
            payload.feature,
            payload.source,
            payload.existing_element_strategy,
        )
    )


@router.post("/codegen/start")
def start_codegen(
    page_id: int = Form(...),
    target_url: str = Form(...),
    project_id: int | None = Form(None),
    feature_type: str | None = Form(None),
    feature_name: str | None = Form(None),
    repository: ResourceRepository = Depends(get_resource_repository),
) -> dict[str, object]:
    return success(
        codegen_service.start(
            repository,
            page_id=page_id,
            target_url=target_url,
            project_id=project_id,
            feature_type=feature_type,
            feature_name=feature_name,
        )
    )


@router.get("/codegen/{session_id}")
def get_codegen_status(session_id: str) -> dict[str, object]:
    return success(codegen_service.status(session_id))


@router.post("/codegen/{session_id}/stop")
def stop_codegen(session_id: str) -> dict[str, object]:
    return success(codegen_service.stop(session_id))


@router.post("/parse-script")
async def parse_script(
    project_id: int = Form(...),
    page_id: int = Form(...),
    source_type: str = Form("codegen"),
    existing_element_strategy: str = Form("update"),
    script_text: str | None = Form(None),
    file: UploadFile | None = File(None),
    service: UiTestingService = Depends(get_web_page_scan_service),
) -> dict[str, Any]:
    script = script_text or ""
    if file is not None:
        raw = await file.read()
        script = raw.decode("utf-8", errors="ignore")
    if not script.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请上传脚本文件或粘贴脚本内容")

    return success(service.parse_playwright_script(project_id, page_id, script, source_type, existing_element_strategy))


@router.get("")
def list_web_pages(
    query: ResourceListQuery = Depends(),
    service: WebPageResourceService = Depends(get_web_page_resource_service),
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
def create_web_page(
    payload: ResourceCreate,
    service: WebPageResourceService = Depends(get_web_page_resource_service),
) -> dict[str, object]:
    return success(service.create(payload.model_dump()))


@router.post("/batch-delete")
def batch_delete_web_pages(
    payload: BatchDeleteRequest,
    service: WebPageResourceService = Depends(get_web_page_resource_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@router.get("/{item_id:int}")
def get_web_page(
    item_id: int,
    service: WebPageResourceService = Depends(get_web_page_resource_service),
) -> dict[str, object]:
    return success(service.get(item_id))


@router.put("/{item_id:int}")
def update_web_page(
    item_id: int,
    payload: ResourceUpdate,
    service: WebPageResourceService = Depends(get_web_page_resource_service),
) -> dict[str, object]:
    return success(service.update(item_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{item_id:int}")
def delete_web_page(
    item_id: int,
    service: WebPageResourceService = Depends(get_web_page_resource_service),
) -> dict[str, object]:
    return success(service.delete(item_id))
