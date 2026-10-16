from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse


router = APIRouter(prefix="/app-recordings", tags=["app-recordings"])
BACKEND_DIR = Path(__file__).resolve().parents[3]
from app.core.storage import storage_path

RECORDING_DIR = storage_path("app-recordings")


@router.get("/{filename}")
def get_app_recording(filename: str) -> FileResponse:
    safe_name = Path(filename).name
    if safe_name != filename or not safe_name.lower().endswith((".mp4", ".m4v", ".webm")):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="录屏不存在")
    path = RECORDING_DIR / safe_name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="录屏不存在")
    return FileResponse(path, media_type="video/webm" if safe_name.endswith(".webm") else "video/mp4")
