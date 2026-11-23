"""Mocked contract checks for the OpenRouter Free executor client."""

from __future__ import annotations

import json
import os
import unittest
from email.message import Message
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

from tools.ai_executor import openrouter_client


class FakeResponse(BytesIO):
    def __init__(self, payload: bytes, status: int = 200) -> None:
        super().__init__(payload)
        self.status = status
        self.headers = Message()

    def getcode(self) -> int:
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class FakeOpener:
    def __init__(self, response_or_error) -> None:
        self.response_or_error = response_or_error
        self.calls = 0
        self.request = None
        self.timeout = None

    def open(self, request, timeout):
        self.calls += 1
        self.request = request
        self.timeout = timeout
        if isinstance(self.response_or_error, Exception):
            raise self.response_or_error
        return self.response_or_error


def valid_response(content: str) -> bytes:
    return json.dumps(
        {
            "id": "gen-test-123",
            "choices": [{"finish_reason": "stop", "message": {"content": content}}],
            "usage": {"prompt_tokens": 125, "completion_tokens": 80},
        }
    ).encode("utf-8")


class OpenRouterClientTests(unittest.TestCase):
    def _proposal_arguments(self) -> dict:
        return {
            "task_title": "Synthetic bounded task",
            "task_description": "Change one public documentation file.",
            "acceptance_criteria": ["Only update the allowlisted file."],
            "allowed_paths": ["docs/example.md"],
            "repository_context": "FILE: docs/example.md\nCONTENT:\nPublic text.\n",
        }

    def _client(self, opener: FakeOpener) -> openrouter_client.OpenRouterClient:
        with patch.dict(
            os.environ,
            {"OPENROUTER_API_KEY": "test-key-not-a-real-credential", "NIVUS_AI_BUDGET_MODE": "free-tier"},
        ):
            with patch.object(openrouter_client.urllib.request, "build_opener", return_value=opener):
                return openrouter_client.OpenRouterClient()

    def test_uses_fixed_free_route_and_parses_only_allowlisted_json(self) -> None:
        proposal_json = json.dumps(
            {
                "summary": "Update one file",
                "changes": [
                    {
                        "path": "docs/example.md",
                        "operation": "update",
                        "content": "Updated public text.\n",
                    }
                ],
            }
        )
        opener = FakeOpener(FakeResponse(valid_response(proposal_json)))
        client = self._client(opener)

        result = client.propose_changes(**self._proposal_arguments())

        self.assertEqual(opener.calls, 1)
        self.assertEqual(opener.timeout, 120)
        self.assertEqual(result.changes[0].path, "docs/example.md")
        self.assertEqual(result.usage_report.provider, "openrouter")
        self.assertEqual(result.usage_report.model, "openrouter/free")
        body = json.loads(opener.request.data.decode("utf-8"))
        self.assertEqual(body["model"], "openrouter/free")
        self.assertFalse(body["provider"]["allow_fallbacks"])
        self.assertTrue(body["provider"]["require_parameters"])
        self.assertEqual(body["response_format"]["type"], "json_schema")

    def test_missing_key_fails_before_creating_network_client(self) -> None:
        with patch.dict(os.environ, {"NIVUS_AI_BUDGET_MODE": "free-tier"}, clear=True):
            with patch.object(openrouter_client.urllib.request, "build_opener") as build_opener:
                with self.assertRaisesRegex(ValueError, "OPENROUTER_API_KEY"):
                    openrouter_client.OpenRouterClient()
            build_opener.assert_not_called()

    def test_http_429_is_sanitized_and_never_retried(self) -> None:
        headers = Message()
        headers["Retry-After"] = "60"
        error = HTTPError(
            openrouter_client.API_URL,
            429,
            "Rate limited: sensitive provider text",
            headers,
            BytesIO(b"sensitive response body"),
        )
        opener = FakeOpener(error)
        client = self._client(opener)

        with self.assertRaises(openrouter_client.OpenRouterAPIError) as raised:
            client.propose_changes(**self._proposal_arguments())

        self.assertEqual(opener.calls, 1)
        self.assertEqual(raised.exception.error_code, "provider_http_429")
        self.assertEqual(client.last_usage_report.retry_after, "60")
        self.assertNotIn("sensitive", str(raised.exception))
        self.assertEqual(client.last_usage_report.error_code, "provider_http_429")

    def test_invalid_model_json_stops_without_retry(self) -> None:
        opener = FakeOpener(FakeResponse(valid_response("not valid JSON")))
        client = self._client(opener)

        with self.assertRaises(openrouter_client.OpenRouterAPIError) as raised:
            client.propose_changes(**self._proposal_arguments())

        self.assertEqual(opener.calls, 1)
        self.assertEqual(raised.exception.error_code, "proposal_invalid_json")
        self.assertEqual(client.last_usage_report.error_code, "proposal_invalid_json")

    def test_model_override_cannot_select_paid_route(self) -> None:
        with patch.dict(
            os.environ,
            {"OPENROUTER_API_KEY": "test-key-not-a-real-credential", "NIVUS_AI_BUDGET_MODE": "free-tier"},
        ):
            with patch.object(openrouter_client.urllib.request, "build_opener") as build_opener:
                with self.assertRaisesRegex(ValueError, "restricted"):
                    openrouter_client.OpenRouterClient(model="openai/paid-model")
            build_opener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
