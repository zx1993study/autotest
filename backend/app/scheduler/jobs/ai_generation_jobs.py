from __future__ import annotations

import logging

from app.db.session import SessionLocal
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.schemas.ai import WebPageAiGenerationRequest
from app.scheduler.jobs.thread_jobs import start_daemon_job
from app.services.ai_generation_service import AiGenerationService


logger = logging.getLogger(__name__)


def submit_web_page_generation_job(task_id: int, payload: WebPageAiGenerationRequest) -> None:
    """Trigger a queued AI web-page generation task."""

    start_daemon_job(
        name=f"ai-web-page-generation-{task_id}",
        job=lambda: run_web_page_generation_job(task_id, payload),
    )


def submit_saved_generation_job(task_id: int) -> None:
    """Trigger a queued AI generation task stored in the database."""

    start_daemon_job(
        name=f"ai-generation-task-{task_id}",
        job=lambda: run_saved_generation_job(task_id),
    )


def run_web_page_generation_job(task_id: int, payload: WebPageAiGenerationRequest) -> None:
    """Execute a web-page generation job by delegating to the service layer."""

    db = SessionLocal()
    try:
        service = AiGenerationService(SqlAlchemyResourceRepository(db))
        service.run_web_pages_task(task_id, payload)
    except Exception:  # noqa: BLE001 - service persists failure state; scheduler logs the trigger failure.
        logger.exception("AI web-page generation job failed: task_id=%s", task_id)
    finally:
        db.close()


def run_saved_generation_job(task_id: int) -> None:
    """Execute a stored AI generation job by delegating to the service layer."""

    db = SessionLocal()
    try:
        service = AiGenerationService(SqlAlchemyResourceRepository(db))
        service.run_saved_task(task_id)
    except Exception:  # noqa: BLE001 - service persists failure state; scheduler logs the trigger failure.
        logger.exception("AI generation job failed: task_id=%s", task_id)
    finally:
        db.close()
