from app.schemas.api_report import ApiReportQuery, ApiReportRow
from app.utils.api_report_metadata import inferred_case_field


class ApiReportService:
    """Read execution/scenario summaries, leaving historical evidence in its owner."""

    def __init__(self, repository):
        self.repository = repository

    def list(self, query: ApiReportQuery):
        rows, total = self.repository.api_report_rows(query)
        return [self._row(row).model_dump() for row in rows], total

    @staticmethod
    def _row(row):
        row = dict(row)
        index = row.pop("scene_index")
        row["key"] = f"{row['kind']}:{row['record_id']}:{index}"
        row["passed"] = True if row["status"] == "success" else False if row["status"] == "failed" else None
        at = row["executed_at"]
        row["executed_at"] = at.isoformat() if at else ""
        if row["kind"] == "api":
            row["test_point"] = row["test_point"].removeprefix("API 用例执行 - ")
            if row["field_or_scene"] == "未记录字段":
                row["field_or_scene"] = inferred_case_field(row["test_point"]) or "未记录字段"
        return ApiReportRow.model_validate(row)
