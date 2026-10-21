from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_resource_repository
from app.core.response import success
from app.repositories.interfaces import ResourceRepository
from app.schemas.miniapp_source import (
    SourceBusinessBinding,
    SourceCatalogImport,
    SourceRunRequest,
)
from app.services.miniapp_source_run_service import MiniappSourceRunService
from app.services.miniapp_source_service import MiniappSourceService

router = APIRouter(prefix="/miniapp-testing/cases/source", tags=["miniapp-cases"])
Repository = Annotated[ResourceRepository, Depends(get_resource_repository)]


@router.post("/import")
def import_catalog(payload: SourceCatalogImport, repository: Repository):
    return success(MiniappSourceService(repository).import_catalog(payload))


@router.put("/{case_id:int}/business")
def bind_business(case_id: int, payload: SourceBusinessBinding, repository: Repository):
    return success(MiniappSourceService(repository).bind_business(case_id, payload))


@router.post("/runs")
def create_run(payload: SourceRunRequest, repository: Repository):
    return success(MiniappSourceRunService(repository).create_run(payload))


@router.get("/runs")
def list_runs(repository: Repository, project_id: int = Query(ge=1)):
    return success(MiniappSourceRunService(repository).list_runs(project_id))


@router.get("/runs/{run_id:int}")
def get_run(run_id: int, repository: Repository):
    return success(MiniappSourceRunService(repository).get_run(run_id))
