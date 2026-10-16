import json


class ExecutionJournal:
    """A crashed execution is uncertain, never a reason to replay device writes."""

    def __init__(self, outbox):
        self.outbox = outbox

    def start(self, task):
        data = task.get("data") or {}
        payload = data.get("payload") or {}
        context = payload.get("context") or {}
        records = [{"name": case.get("name") or "Interrupted execution", "project_id": case.get("project_id"), "status": "failed", "data": {"case_type": payload.get("case_type"), "case_id": case.get("id"), "run_id": context.get("run_id"), "scenario_id": context.get("scenario_id"), "outcome_unknown": True}} for case in payload.get("cases", [])]
        error = "Agent 在执行完成确认前退出，操作结果未知；请人工确认设备状态，不要自动重放"
        report = {"status": "failed", "result": {"records": records, "failed_count": len(records), "outcome_unknown": True}, "error": error, "lease_token": data.get("lease_token")}
        path = self._path(task["id"])
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)

    def complete(self, task_id):
        self._path(task_id).unlink(missing_ok=True)

    def recover(self):
        for path in self.outbox.path.glob("*.inflight"):
            task_id = int(path.stem)
            if not (self.outbox.path / f"{task_id}.json").exists():
                self.outbox.save(task_id, json.loads(path.read_text(encoding="utf-8")))
            path.unlink()

    def _path(self, task_id):
        return self.outbox.path / f"{int(task_id)}.inflight"
