from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


MANIFEST_VERSION = "1.0"
RESULT_VERSION = "1.0"
SUPPORTED_ENGINES = {"playwright", "stagehand", "hybrid"}


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _truthy(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "是"}


@dataclass(frozen=True)
class RunConfig:
    mode: str = "server_headless"
    engine: str = "hybrid"
    headless: bool = True
    slow_mo_ms: int = 0
    action_timeout_ms: int = 5000
    navigation_timeout_ms: int = 30000
    step_wait_ms: int = 0
    screenshot: str = "full_page"
    max_ai_calls_per_case: int = 3
    max_healing_time_ms: int = 30000
    disable_ai_after_429: bool = True
    model_id: int | None = None
    record_video: bool = False

    @classmethod
    def from_execution(cls, execution: dict[str, Any] | None) -> "RunConfig":
        execution = execution if isinstance(execution, dict) else {}
        config = execution.get("config") if isinstance(execution.get("config"), dict) else {}
        engine = str(config.get("engine") or execution.get("engine") or "hybrid").strip().lower()
        if engine not in SUPPORTED_ENGINES:
            raise ValueError(f"Unsupported Web engine: {engine}")
        mode = str(execution.get("mode") or "server_headless")
        default_headless = mode not in {"local_headed"}
        model_id = config.get("model_id")
        try:
            normalized_model_id = int(model_id) if model_id not in (None, "") else None
        except (TypeError, ValueError):
            normalized_model_id = None
        return cls(
            mode=mode,
            engine=engine,
            headless=_truthy(config.get("headless"), default_headless),
            slow_mo_ms=max(0, _int(config.get("slow_mo_ms"), 0 if default_headless else 80)),
            action_timeout_ms=max(1, _int(config.get("action_timeout_ms"), 5000 if default_headless else 8000)),
            navigation_timeout_ms=max(1, _int(config.get("navigation_timeout_ms"), 30000)),
            step_wait_ms=max(0, _int(config.get("step_wait_ms"), 0 if default_headless else 300)),
            screenshot=str(config.get("screenshot") or "full_page"),
            max_ai_calls_per_case=max(0, _int(config.get("max_ai_calls_per_case"), 3)),
            max_healing_time_ms=max(1, _int(config.get("max_healing_time_ms"), 30000)),
            disable_ai_after_429=_truthy(config.get("disable_ai_after_429"), True),
            model_id=normalized_model_id,
            record_video=_truthy(config.get("record_video"), False),
        )


@dataclass(frozen=True)
class CompiledCase:
    id: Any
    name: str
    project_id: Any
    source_id: Any
    target_url: str
    steps: tuple[dict[str, Any], ...]
    assertions: tuple[dict[str, Any], ...]
    auth_context: dict[str, Any]
    raw: dict[str, Any] = field(repr=False)


@dataclass(frozen=True)
class ExecutionPlan:
    manifest_version: str
    result_version: str
    config: RunConfig
    cases: tuple[CompiledCase, ...]
    ai_model: dict[str, Any]
    metadata: dict[str, Any]
