from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_resource_repository
from app.core.response import success
from app.core.response import page_result
from app.db.session import get_db
from app.repositories.interfaces import ResourceRepository
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.schemas.common import BatchDeleteRequest, ResourceCreate, ResourceUpdate
from app.scheduler.jobs.project_auth_jobs import refresh_project_auth_job
from app.services.project_auth_resource_service import ProjectAuthResourceService
from app.services.project_auth_service import ProjectAuthService

router = APIRouter(prefix="/project-auth", tags=["project-auth"])


class CookieAuthGenerateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    record_id: int
    case_id: int | None = None


class TokenAuthGenerateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    token: str = Field(min_length=1)
    project_id: int | None = None
    login_case_id: int | None = None
    source_record_id: int | None = None
    header_name: str = "Authorization"
    auth_type: str = "bearer"
    login_case_type: str = "API"
    refresh_strategy: str = "manual"
    description: str | None = None


class AuthRefreshRequest(BaseModel):
    mode: str = Field(default="local_headless", max_length=64)
    config: dict[str, Any] = Field(default_factory=dict)


@router.get("/options")
def list_auth_options(
    project_id: int | None = None,
    login_case_type: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    service = ProjectAuthService(SqlAlchemyResourceRepository(db))
    return success(service.list_options(project_id, login_case_type))


@router.post("/generate-cookie")
def generate_cookie_auth(
    payload: CookieAuthGenerateRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    service = ProjectAuthService(SqlAlchemyResourceRepository(db))
    return success(service.generate_cookie_auth(payload.model_dump()))


@router.post("/generate-token")
def generate_token_auth(
    payload: TokenAuthGenerateRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    service = ProjectAuthService(SqlAlchemyResourceRepository(db))
    return success(service.generate_token_auth(payload.model_dump()))


@router.post("/{item_id:int}/refresh")
def refresh_auth_item(
    item_id: int,
    payload: AuthRefreshRequest,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> dict[str, Any]:
    return success(refresh_project_auth_job(item_id, payload.model_dump(), repository))


def _resource_service(db: Session) -> ProjectAuthResourceService:
    return ProjectAuthResourceService(SqlAlchemyResourceRepository(db))


@router.get("")
def list_auth_items(
    project_id: int | None = None,
    keyword: str | None = None,
    page: int = 1,
    pageSize: int = 20,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    items, total = _resource_service(db).list(keyword, project_id, page, pageSize)
    return page_result(items, total, page, pageSize)


@router.post("")
def create_auth_item(payload: ResourceCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    return success(_resource_service(db).create(payload.model_dump()))


@router.post("/batch-delete")
def batch_delete_auth_items(payload: BatchDeleteRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    return success(_resource_service(db).batch_delete(payload.ids))


@router.get("/{item_id:int}")
def get_auth_item(item_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    return success(_resource_service(db).get(item_id))


@router.put("/{item_id:int}")
def update_auth_item(
    item_id: int,
    payload: ResourceUpdate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return success(_resource_service(db).update(item_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{item_id:int}")
def delete_auth_item(item_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    return success(_resource_service(db).delete(item_id))
