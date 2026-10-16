from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.system_status_service import SystemStatusService

router = APIRouter()


@router.get("/health")
def health():
    result = SystemStatusService().readiness()
    return JSONResponse(result, status_code=200 if result["ready"] else 503)
