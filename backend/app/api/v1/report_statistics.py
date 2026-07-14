from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import success
from app.repositories.interfaces import ResourceRepository
from app.services.report_statistics_service import ReportStatisticsService

router = APIRouter(prefix="/reports/statistics", tags=["report-statistics"])


def get_report_statistics_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> ReportStatisticsService:
    """Provide report dashboard aggregation behavior."""

    return ReportStatisticsService(repository)


@router.get("")
def get_statistics(
    project_id: int | None = None,
    service: ReportStatisticsService = Depends(get_report_statistics_service),
) -> dict[str, object]:
    return success(service.overview(project_id))
