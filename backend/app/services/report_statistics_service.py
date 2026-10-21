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
    "blocked": "阻塞",
    "interrupted": "中断",
}


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

        today = datetime.now().date()
        aggregate = self.repository.report_statistics(project_id, today - timedelta(days=6), today + timedelta(days=1))
        groups = aggregate["execution_groups"]
        case_groups = [self._case_group(table, code, label, aggregate["case_counts"]) for table, code, label in CASE_TABLES]
        status_counts = Counter()
        for group in groups:
            status_counts[group["status"]] += group["total"]
        case_type_counts = self._case_type_distribution(groups)
        success_count = status_counts["success"]
        abnormal_count = status_counts["failed"] + status_counts["error"]
        execution_total = sum(status_counts.values())
        duration_count = sum(group["duration_count"] for group in groups)
        duration_total = sum(group["duration_sum"] for group in groups)

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
                "avg_duration_ms": int(duration_total / duration_count) if duration_count else 0,
            },
            "case_groups": case_groups,
            "status_distribution": self._status_distribution(status_counts, execution_total),
            "case_type_distribution": case_type_counts,
            "trend": self._last_seven_day_trend(aggregate["trend"]),
            "recent_records": [self._recent_record(record) for record in aggregate["recent_records"]],
        }

    def _case_group(self, table: str, code: str, label: str, counts: dict[str, dict[str, int]]) -> dict[str, Any]:
        status_counts = Counter(counts.get(table, {}))
        return {
            "type": code,
            "label": label,
            "total": sum(status_counts.values()),
            "active": status_counts["active"],
            "inactive": sum(count for status, count in status_counts.items() if status != "active"),
        }

    def _case_type_distribution(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        groups: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "success": 0, "abnormal": 0})
        for record in records:
            case_type = record["case_type"]
            status = record["status"]
            groups[case_type]["total"] += record["total"]
            if status == "success":
                groups[case_type]["success"] += record["total"]
            if status in {"failed", "error"}:
                groups[case_type]["abnormal"] += record["total"]
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
        statuses = ("success", "failed", "error", "running", "queued", "blocked", "interrupted", "skipped", "cancelled")
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
            day = record["date"]
            if day not in buckets:
                continue
            status = self._record_status(record)
            buckets[day]["total"] += record["total"]
            if status == "success":
                buckets[day]["success"] += record["total"]
            if status in {"failed", "error"}:
                buckets[day]["abnormal"] += record["total"]
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
