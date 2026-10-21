from app.repositories.interfaces import ResourceRepository
from app.schemas.web_execution_summary import (
    WebExecutionSnapshot,
    WebExecutionSummaries,
    WebExecutionSummary,
    WebExecutionSummaryQuery,
)


class WebExecutionSummaryService:
    """Summarize the latest result of each currently associated Web case."""

    def __init__(self, repository: ResourceRepository):
        self.repository = repository

    def summarize(self, query: WebExecutionSummaryQuery) -> WebExecutionSummaries:
        summaries = {item_id: WebExecutionSummary(id=item_id) for item_id in query.ids}
        representatives = {}
        for row in self.repository.web_execution_snapshots(query):
            summary = summaries.get(row[f"{query.scope}_id"])
            if summary is None:
                continue
            status = self._case_status(row)
            summary.total_count += 1
            field = f"{status}_count"
            setattr(summary, field, getattr(summary, field) + 1)
            if row["executed_at"] is not None:
                summary.executed_at = max(summary.executed_at or row["executed_at"], row["executed_at"])
                order = (status == "failed", row["executed_at"], row["record_id"])
                if summary.id not in representatives or order > representatives[summary.id]:
                    representatives[summary.id] = order
                    summary.record_id = row["record_id"]
        for summary in summaries.values():
            summary.status = self._summary_status(summary)
        return WebExecutionSummaries(items=list(summaries.values()))

    @staticmethod
    def _case_status(row: WebExecutionSnapshot) -> str:
        if row["record_id"] is None:
            return "not_run"
        if row["status"] in {"failed", "error", "blocked", "interrupted"} or row["business_result"] == "failed":
            return "failed"
        if row["status"] in {"running", "pending", "queued"}:
            return "running"
        if row["status"] in {"canceled", "cancelled", "skipped"}:
            return "canceled"
        count = row["assertion_count"]
        if row["status"] == "success" and row["business_result"] == "passed" and type(count) is int and count > 0:
            return "success"
        return "unverified"

    @staticmethod
    def _summary_status(summary: WebExecutionSummary) -> str:
        if summary.failed_count:
            return "failed"
        if summary.running_count:
            return "running"
        if not summary.total_count:
            return "empty"
        for status in ("success", "not_run", "unverified", "canceled"):
            if getattr(summary, f"{status}_count") == summary.total_count:
                return status
        return "partial"
