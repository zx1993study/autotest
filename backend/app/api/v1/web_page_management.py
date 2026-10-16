
from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.schemas.web_page_management import (
    WebPageApiRelationCreate,
    WebPageFeatureListQuery,
    WebPageGroupCreate,
    WebPageGroupListQuery,
    WebPageGroupUpdate,
    WebPageInterfaceListQuery,
)
from app.services.web_page_management_service import WebPageManagementService

router = APIRouter(prefix="/web-testing/page-groups", tags=["web-page-management"])


def get_web_page_management_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> WebPageManagementService:
    return WebPageManagementService(repository)


@router.get("")
def list_page_groups(
    query: WebPageGroupListQuery = Depends(),
    service: WebPageManagementService = Depends(get_web_page_management_service),
) -> dict[str, object]:
    items, total = service.list_groups(
        query.project_id,
        query.keyword,
        query.status,
        query.page,
        query.page_size,
    )
    return page_result(items, total, query.page, query.page_size)


@router.post("")
def create_page_group(
    payload: WebPageGroupCreate,
    service: WebPageManagementService = Depends(get_web_page_management_service),
) -> dict[str, object]:
    return success(service.create_group(payload.model_dump()))


@router.get("/{group_id:int}")
def get_page_group(
    group_id: int,
    service: WebPageManagementService = Depends(get_web_page_management_service),
) -> dict[str, object]:
    return success(service.get_group(group_id))


@router.put("/{group_id:int}")
def update_page_group(
    group_id: int,
    payload: WebPageGroupUpdate,
    service: WebPageManagementService = Depends(get_web_page_management_service),
) -> dict[str, object]:
    return success(service.update_group(group_id, payload.model_dump(exclude_unset=True)))


@router.get("/{group_id:int}/features")
def list_page_features(
    group_id: int,
    query: WebPageFeatureListQuery = Depends(),
    service: WebPageManagementService = Depends(get_web_page_management_service),
) -> dict[str, object]:
    items, total = service.list_features(
        group_id, query.keyword, query.status, query.page, query.page_size,
        feature_type=query.feature_type, script_status=query.script_status,
    )
    return page_result(items, total, query.page, query.page_size)


@router.get("/{group_id:int}/interfaces")
def list_page_interfaces(
    group_id: int,
    query: WebPageInterfaceListQuery = Depends(),
    service: WebPageManagementService = Depends(get_web_page_management_service),
) -> dict[str, object]:
    items, total = service.list_interfaces(
        group_id,
        query.feature_id,
        query.keyword,
        query.method,
        query.page,
        query.page_size,
    )
    return page_result(items, total, query.page, query.page_size)


@router.post("/{group_id:int}/interface-relations")
def create_page_interface_relations(
    group_id: int,
    payload: WebPageApiRelationCreate,
    service: WebPageManagementService = Depends(get_web_page_management_service),
) -> dict[str, object]:
    return success(
        service.create_relations(
            group_id,
            payload.interface_ids,
            payload.feature_id,
            payload.source,
        )
    )


@router.delete("/{group_id:int}/interface-relations/{relation_id:int}")
def delete_page_interface_relation(
    group_id: int,
    relation_id: int,
    service: WebPageManagementService = Depends(get_web_page_management_service),
) -> dict[str, object]:
    return success(service.delete_relation(group_id, relation_id))
