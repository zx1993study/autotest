from app.db.session import SessionLocal
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.scheduler.jobs.thread_jobs import start_daemon_job
from app.services.web_vision_control_service import WebVisionControlService
from app.services.web_vision_discovery_service import WebVisionDiscoveryService
from app.services.web_vision_step_service import WebVisionStepService
from app.utils.cancellable_model_request import ModelRequestCancelled


def vision_cancelled(ai_task_id):
    with SessionLocal() as db:
        return WebVisionControlService(SqlAlchemyResourceRepository(db)).cancelled(ai_task_id)


def submit_vision_step(task_id, payload, job_id):
    start_daemon_job(f"web-vision-{task_id}-{job_id}", lambda: run_vision_step(task_id, payload, job_id))


def run_vision_step(task_id, payload, job_id):
    with SessionLocal() as db:
        repository = SqlAlchemyResourceRepository(db)
        task = repository.get("agent_tasks", task_id)
        ai_id = task["data"]["payload"]["ai_task_id"]
        WebVisionStepService(repository).run(task_id, payload, job_id, lambda: vision_cancelled(ai_id))


def submit_server_vision(task_id, payload):
    start_daemon_job(f"server-vision-{task_id}", lambda: run_server_vision(task_id, payload))


def run_server_vision(task_id, payload):
    with SessionLocal() as db:
        service = WebVisionDiscoveryService(SqlAlchemyResourceRepository(db))
        service.cancel_check = lambda: vision_cancelled(task_id)
        try:
            service.run_task(task_id, payload)
        except ModelRequestCancelled:
            pass
        except Exception:
            import logging

            logging.getLogger(__name__).exception("Server Web discovery failed: task_id=%s", task_id)
