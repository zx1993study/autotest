"""In-process batch jobs; every database writer owns its own session."""

from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Event, Lock

from app.scheduler.jobs.thread_jobs import start_daemon_job
from app.services.api_flow_runner import ApiFlowRunner

_controls: dict[int, Event] = {}
_lock = Lock()


def is_batch_active(batch_id):
    with _lock:
        return batch_id in _controls


def cancel_batch(batch_id):
    with _lock:
        event = _controls.get(batch_id)
        if event:
            event.set()
        return bool(event)


def submit_api_flow_batch(batch_id, snapshots, concurrency):
    event = Event()
    with _lock:
        _controls[batch_id] = event
    start_daemon_job(f"api-flow-{batch_id}", lambda: _execute_batch(batch_id, snapshots, concurrency, event))


def _execute_batch(batch_id, snapshots, concurrency, event):
    from app.db.session import SessionLocal
    from app.repositories.sqlalchemy_resource_repository import (
        SqlAlchemyResourceRepository,
    )
    from app.services.api_flow_run_service import ApiFlowRunService

    db = SessionLocal()
    service = ApiFlowRunService(SqlAlchemyResourceRepository(db))
    try:
        service.mark_running(batch_id)
        updates = Queue()
        remaining = len(snapshots)
        with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix=f"flow-{batch_id}") as pool:
            for snapshot in snapshots:
                pool.submit(_run_scenario, snapshot, event, updates)
            while remaining:
                result = updates.get()
                service.save_result(batch_id, result)
                if result["status"] != "running":
                    remaining -= 1
        service.finish(batch_id)
    except Exception:  # noqa: BLE001 - persist an interrupted status at the job boundary.
        db.rollback()
        service.interrupt(batch_id)
    finally:
        db.close()
        with _lock:
            _controls.pop(batch_id, None)


def _run_scenario(snapshot, event, updates):
    try:
        result = ApiFlowRunner(snapshot, event, updates.put).run()
    except Exception:  # noqa: BLE001 - one scenario must not abort other scenarios.
        result = {"scenario_id": snapshot["scenario"]["id"], "name": snapshot["scenario"]["name"],
                  "status": "failed", "error": "场景执行器异常", "nodes": []}
    updates.put(result)
