from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import page_result
from app.repositories.interfaces import ResourceRepository
from app.schemas.api_report import ApiReportQuery
from app.services.api_report_service import ApiReportService

router = APIRouter(prefix="/api-testing/reports", tags=["api-reports"])


def get_service(repository: Annotated[ResourceRepository, Depends(get_resource_repository)]):
    return ApiReportService(repository)


@router.get("")
def list_reports(query: Annotated[ApiReportQuery, Depends()], service: Annotated[ApiReportService, Depends(get_service)]):
    rows, total = service.list(query)
    return page_result(rows, total, query.page, query.page_size)
