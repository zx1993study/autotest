from __future__ import annotations

import logging

from app.db.session import SessionLocal
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.schemas.tasks import OpenApiImportJobPayload
from app.scheduler.jobs.thread_jobs import start_daemon_job
from app.services.openapi_import_task_service import OpenApiImportTaskService


logger = logging.getLogger(__name__)


def submit_openapi_import_job(task_id: int, payload: OpenApiImportJobPayload) -> None:
    """Trigger an OpenAPI import task."""

    start_daemon_job(
        name=f"openapi-import-{task_id}",
        job=lambda: run_openapi_import_job(task_id, payload),
    )


def run_openapi_import_job(task_id: int, payload: OpenApiImportJobPayload) -> None:
    """Execute an OpenAPI import job by delegating to the service layer."""

    db = SessionLocal()
    try:
        service = OpenApiImportTaskService(SqlAlchemyResourceRepository(db))
        service.run_task(task_id, payload)
    except Exception:  # noqa: BLE001 - scheduler must keep worker exceptions isolated.
        logger.exception("OpenAPI import job failed: task_id=%s", task_id)
    finally:
        db.close()
