from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from app.repositories.interfaces import ResourceRepository


CASE_TABLES: tuple[tuple[str, str, str], ...] = (
    ("api_test_cases", "API", "API 用例"),
    ("web_test_cases", "WEB", "Web 用例"),
    ("app_test_cases", "APP", "App 用例"),
    ("miniapp_test_cases", "MINIAPP", "小程序用例"),
)

STATUS_LABELS: dict[str, str] = {
    "success": "通过",
    "failed": "异常",
    "error": "异常",
    "queued": "排队中",
    "running": "执行中",
}

PAGE_SIZE = 10000


class ReportStatisticsService:
    """Build dashboard-level testing statistics from resource repositories.

    The dashboard intentionally reads through ``ResourceRepository`` instead of
    raw SQL so API/Web/App/Miniapp case storage differences stay hidden below
    the service layer.
    """

    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def overview(self, project_id: int | None = None) -> dict[str, Any]:
        """Return aggregate testing statistics for the report dashboard."""

        records = self._list_all("execution_records", project_id)
        case_groups = [self._case_group(table, code, label, project_id) for table, code, label in CASE_TABLES]
        status_counts = Counter(self._record_status(record) for record in records)
        case_type_counts = self._case_type_distribution(records)
        success_count = status_counts["success"]
        abnormal_count = status_counts["failed"] + status_counts["error"]
        execution_total = len(records)

        return {
            "summary": {
                "case_total": sum(int(group["total"]) for group in case_groups),
                "active_case_total": sum(int(group["active"]) for group in case_groups),
                "execution_total": execution_total,
                "success_count": success_count,
                "abnormal_count": abnormal_count,
                "queued_count": status_counts["queued"],
                "running_count": status_counts["running"],
                "pass_rate": self._percent(success_count, success_count + abnormal_count),
                "avg_duration_ms": self._average_duration(records),
            },
            "case_groups": case_groups,
            "status_distribution": self._status_distribution(status_counts, execution_total),
            "case_type_distribution": case_type_counts,
            "trend": self._last_seven_day_trend(records),
            "recent_records": [self._recent_record(record) for record in records[:8]],
        }

    def _case_group(self, table: str, code: str, label: str, project_id: int | None) -> dict[str, Any]:
        rows = self._list_all(table, project_id)
        status_counts = Counter(str(row.get("status") or "unknown") for row in rows)
        return {
            "type": code,
            "label": label,
            "total": len(rows),
            "active": status_counts["active"],
            "inactive": sum(count for status, count in status_counts.items() if status != "active"),
        }

    def _case_type_distribution(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        groups: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "success": 0, "abnormal": 0})
        for record in records:
            case_type = self._record_case_type(record)
            status = self._record_status(record)
            groups[case_type]["total"] += 1
            if status == "success":
                groups[case_type]["success"] += 1
            if status in {"failed", "error"}:
                groups[case_type]["abnormal"] += 1
        ordered_types = ["API", "WEB", "APP", "MINIAPP", "UNKNOWN"]
        result = []
        for case_type in ordered_types:
            group = groups.get(case_type)
            if not group:
                continue
            measured_total = group["success"] + group["abnormal"]
            result.append(
                {
                    "type": case_type,
                    "label": self._case_type_label(case_type),
                    "total": group["total"],
                    "success": group["success"],
                    "abnormal": group["abnormal"],
                    "pass_rate": self._percent(group["success"], measured_total),
                }
            )
        return result

    def _status_distribution(self, counts: Counter[str], total: int) -> list[dict[str, Any]]:
        statuses = ("success", "failed", "error", "running", "queued")
        return [
            {
                "status": status,
                "label": STATUS_LABELS.get(status, status),
                "count": counts[status],
                "percent": self._percent(counts[status], total),
            }
            for status in statuses
            if counts[status] > 0 or status in {"success", "failed"}
        ]

    def _last_seven_day_trend(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        today = datetime.now().date()
        days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
        buckets = {
            day.isoformat(): {"date": day.isoformat(), "success": 0, "abnormal": 0, "total": 0}
            for day in days
        }
        for record in records:
            day = self._record_day(record)
            if day not in buckets:
                continue
            status = self._record_status(record)
            buckets[day]["total"] += 1
            if status == "success":
                buckets[day]["success"] += 1
            if status in {"failed", "error"}:
                buckets[day]["abnormal"] += 1
        return list(buckets.values())

    def _recent_record(self, record: dict[str, Any]) -> dict[str, Any]:
        data = self._record_data(record)
        return {
            "id": record.get("id"),
            "name": record.get("name") or "-",
            "status": self._record_status(record),
            "status_label": STATUS_LABELS.get(self._record_status(record), self._record_status(record)),
            "case_type": self._record_case_type(record),
            "duration_ms": self._to_int(data.get("duration_ms"), 0),
            "error": str(data.get("error") or record.get("description") or ""),
            "updated_at": record.get("updated_at") or record.get("created_at") or "",
        }

    def _list_all(self, table: str, project_id: int | None) -> list[dict[str, Any]]:
        rows, total = self.repository.list(table, project_id=project_id, page=1, page_size=PAGE_SIZE)
        if total <= len(rows):
            return rows
        all_rows = list(rows)
        page = 2
        while len(all_rows) < total:
            next_rows, _ = self.repository.list(table, project_id=project_id, page=page, page_size=PAGE_SIZE)
            if not next_rows:
                break
            all_rows.extend(next_rows)
            page += 1
        return all_rows

    def _record_status(self, record: dict[str, Any]) -> str:
        status = str(record.get("status") or "").strip().lower()
        return status or "unknown"

    def _record_case_type(self, record: dict[str, Any]) -> str:
        data = self._record_data(record)
        value = str(record.get("case_type") or data.get("case_type") or "").strip().upper()
        return value or "UNKNOWN"

    def _record_data(self, record: dict[str, Any]) -> dict[str, Any]:
        data = record.get("data")
        return data if isinstance(data, dict) else {}

    def _record_day(self, record: dict[str, Any]) -> str:
        value = str(record.get("updated_at") or record.get("created_at") or "")
        if not value:
            return ""
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return value[:10]

    def _average_duration(self, records: list[dict[str, Any]]) -> int:
        durations = [
            value
            for value in (self._to_int(self._record_data(record).get("duration_ms")) for record in records)
            if value is not None and value >= 0
        ]
        return int(sum(durations) / len(durations)) if durations else 0

    def _percent(self, numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round((numerator / denominator) * 100, 1)

    def _to_int(self, value: Any, default: int | None = None) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _case_type_label(self, case_type: str) -> str:
        labels = {
            "API": "API",
            "WEB": "Web",
            "APP": "App",
            "MINIAPP": "小程序",
            "UNKNOWN": "未知",
        }
        return labels.get(case_type, case_type)
