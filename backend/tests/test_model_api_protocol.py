import io
import json
import unittest
from unittest.mock import patch

from app.utils.model_api_request import build_model_body, model_api_url, model_protocol
from app.utils.model_api_response import (
    ModelResponseError,
    read_model_response,
    responses_to_chat,
)


def completed_response(text='{"status":"ok"}'):
    return {
        "id": "response-test", "model": "test-model", "status": "completed",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
        "usage": {"input_tokens": 3, "output_tokens": 4, "total_tokens": 7},
    }


class ModelHttpResponse(io.BytesIO):
    def __init__(self, value=None, *, events=None):
        if events is None:
            raw = json.dumps(value).encode()
            self.headers = {"Content-Type": "application/json"}
        else:
            raw = b"".join(b"data: " + json.dumps(event).encode() + b"\n\n" for event in events)
            self.headers = {"Content-Type": "text/event-stream; charset=utf-8"}
        super().__init__(raw)


class ModelApiProtocolTest(unittest.TestCase):
    def test_urls_preserve_explicit_paths_and_responses_base(self):
        cases = [
            ("https://example.test", "chat_completions", "https://example.test/v1/chat/completions"),
            ("https://example.test/api/chat/completions", "chat_completions", "https://example.test/api/chat/completions"),
            ("https://example.test", "responses", "https://example.test/responses"),
            ("https://example.test/v1/", "responses", "https://example.test/v1/responses"),
            ("https://example.test/api/responses?version=1", "responses", "https://example.test/api/responses?version=1"),
            ("https://example.test/v1/chat/completions", "responses", "https://example.test/v1/responses"),
        ]
        for base, protocol, expected in cases:
            with self.subTest(base=base, protocol=protocol):
                self.assertEqual(model_api_url(base, protocol), expected)
        self.assertEqual(model_protocol({}), "chat_completions")
        with self.assertRaises(ValueError):
            model_protocol({"api_protocol": "unsupported"})

    def test_responses_text_image_and_reasoning_request(self):
        chat = {"model": "test", "temperature": 0.2, "response_format": {"type": "json_object"}, "messages": [
            {"role": "system", "content": "JSON only"},
            {"role": "user", "content": [{"type": "text", "text": "inspect"}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}}]},
        ]}
        body = build_model_body(chat, "responses", "low")
        self.assertTrue(body["stream"])
        self.assertFalse(body["store"])
        self.assertNotIn("messages", body)
        self.assertNotIn("temperature", body)
        self.assertNotIn("response_format", body)
        self.assertEqual(body["reasoning"], {"effort": "low"})
        self.assertEqual(body["input"][0]["content"][1]["type"], "input_image")
        self.assertEqual(build_model_body(chat, "chat_completions"), chat)

    def test_function_tools_results_and_schema_are_translated(self):
        chat = {"model": "test", "tools": [{"type": "function", "function": {"name": "click", "parameters": {"type": "object"}}}],
                "tool_choice": {"type": "function", "function": {"name": "click"}}, "max_tokens": 20,
                "response_format": {"type": "json_schema", "json_schema": {"name": "result", "schema": {"type": "object"}}},
                "messages": [{"role": "assistant", "tool_calls": [{"id": "call-1", "type": "function", "function": {"name": "click", "arguments": "{}"}}]},
                             {"role": "tool", "tool_call_id": "call-1", "content": "done"}]}
        body = build_model_body(chat, "responses")
        self.assertEqual(body["tools"][0]["name"], "click")
        self.assertEqual(body["tool_choice"], {"type": "function", "name": "click"})
        self.assertEqual(body["input"][0]["type"], "function_call")
        self.assertEqual(body["input"][1]["call_id"], "call-1")
        self.assertEqual(body["max_output_tokens"], 20)
        self.assertEqual(body["text"]["format"]["type"], "json_schema")

    def test_completed_sse_and_json_return_internal_chat_shape(self):
        value = completed_response()
        for response in [ModelHttpResponse(value), ModelHttpResponse(events=[{"type": "response.created"}, {"type": "response.completed", "response": value}])]:
            with response:
                result = read_model_response(response, "responses")
            self.assertEqual(result["choices"][0]["message"]["content"], '{"status":"ok"}')
            self.assertEqual(result["usage"]["total_tokens"], 7)

    def test_truncated_sse_does_not_accept_partial_json(self):
        events = [{"type": "response.output_text.delta", "delta": '{"status":"ok"}'}]
        with ModelHttpResponse(events=events) as response, self.assertRaisesRegex(ModelResponseError, "interrupted"):
            read_model_response(response, "responses")

    def test_failed_incomplete_malformed_and_done_only_streams_fail(self):
        for kind in ["error", "response.failed", "response.incomplete"]:
            with ModelHttpResponse(events=[{"type": kind}]) as response, self.assertRaises(ModelResponseError):
                read_model_response(response, "responses")
        for raw in [b"data: broken\n\n", b"data: [DONE]\n\n", b"data: []\n\n"]:
            response = ModelHttpResponse(events=[])
            response.write(raw)
            response.seek(0)
            with response, self.assertRaises(ModelResponseError):
                read_model_response(response, "responses")

    def test_size_limit_and_stream_deadline(self):
        with patch("app.utils.model_api_response.MAX_MODEL_RESPONSE_BYTES", 32):
            with ModelHttpResponse({"text": "x" * 40}) as response, self.assertRaisesRegex(ModelResponseError, "10 MiB"):
                read_model_response(response, "chat_completions")
            with ModelHttpResponse(events=[{"text": "x" * 40}]) as response, self.assertRaisesRegex(ModelResponseError, "10 MiB"):
                read_model_response(response, "responses")
        with ModelHttpResponse(events=[]) as response, patch("app.utils.model_api_response.time.monotonic", side_effect=[0, 2]), self.assertRaises(TimeoutError):
            read_model_response(response, "responses", timeout_sec=1)

    def test_function_response_and_incomplete_json(self):
        value = completed_response()
        value["output"] = [{"type": "function_call", "call_id": "call-1", "name": "click", "arguments": "{}"}]
        result = responses_to_chat(value)
        self.assertEqual(result["choices"][0]["finish_reason"], "tool_calls")
        self.assertEqual(result["choices"][0]["message"]["tool_calls"][0]["id"], "call-1")
        value["status"] = "incomplete"
        with self.assertRaises(ModelResponseError):
            responses_to_chat(value)


if __name__ == "__main__":
    unittest.main()
