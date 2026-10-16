"""Translate the shared chat request into the configured provider protocol."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit


def model_protocol(config: dict[str, Any]) -> str:
    protocol = str(config.get("api_protocol") or "chat_completions")
    if protocol not in {"chat_completions", "responses"}:
        raise ValueError("Unsupported AI API protocol")
    return protocol


def model_api_url(base_url: str, protocol: str) -> str:
    base = (base_url or "https://api.openai.com/v1").rstrip("/")
    parts = urlsplit(base)
    path = parts.path.rstrip("/")
    endpoint = "/responses" if protocol == "responses" else "/chat/completions"
    if path.endswith(endpoint):
        return urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))
    for suffix in ("/chat/completions", "/responses"):
        if path.endswith(suffix):
            path = path[:-len(suffix)]
            break
    if protocol == "chat_completions":
        versioned = any(part.startswith("v") and part[1:].isdigit() for part in path.split("/"))
        if not versioned:
            path += "/v1"
    return urlunsplit((parts.scheme, parts.netloc, path + endpoint, parts.query, ""))


def build_model_body(chat_body: dict[str, Any], protocol: str, reasoning_effort: str | None = None) -> dict[str, Any]:
    if protocol == "chat_completions":
        return dict(chat_body)
    instructions: list[str] = []
    inputs: list[dict[str, Any]] = []
    for message in chat_body["messages"]:
        _append_message(message, instructions, inputs)
    body: dict[str, Any] = {
        "model": chat_body["model"], "input": inputs,
        "instructions": "\n\n".join(instructions), "store": False, "stream": True,
    }
    effort = reasoning_effort or chat_body.get("reasoning_effort")
    if effort:
        body["reasoning"] = {"effort": effort}
    maximum = chat_body.get("max_completion_tokens", chat_body.get("max_tokens"))
    if maximum is not None:
        body["max_output_tokens"] = maximum
    _append_tools(chat_body, body)
    response_format = chat_body.get("response_format") or {}
    if response_format.get("type") == "json_schema":
        body["text"] = {"format": {"type": "json_schema", **response_format["json_schema"]}}
    elif response_format.get("type") == "json_object":
        body["instructions"] += "\nReturn only a valid JSON object."
    return body


def _append_message(message: dict[str, Any], instructions: list[str], inputs: list[dict[str, Any]]) -> None:
    role = message.get("role")
    content = message.get("content")
    if role in {"system", "developer"}:
        instructions.append(content if isinstance(content, str) else "\n".join(part["text"] for part in content or []))
        return
    if role == "tool":
        inputs.append({"type": "function_call_output", "call_id": message["tool_call_id"], "output": content or ""})
        return
    if role not in {"user", "assistant"}:
        raise ValueError("Unsupported model message role")
    if content:
        inputs.append({"role": role, "content": _message_content(content, role)})
    for call in message.get("tool_calls") or []:
        if call.get("type") != "function":
            raise ValueError("Unsupported model tool call")
        inputs.append({"type": "function_call", "call_id": call["id"], **call["function"]})


def _message_content(content: Any, role: str) -> list[dict[str, Any]]:
    text_type = "output_text" if role == "assistant" else "input_text"
    if isinstance(content, str):
        return [{"type": text_type, "text": content}]
    converted = []
    for part in content:
        if part.get("type") == "text":
            converted.append({"type": text_type, "text": part["text"]})
        elif part.get("type") == "image_url" and role == "user":
            image = part["image_url"]
            converted.append({"type": "input_image", "image_url": image["url"], "detail": image.get("detail", "auto")})
        else:
            raise ValueError("Unsupported model content type")
    return converted


def _append_tools(chat_body: dict[str, Any], body: dict[str, Any]) -> None:
    if chat_body.get("tools"):
        tools = []
        for tool in chat_body["tools"]:
            if tool.get("type") != "function":
                raise ValueError("Unsupported model tool type")
            tools.append({"type": "function", **tool["function"]})
        body["tools"] = tools
    choice = chat_body.get("tool_choice")
    if choice is not None:
        body["tool_choice"] = {"type": "function", "name": choice["function"]["name"]} if isinstance(choice, dict) else choice
    if "parallel_tool_calls" in chat_body:
        body["parallel_tool_calls"] = chat_body["parallel_tool_calls"]
