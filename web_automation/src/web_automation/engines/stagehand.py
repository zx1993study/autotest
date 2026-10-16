from __future__ import annotations

import importlib.util
import inspect
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


DEFAULT_STAGEHAND_TIMEOUT_MS = 30000


class StagehandExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class StagehandModelConfig:
    model_name: str
    api_key: str
    base_url: str = ""
    timeout_ms: int = DEFAULT_STAGEHAND_TIMEOUT_MS
    max_retries: int = 0


@dataclass
class ObservedActionCache:
    selector: str
    method: str = ""
    arguments: list[Any] = field(default_factory=list)
    description: str = ""
    model: str = ""
    source_url: str = ""
    observed_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "selector": self.selector,
            "method": self.method,
            "arguments": self.arguments,
            "description": self.description,
            "model": self.model,
            "source_url": self.source_url,
            "observed_at": self.observed_at,
        }


def stagehand_available() -> bool:
    return importlib.util.find_spec("stagehand") is not None


def build_step_instruction(step: dict[str, Any]) -> str:
    action = str(step.get("action") or step.get("交互类型") or "click").lower()
    name = str(step.get("name") or step.get("元素名称") or "").strip()
    description = str(step.get("description") or "").strip()
    value = step.get("value", step.get("元素值", step.get("default_value")))
    target = name or description or "目标元素"
    location = f"（位置说明：{description}）" if description and description != name else ""
    if action in {"fill", "input", "type"}:
        return f"在「{target}」输入框中输入：{'' if value is None else value}{location}"
    if action in {"select", "select_option", "multi_select", "multi-select"}:
        return f"在「{target}」选择「{'' if value is None else value}」{location}"
    if action in {"check", "checkbox"}:
        return f"勾选「{target}」{location}"
    if action == "uncheck":
        return f"取消勾选「{target}」{location}"
    if action in {"dblclick", "double_click"}:
        return f"双击「{target}」{location}"
    return f"点击「{target}」{location}"


class StagehandSession:
    def __init__(
        self,
        model: StagehandModelConfig,
        *,
        headless: bool = True,
        viewport: dict[str, int] | None = None,
    ) -> None:
        self.model = model
        self.headless = headless
        self.viewport = viewport or {"width": 1440, "height": 900}
        self._stagehand: Any = None

    async def __aenter__(self) -> "StagehandSession":
        await self.start()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()

    @property
    def page(self) -> Any:
        if self._stagehand is None:
            raise StagehandExecutionError("Stagehand session is not started")
        return self._stagehand.page

    async def start(self) -> None:
        if not stagehand_available():
            raise StagehandExecutionError("未安装 stagehand，请安装后再使用 AI 执行引擎")
        try:
            self._stagehand = await self._start_sdk()
        except Exception as exc:  # noqa: BLE001 - normalize optional SDK failures.
            raise StagehandExecutionError(f"Stagehand startup failed: {exc}") from exc

    async def _start_sdk(self) -> Any:
        from stagehand import Stagehand, StagehandConfig  # noqa: PLC0415

        values = self._sdk_config_values()
        config = StagehandConfig(**self._supported_kwargs(StagehandConfig, values))
        instance = Stagehand(config)
        await instance.init()
        return instance

    def _sdk_config_values(self) -> dict[str, Any]:
        values: dict[str, Any] = {
            "env": "LOCAL",
            "model_name": self.model.model_name,
            "model_api_key": self.model.api_key,
            "headless": self.headless,
            "verbose": 0,
            "use_api": False,
            "local_browser_launch_options": {
                "headless": self.headless,
                "viewport": self.viewport,
            },
        }
        model_client_options: dict[str, Any] = {
            "num_retries": max(0, self.model.max_retries),
            "request_timeout": max(1, self.model.timeout_ms) / 1000,
        }
        if self.model.base_url:
            model_client_options["api_base"] = self.model.base_url
        values["model_client_options"] = model_client_options
        return values

    async def resolve_and_execute(self, step: dict[str, Any]) -> dict[str, Any]:
        instruction = build_step_instruction(step)
        cache = await self.act_with_observe_cache(instruction)
        return cache.as_dict()

    async def goto(self, url: str, *, timeout_ms: int = DEFAULT_STAGEHAND_TIMEOUT_MS) -> None:
        await self.page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

    async def act(self, instruction: str) -> Any:
        return await self.page.act(instruction)

    async def observe(self, instruction: str) -> list[dict[str, Any]]:
        observations = await self.page.observe(instruction)
        result: list[dict[str, Any]] = []
        for item in observations or []:
            if isinstance(item, dict):
                result.append(item)
            elif hasattr(item, "model_dump"):
                value = item.model_dump(exclude_none=True)
                if isinstance(value, dict):
                    result.append(value)
        return result

    async def extract(self, instruction: str, schema: Any | None = None) -> Any:
        if schema is None:
            return await self.page.extract(instruction)
        return await self.page.extract(instruction, schema=schema)

    async def screenshot(self, path: str, *, full_page: bool = True) -> None:
        await self.page.screenshot(path=path, full_page=full_page)

    async def act_with_observe_cache(self, instruction: str) -> ObservedActionCache:
        observations = await self.observe(instruction)
        observed = next(
            (
                item
                for item in observations
                if str(item.get("selector") or "").strip()
            ),
            None,
        )
        if observed is None:
            raise StagehandExecutionError(f"Stagehand could not resolve target: {instruction}")
        await self.page.act(observed)
        return ObservedActionCache(
            selector=str(observed.get("selector") or ""),
            method=str(observed.get("method") or ""),
            arguments=list(observed.get("arguments") or []),
            description=str(observed.get("description") or ""),
            model=self.model.model_name,
            source_url=str(getattr(self.page, "url", "") or ""),
            observed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

    async def close(self) -> None:
        if self._stagehand is None:
            return
        try:
            await self._stagehand.close()
        finally:
            self._stagehand = None

    def _supported_kwargs(self, target: Any, values: dict[str, Any]) -> dict[str, Any]:
        if hasattr(target, "model_fields"):
            return values
        try:
            signature = inspect.signature(target)
        except (TypeError, ValueError):
            return values
        if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()):
            return values
        return {key: value for key, value in values.items() if key in signature.parameters}
