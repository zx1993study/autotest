from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime

from pydantic import ValidationError

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.schemas.miniapp_source import SourceCase
from app.services.resource_service import ResourceService


class MiniappSourceRunService(ResourceService):
    """Own source-suite snapshots and reports, never infer UI success from API runs."""

    def __init__(self, repository):
        super().__init__("miniapp_source_runs", repository)

    def create_run(self, payload):
        project = self.repository.get("projects", payload.project_id)
        if not project:
            raise ResourceNotFoundError("项目不存在")
        cases = []
        selected = list(dict.fromkeys(payload.case_ids))
        loaded = {case["id"]: case for case in self.repository.get_many("miniapp_test_cases", selected)}
        for case_id in selected:
            case = loaded.get(case_id)
            if not case or case["project_id"] != payload.project_id:
                raise BusinessRuleError("用例不存在或不属于当前项目")
            if case["status"] != "active" or case["data"].get("execution_engine") != "source_catalog":
                raise BusinessRuleError("请选择启用的源码测试用例")
            try:
                SourceCase.model_validate(case["data"].get("definition"))
            except ValidationError:
                raise BusinessRuleError(f"用例 #{case_id} 的源码定义无效，请先修正配置") from None
            cases.append(deepcopy(case))
        run = self.create({"name": f"小程序源码测试 {datetime.now(UTC).isoformat(timespec='seconds')}",
                           "project_id": payload.project_id, "status": "queued", "data": {
                               "platform": payload.platform, "results": [], "case_count": len(cases)}})
        from app.scheduler.jobs.miniapp_source_jobs import submit_source_run
        try:
            submit_source_run(run["id"], cases, payload.platform, (project.get("data") or {}).get("miniapp_h5_url"))
        except Exception:
            self.update(run["id"], {"status": "interrupted"})
            raise
        return run

    def list_runs(self, project_id):
        rows, _ = self.repository.list(self.table, project_id=project_id, page_size=100)
        return [self._reconcile(row, True) for row in rows]

    def get_run(self, run_id):
        return self._reconcile(self.get(run_id))

    def finish(self, run_id, results):
        row = self.get(run_id)
        counts = dict(Counter(result["status"] for result in results))
        status = "failed" if counts.get("failed") else "blocked" if counts.get("blocked") else "success"
        records = [{"name": f"小程序用例 - {item['name']}", "project_id": row["project_id"], "status": item["status"],
                    "data": {**item, "case_type": "MINIAPP", "source_run_id": run_id, "platform": row["data"]["platform"]}}
                   for item in results]
        # Reports and immutable run snapshots remain separate from editable case definitions.
        self.repository.create_many("execution_records", records)
        return self.update(run_id, {"status": status, "data": {**row["data"], "results": results, "counts": counts,
                                                               "finished_at": datetime.now(UTC).isoformat()}})

    def _reconcile(self, row, summary=False):
        from app.scheduler.jobs.miniapp_source_jobs import is_source_run_active
        if row["status"] in {"queued", "running"} and not is_source_run_active(row["id"]):
            row = self.update(row["id"], {"status": "interrupted", "data": {**row["data"], "error": "执行服务已中断，请重新执行"}})
        if summary:
            row = deepcopy(row)
            row["data"].pop("results", None)
        return row
