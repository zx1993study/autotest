"""Read bounded JSON/SSE responses and preserve the internal chat contract."""
from __future__ import annotations

import json
import time
from typing import Any

MAX_MODEL_RESPONSE_BYTES = 10 * 1024 * 1024


class ModelResponseError(ValueError):
    pass


def read_model_response(response: Any, protocol: str, *, timeout_sec: int | None = 120) -> dict[str, Any]:
    headers = getattr(response, "headers", {})
    content_type = str(headers.get("Content-Type", ""))
    if protocol == "responses" and "text/event-stream" in content_type.lower():
        value = _read_completed_stream(response, time.monotonic() + timeout_sec if timeout_sec is not None else None)
    else:
        raw = response.read(MAX_MODEL_RESPONSE_BYTES + 1)
        if len(raw) > MAX_MODEL_RESPONSE_BYTES:
            raise ModelResponseError("Model response exceeds 10 MiB")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            if raw.lstrip().lower().startswith((b"<!doctype", b"<html")):
                raise ModelResponseError("Model endpoint returned HTML, not JSON") from exc
            raise ModelResponseError("Model endpoint returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise ModelResponseError("Model response must be an object")
    return responses_to_chat(value) if protocol == "responses" else value


def _read_completed_stream(response: Any, deadline: float | None) -> dict[str, Any]:
    for event in _stream_events(response, deadline):
        kind = event.get("type")
        if kind == "response.completed":
            completed = event.get("response")
            if not isinstance(completed, dict):
                raise ModelResponseError("Responses completion is missing its response")
            return completed
        if kind in {"error", "response.failed", "response.incomplete"}:
            detail = event.get("error") or (event.get("response") or {}).get("error") or event.get("message") or kind
            raise ModelResponseError(f"Responses failed: {str(detail)[:500]}")
    raise ModelResponseError("Responses stream interrupted before completion")


def _stream_events(response: Any, deadline: float | None):
    size = 0
    pending: list[bytes] = []
    while True:
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError("Responses stream exceeded request timeout")
        line = response.readline(MAX_MODEL_RESPONSE_BYTES - size + 1)
        size += len(line)
        if size > MAX_MODEL_RESPONSE_BYTES:
            raise ModelResponseError("Model response exceeds 10 MiB")
        if not line or not line.strip():
            if pending:
                data = b"\n".join(pending)
                pending = []
                if data.strip() == b"[DONE]":
                    return
                try:
                    event = json.loads(data)
                except json.JSONDecodeError as exc:
                    raise ModelResponseError("Invalid Responses stream event") from exc
                if not isinstance(event, dict):
                    raise ModelResponseError("Invalid Responses stream event")
                yield event
            if not line:
                return
        elif line.startswith(b"data:"):
            pending.append(line[5:].strip())


def responses_to_chat(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("error") or value.get("status") != "completed":
        detail = value.get("error") or value.get("incomplete_details") or value.get("status")
        raise ModelResponseError(f"Responses did not complete: {str(detail)[:500]}")
    text: list[str] = []
    calls: list[dict[str, Any]] = []
    for item in value.get("output") or []:
        if item.get("type") == "message":
            text.extend(part["text"] for part in item.get("content", []) if part.get("type") == "output_text")
        elif item.get("type") == "function_call":
            calls.append({"id": item["call_id"], "type": "function", "function": {"name": item["name"], "arguments": item["arguments"]}})
    if not text and not calls:
        raise ModelResponseError("Responses returned no text or function calls")
    message: dict[str, Any] = {"role": "assistant", "content": "".join(text) if text else None}
    if calls:
        message["tool_calls"] = calls
    usage = value.get("usage") or {}
    return {
        "id": value.get("id"), "object": "chat.completion", "model": value.get("model"),
        "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if calls else "stop"}],
        "usage": {"prompt_tokens": usage.get("input_tokens", 0), "completion_tokens": usage.get("output_tokens", 0), "total_tokens": usage.get("total_tokens", 0)},
    }
