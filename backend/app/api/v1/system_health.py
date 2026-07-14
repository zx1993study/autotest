"""System health and readiness endpoints."""

from fastapi import APIRouter

from app.core.response import success
from app.services.system_status_service import SystemStatusService


router = APIRouter(prefix="/system", tags=["system-health"])


@router.get("/database-status")
def get_database_status() -> dict[str, object]:
    """Return database readiness without exposing credentials."""

    return success(SystemStatusService().database_status())
