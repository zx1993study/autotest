from threading import Lock

from app.core.exceptions import BusinessRuleError
from app.scheduler.jobs.thread_jobs import start_daemon_job

_active = set()
_lock = Lock()


def is_source_run_active(run_id):
    with _lock:
        return run_id in _active


def submit_source_run(run_id, cases, platform, base_url):
    with _lock:
        if len(_active) >= 2:
            raise BusinessRuleError("小程序测试队列已满，请稍后重试")
        _active.add(run_id)
    try:
        start_daemon_job(f"miniapp-source-{run_id}", lambda: _execute(run_id, cases, platform, base_url))
    except Exception:
        with _lock:
            _active.discard(run_id)
        raise


def _execute(run_id, cases, platform, base_url):
    from app.db.session import SessionLocal
    from app.repositories.sqlalchemy_resource_repository import (
        SqlAlchemyResourceRepository,
    )
    from app.scheduler.jobs.miniapp_source_executor import execute_source_case
    from app.services.miniapp_source_run_service import MiniappSourceRunService

    with SessionLocal() as db:
        service = MiniappSourceRunService(SqlAlchemyResourceRepository(db))
        try:
            service.update(run_id, {"status": "running"})
            results = [execute_source_case(case, platform, base_url) for case in cases]
            service.finish(run_id, results)
        except Exception:  # noqa: BLE001 - persist safe diagnostics, not credentials or browser payloads.
            db.rollback()
            service.update(run_id, {"status": "interrupted", "data": {"error": "执行服务异常，结果未完成"}})
        finally:
            with _lock:
                _active.discard(run_id)
