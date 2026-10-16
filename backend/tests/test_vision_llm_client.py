from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from app.utils.vision_llm_client import VisionLlmClient


class ChatCompletionsUrlTest(unittest.TestCase):
    def test_should_keep_full_chat_completions_url(self) -> None:
        url = VisionLlmClient.chat_completions_url("https://api.example.com/v1/chat/completions")
        self.assertEqual("https://api.example.com/v1/chat/completions", url)

    def test_should_append_v1_for_bare_host(self) -> None:
        url = VisionLlmClient.chat_completions_url("https://api.example.com")
        self.assertEqual("https://api.example.com/v1/chat/completions", url)

    def test_should_append_chat_completions_for_versioned_base(self) -> None:
        url = VisionLlmClient.chat_completions_url("https://api.example.com/v1")
        self.assertEqual("https://api.example.com/v1/chat/completions", url)

    def test_should_default_to_openai_when_empty(self) -> None:
        url = VisionLlmClient.chat_completions_url("")
        self.assertEqual("https://api.openai.com/v1/chat/completions", url)


class ParseJsonContentTest(unittest.TestCase):
    def test_should_parse_plain_json_object(self) -> None:
        parsed = VisionLlmClient.parse_json_content('{"features": []}')
        self.assertEqual({"features": []}, parsed)

    def test_should_strip_markdown_fence(self) -> None:
        content = "```json\n{\"features\": [{\"feature\": \"新增\"}]}\n```"
        parsed = VisionLlmClient.parse_json_content(content)
        self.assertEqual([{"feature": "新增"}], parsed["features"])

    def test_should_return_none_for_invalid_json(self) -> None:
        self.assertIsNone(VisionLlmClient.parse_json_content("not json"))

    def test_should_enforce_expected_root_type(self) -> None:
        self.assertIsNone(VisionLlmClient.parse_json_content("[1, 2]"))
        self.assertIsNone(VisionLlmClient.parse_json_content('{"a": 1}', expect_list=True))
        self.assertEqual([1, 2], VisionLlmClient.parse_json_content("[1, 2]", expect_list=True))


class VisionResponseCacheTest(unittest.TestCase):
    def test_should_cache_json_result_by_prompt_and_image_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            client = VisionLlmClient(
                base_url="https://api.example.test/v1",
                api_key="sk-test",
                model="vision-test",
                cache_dir=Path(temp_dir),
            )
            calls: list[str] = []

            def fake_request(system_prompt: str, user_prompt: str, images: list[bytes]) -> str:
                del system_prompt, images
                calls.append(user_prompt)
                return '{"features": [{"feature": "查询"}]}'

            client._request = fake_request  # type: ignore[method-assign]

            first = client.complete_json("system", "user", [b"image"])
            second = client.complete_json("system", "user", [b"image"])

        self.assertEqual(first, second)
        self.assertEqual(1, len(calls))


if __name__ == "__main__":
    unittest.main()
