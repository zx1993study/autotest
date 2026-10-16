from typing import Any, TypedDict


class ExecutionStatisticsBucket(TypedDict):
    status: str
    case_type: str
    total: int
    duration_sum: int
    duration_count: int


class TrendStatisticsBucket(TypedDict):
    date: str
    status: str
    total: int


class ReportStatisticsAggregate(TypedDict):
    case_counts: dict[str, dict[str, int]]
    execution_groups: list[ExecutionStatisticsBucket]
    trend: list[TrendStatisticsBucket]
    recent_records: list[dict[str, Any]]
