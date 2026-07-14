from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse


router = APIRouter(prefix="/screenshots", tags=["screenshots"])
BACKEND_DIR = Path(__file__).resolve().parents[3]
SCREENSHOT_DIR = BACKEND_DIR / "storage" / "screenshots"
LEGACY_SCREENSHOT_DIR = BACKEND_DIR / "app" / "storage" / "screenshots"


@router.get("/{filename}")
def get_screenshot(filename: str) -> FileResponse:
    """Return execution screenshots from the canonical storage directory.

    Earlier scheduler executors wrote screenshots under ``backend/app/storage``.
    Keeping that path as a read-only fallback makes existing execution records
    render while new screenshots are written to ``backend/storage``.
    """

    safe_name = Path(filename).name
    if safe_name != filename or not safe_name.lower().endswith(".png"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="截图不存在")

    for directory in (SCREENSHOT_DIR, LEGACY_SCREENSHOT_DIR):
        path = directory / safe_name
        if path.exists() and path.is_file():
            return FileResponse(path, media_type="image/png")

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="截图不存在")
