from app.db.session import SessionLocal
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.scheduler.jobs.thread_jobs import start_daemon_job
from app.services.business_generation_service import BusinessGenerationService


def submit_generation_job(task_id):
    start_daemon_job(name=f"business-generation-{task_id}", job=lambda: run_generation_job(task_id))


def run_generation_job(task_id):
    with SessionLocal() as db:
        BusinessGenerationService(SqlAlchemyResourceRepository(db)).run(task_id)
