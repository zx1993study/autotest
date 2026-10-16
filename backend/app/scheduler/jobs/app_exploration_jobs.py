from threading import Thread

from app.db.session import SessionLocal
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.app_exploration_planner_service import AppExplorationPlannerService


def plan_device_step(task_id,revision):
    def run():
        with SessionLocal() as db:
            AppExplorationPlannerService(SqlAlchemyResourceRepository(db)).plan(task_id,revision)
    Thread(target=run,daemon=True,name=f'app-plan-{task_id}').start()
