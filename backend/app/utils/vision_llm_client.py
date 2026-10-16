"""Minimal OpenAI-compatible vision chat client.

Used by the Web vision discovery flow to read page screenshots. Calls are
plain HTTP (urllib), mirroring ``AiGenerationService._call_model`` so no new
dependency is introduced. Responses must be JSON; one retry with a stricter
instruction is attempted when the model answers with non-JSON content.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib import error, request

from app.utils.cancellable_model_request import (
    ModelRequestCancelled,
    cancellable_model_response,
)
from app.utils.model_api_request import build_model_body, model_api_url
from app.utils.model_api_response import ModelResponseError, read_model_response


class VisionModelError(RuntimeError):
    """Normalized failure raised by the vision chat client."""


class VisionLlmClient:
    _rate_lock = threading.Lock()
    _last_request_at = 0.0

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        api_protocol: str = "chat_completions",
        reasoning_effort: str | None = None,
        timeout_sec: int | None = 120,
        temperature: float = 0.2,
        cache_dir: str | Path | None = None,
        cache_enabled: bool = True,
        min_interval_ms: int = 0,
        rate_limit_retries: int = 3,
        rate_limit_backoff_ms: int = 2000,
    ) -> None:
        self.api_url = model_api_url(base_url, api_protocol)
        self.api_protocol = api_protocol
        self.reasoning_effort = reasoning_effort
        self.api_key = api_key
        self.model = model
        self.timeout_sec = timeout_sec
        self.temperature = temperature
        self.cache_dir = Path(cache_dir) if cache_dir and cache_enabled else None
        self.min_interval_sec = max(0, min_interval_ms) / 1000
        self.rate_limit_retries = max(0, rate_limit_retries)
        self.rate_limit_backoff_sec = max(0.2, rate_limit_backoff_ms / 1000)
        self.requests_made = 0
        self.cache_hits = 0
        self.cancel_check: Callable[[], bool] | None = None

    def check_cancelled(self) -> None:
        if self.cancel_check and self.cancel_check():
            raise ModelRequestCancelled("用户已中止 AI 分析")

    def _pause(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.check_cancelled()
            time.sleep(min(0.25, max(0, deadline - time.monotonic())))

    @staticmethod
    def chat_completions_url(base_url: str) -> str:
        return model_api_url(base_url, "chat_completions")

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        images: list[bytes],
        *,
        expect_list: bool = False,
    ) -> Any:
        self.check_cancelled()
        cache_key = self._cache_key(system_prompt, user_prompt, images, expect_list)
        cached = self._read_cache(cache_key)
        if cached is not None:
            self.cache_hits += 1
            return cached
        content = self._request(system_prompt, user_prompt, images)
        self.check_cancelled()
        parsed = self.parse_json_content(content, expect_list=expect_list)
        if parsed is not None:
            self._write_cache(cache_key, parsed)
            return parsed
        retry_prompt = f"{user_prompt}\n\n注意：只输出合法 JSON，不要输出任何解释或 Markdown 标记。"
        content = self._request(system_prompt, retry_prompt, images)
        self.check_cancelled()
        parsed = self.parse_json_content(content, expect_list=expect_list)
        if parsed is None:
            raise VisionModelError("视觉模型未返回合法 JSON")
        self._write_cache(cache_key, parsed)
        return parsed

    def _request(self, system_prompt: str, user_prompt: str, images: list[bytes]) -> str:
        user_content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
        for image in images:
            encoded = base64.b64encode(image).decode("ascii")
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}})
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": self.temperature,
        }
        body = build_model_body(body, self.api_protocol, self.reasoning_effort)
        req = request.Request(
            self.api_url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream" if self.api_protocol == "responses" else "application/json",
            },
        )
        for attempt in range(self.rate_limit_retries + 1):
            self.check_cancelled()
            self._throttle()
            try:
                self.requests_made += 1
                if self.timeout_sec is None:
                    response_json = cancellable_model_response(req, self.api_protocol, self.cancel_check)
                else:
                    with request.urlopen(req, timeout=self.timeout_sec) as response:
                        response_json = read_model_response(response, self.api_protocol, timeout_sec=self.timeout_sec)
                break
            except TimeoutError as exc:
                raise VisionModelError(f"视觉模型响应超时，已等待 {self.timeout_sec} 秒") from exc
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore").replace(self.api_key, "[redacted]")[:500]
                if self._retryable_status(exc.code) and attempt < self.rate_limit_retries:
                    self._pause(self._retry_delay(exc, attempt))
                    continue
                prefix = "视觉模型触发限流" if exc.code == 429 else "视觉模型调用失败"
                raise VisionModelError(f"{prefix}: HTTP {exc.code}，已重试 {attempt} 次：{detail}") from exc
            except error.URLError as exc:
                raise VisionModelError(f"视觉模型连接失败: {exc.reason}") from exc
            except ModelResponseError as exc:
                detail = str(exc).replace(self.api_key, "[redacted]")
                if "returned HTML" in detail:
                    detail = f"视觉模型接口返回了网页内容，请检查接口地址：{self.api_url}"
                raise VisionModelError(detail) from exc
        try:
            content = response_json["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise VisionModelError("视觉模型响应格式不正确") from exc
        if not isinstance(content, str):
            raise VisionModelError("视觉模型响应内容不是文本")
        return content

    def _throttle(self) -> None:
        if self.min_interval_sec <= 0:
            return
        with self._rate_lock:
            now = time.monotonic()
            wait_sec = self._last_request_at + self.min_interval_sec - now
            if wait_sec > 0:
                self._pause(wait_sec)
            type(self)._last_request_at = time.monotonic()

    def _retry_delay(self, exc: error.HTTPError, attempt: int) -> float:
        retry_after = str(exc.headers.get("Retry-After") or "").strip()
        if retry_after.isdigit():
            return min(60.0, max(0.2, float(retry_after)))
        return min(60.0, self.rate_limit_backoff_sec * (2**attempt))

    def _retryable_status(self, status_code: int) -> bool:
        return status_code == 429 or status_code in {408, 500, 502, 503, 504}

    def _cache_key(
        self,
        system_prompt: str,
        user_prompt: str,
        images: list[bytes],
        expect_list: bool,
    ) -> str:
        digest = hashlib.sha256()
        for value in (self.api_url, self.api_protocol, self.model, self.reasoning_effort or "", str(expect_list), system_prompt, user_prompt):
            digest.update(value.encode("utf-8"))
            digest.update(b"\0")
        for image in images:
            digest.update(hashlib.sha256(image).digest())
        return digest.hexdigest()

    def _read_cache(self, cache_key: str) -> Any | None:
        if self.cache_dir is None:
            return None
        path = self.cache_dir / f"{cache_key}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _write_cache(self, cache_key: str, parsed: Any) -> None:
        if self.cache_dir is None:
            return
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            path = self.cache_dir / f"{cache_key}.json"
            path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            return

    @staticmethod
    def parse_json_content(content: str, *, expect_list: bool = False) -> Any | None:
        text = content.strip()
        fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
        if fenced:
            text = fenced.group(1).strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None
        if expect_list and not isinstance(parsed, list):
            return None
        if not expect_list and not isinstance(parsed, dict):
            return None
        return parsed


def load_image_bytes(path: str | Path) -> bytes:
    return Path(path).read_bytes()
