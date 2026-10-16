from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from web_automation.cache import cache_failure, cache_update, cached_selector
from web_automation.events import event


AsyncAction = Callable[[], Awaitable[Any]]
CacheCallback = Callable[[int, dict[str, Any]], Any]
InvalidateCallback = Callable[[int], Any]


class AiBudgetExceeded(RuntimeError):
    pass


@dataclass
class AiBudget:
    max_calls: int
    calls: int = 0
    disabled_reason: str = ""

    def consume(self) -> None:
        if self.disabled_reason:
            raise AiBudgetExceeded(self.disabled_reason)
        if self.calls >= self.max_calls:
            raise AiBudgetExceeded(f"AI healing budget exceeded ({self.max_calls} calls per case)")
        self.calls += 1

    def disable(self, reason: str) -> None:
        self.disabled_reason = reason


@dataclass
class StepOutcome:
    source: str
    selector: str = ""
    healed: bool = False
    healing: dict[str, Any] | None = None
    cache_update: dict[str, Any] | None = None
    cache_invalidated: bool = False
    events: list[dict[str, Any]] = field(default_factory=list)


class ActionStrategyPipeline:
    """Execute cache/static/AI strategies without coupling their implementations."""

    def __init__(
        self,
        *,
        engine: str,
        budget: AiBudget,
        target_url: str,
        max_healing_time_ms: int,
        disable_ai_after_429: bool,
        save_cache: CacheCallback | None = None,
        invalidate_cache: InvalidateCallback | None = None,
    ) -> None:
        self.engine = engine
        self.budget = budget
        self.target_url = target_url
        self.max_healing_time_ms = max_healing_time_ms
        self.disable_ai_after_429 = disable_ai_after_429
        self.save_cache = save_cache
        self.invalidate_cache = invalidate_cache
        self.last_events: list[dict[str, Any]] = []

    async def execute(
        self,
        step: dict[str, Any],
        *,
        static_action: AsyncAction,
        cached_action: Callable[[str], Awaitable[Any]],
        ai_action: AsyncAction,
    ) -> StepOutcome:
        events = [event("step_started", step_name=self._name(step), action=step.get("action"))]
        self.last_events = events
        cache_error: Exception | None = None
        static_error: Exception | None = None
        selector = cached_selector(step)

        if selector:
            try:
                await cached_action(selector)
                update = cache_update(step, {"selector": selector}, target_url=self.target_url, source="ai_cache")
                self._save(step, update)
                events.append(event("step_finished", source="ai_cache", step_name=self._name(step)))
                return StepOutcome(source="ai_cache", selector=selector, cache_update=update, events=events)
            except Exception as exc:  # noqa: BLE001 - a stale cache should fall through to deterministic/AI strategies.
                cache_error = exc
                self._invalidate(step)
                events.append(event("cache_invalidated", step_name=self._name(step), error=str(exc)[:300]))

        if self.engine in {"playwright", "hybrid"}:
            try:
                await static_action()
                events.append(event("step_finished", source="playwright", step_name=self._name(step)))
                return StepOutcome(
                    source="playwright",
                    cache_invalidated=cache_error is not None,
                    events=events,
                )
            except Exception as exc:  # noqa: BLE001 - hybrid may recover through Stagehand.
                static_error = exc
                if self.engine == "playwright":
                    events.append(event("step_failed", source="playwright", error=str(exc)[:300]))
                    raise

        try:
            self.budget.consume()
        except AiBudgetExceeded as exc:
            events.append(event("step_failed", source="stagehand", error=str(exc)[:300]))
            raise
        try:
            raw_cache = await asyncio.wait_for(ai_action(), timeout=self.max_healing_time_ms / 1000)
        except Exception as exc:  # noqa: BLE001 - normalize budget behavior around provider failures.
            if self.disable_ai_after_429 and self._is_rate_limit_error(exc):
                self.budget.disable("AI healing disabled after provider rate limit (429)")
            events.append(event("step_failed", source="stagehand", error=str(exc)[:300]))
            if static_error is not None:
                raise RuntimeError(f"Static locator failed: {static_error}; Stagehand healing failed: {exc}") from exc
            raise

        cache = raw_cache if isinstance(raw_cache, dict) else {}
        update = cache_update(step, cache, target_url=self.target_url, source="stagehand")
        self._save(step, update)
        healed = static_error is not None or cache_error is not None
        healing = None
        if healed:
            healing = {
                "step_name": self._name(step),
                "action": str(step.get("action") or ""),
                "source": "stagehand",
                "old_locator": str(step.get("locator") or step.get("playwright_locator") or selector or ""),
                "new_selector": str(update.get("selector") or ""),
                "error": str(static_error or cache_error or "")[:300],
            }
            events.append(event("step_healed", **healing))
        events.append(event("step_finished", source="stagehand", step_name=self._name(step)))
        return StepOutcome(
            source="stagehand",
            selector=str(update.get("selector") or ""),
            healed=healed,
            healing=healing,
            cache_update=update,
            cache_invalidated=cache_error is not None,
            events=events,
        )

    def _save(self, step: dict[str, Any], cache: dict[str, Any]) -> None:
        element_id = self._element_id(step)
        if element_id is not None and self.save_cache is not None:
            self.save_cache(element_id, cache)

    def _invalidate(self, step: dict[str, Any]) -> None:
        element_id = self._element_id(step)
        if element_id is None:
            return
        if self.invalidate_cache is not None:
            self.invalidate_cache(element_id)
        elif self.save_cache is not None:
            self.save_cache(element_id, cache_failure(step))

    def _element_id(self, step: dict[str, Any]) -> int | None:
        try:
            return int(step.get("element_id"))
        except (TypeError, ValueError):
            return None

    def _name(self, step: dict[str, Any]) -> str:
        return str(step.get("name") or step.get("元素名称") or "")

    def _is_rate_limit_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return any(
            marker in message
            for marker in ("429", "too many requests", "ratelimit", "rate limit")
        )
