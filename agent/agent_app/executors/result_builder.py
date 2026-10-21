from __future__ import annotations

from typing import Any


def build_execution_record(
    case: dict[str, Any],
    execution: dict[str, Any],
    status: str,
    description: str,
    result: dict[str, Any],
    error: str | None,
) -> dict[str, Any]:
    """Build an execution record payload compatible with platform storage."""

    return {
        "name": f"WEB 用例执行 - {case.get('name') or case.get('id')}",
        "project_id": case.get("project_id") or execution.get("project_id"),
        "description": description,
        "status": status,
        "data": {
            "case_id": case.get("id"),
            "case_type": "WEB",
            "mode": execution.get("mode", "local_headed"),
            "node_id": execution.get("node_id"),
            "steps": result.get("steps", []),
            "duration_ms": result.get("duration_ms", 0),
            "url": result.get("url", ""),
            "step_count": result.get("step_count", 0),
            "screenshots": result.get("screenshots", []),
            "screenshot_file": result.get("screenshot_file"),
            "screenshot_error": result.get("screenshot_error"),
            "cookies": result.get("cookies", []),
            "storage_state": result.get("storage_state", {}),
            "engine": result.get("engine"),
            "ai_usage": result.get("ai_usage"),
            "healing": result.get("healing", []),
            "events": result.get("events", []),
            "cache_updates": result.get("cache_updates", []),
            "cache_invalidations": result.get("cache_invalidations", []),
            "manifest_version": "1.0",
            "result_version": "1.0",
            "assertions": case.get("assertions") or [],
            "assertion_results": result.get("assertion_results", []),
            "dynamic_values": case.get("_dynamic_values", {}),
            "error": error,
            "agent_result": True,
            **{key: result[key] for key in ('operation_result', 'business_result', 'assertion_count', 'result_label', 'privacy_notice') if key in result},
            **({"video_local_path": result["video_local_path"]} if result.get("video_local_path") else {}),
        },
    }


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the platform execution summary contract."""

    success_count = sum(1 for record in records if record.get("status") == "success")
    failed_count = sum(1 for record in records if record.get("status") == "failed")
    return {
        "total": len(records),
        "success_count": success_count,
        "failed_count": failed_count,
        "queued_count": 0,
        "records": records,
    }
