"""Offline tests for the fixed OpenRouter Free adapter."""

from __future__ import annotations

import io
import json
import os
import urllib.error
import unittest
from email.message import Message
from unittest.mock import patch

from tools.ai_executor.openrouter_client import API_URL, FREE_MODEL, OpenRouterAPIError, OpenRouterClient


class FakeResponse:
    def __init__(self, payload):
        self.raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, _limit):
        return self.raw


class FakeOpener:
    def __init__(self, results):
        self.results = list(results)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return FakeResponse(result)


def completed_response():
    proposal = {
        "summary": "Add a short public note.",
        "changes": [{
            "path": "docs/example.md",
            "operation": "create",
            "content": "# Example\n\nPublic synthetic content.\n",
        }],
    }
    return {
        "model": "provider/example:free",
        "choices": [{"message": {"content": json.dumps(proposal)}}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 80},
    }


class OpenRouterClientTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(
            os.environ,
            {
                "NIVUS_AI_BUDGET_MODE": "free-tier",
                "OPENROUTER_API_KEY": "synthetic-openrouter-key",
            },
            clear=False,
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    def invoke_client(self, client):
        return client.propose_changes(
            task_title="Synthetic documentation task",
            task_description="Add a public note.",
            acceptance_criteria=["The note explains the feature."],
            allowed_paths=["docs/example.md"],
            repository_context="Public synthetic repository context.",
        )

    def call_client(self, opener):
        client = OpenRouterClient()
        proposal = self.invoke_client(client)
        return client, proposal, opener

    def test_sends_only_free_route_and_no_fallback(self):
        opener = FakeOpener([completed_response()])
        with patch("tools.ai_executor.openrouter_client.urllib.request.build_opener", return_value=opener):
            client, proposal, _ = self.call_client(opener)
        self.assertEqual(proposal.summary, "Add a short public note.")
        request, timeout = opener.requests[0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.full_url, API_URL)
        self.assertEqual(body["model"], FREE_MODEL)
        self.assertEqual(body["provider"], {
            "data_collection": "deny",
            "allow_fallbacks": False,
            "require_parameters": True,
        })
        self.assertEqual(len(opener.requests), 1)
        self.assertGreater(timeout, 0)
        self.assertNotIn("synthetic-openrouter-key", request.data.decode("utf-8"))
        report = client.last_usage_report.to_dict()
        self.assertEqual(report["provider"], "openrouter")
        self.assertEqual(report["input_tokens"], 120)
        self.assertFalse({"prompt", "response", "api_key"}.intersection(report))

    def test_provider_http_failure_is_sanitized_and_not_retried(self):
        headers = Message()
        opener = FakeOpener([urllib.error.HTTPError(API_URL, 503, "unavailable", headers, None)])
        with patch("tools.ai_executor.openrouter_client.urllib.request.build_opener", return_value=opener):
            with self.assertRaises(OpenRouterAPIError) as caught:
                self.call_client(opener)
        self.assertEqual(caught.exception.error_code, "provider_http_503")
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(len(opener.requests), 1)

    def test_malformed_output_is_sanitized_and_not_retried(self):
        marker = "synthetic-model-output-marker"
        response = completed_response()
        response["choices"][0]["message"]["content"] = marker
        opener = FakeOpener([response])
        client = OpenRouterClient()
        with patch("tools.ai_executor.openrouter_client.urllib.request.build_opener", return_value=opener):
            with self.assertRaises(OpenRouterAPIError) as caught:
                self.invoke_client(client)
        self.assertTrue(caught.exception.error_code.startswith("proposal_"))
        self.assertEqual(len(opener.requests), 1)
        self.assertNotIn(marker, str(caught.exception))
        report = client.last_usage_report.to_dict()
        self.assertEqual(report["status"], "invalid_model_output")
        self.assertNotIn(marker, json.dumps(report))
        self.assertNotIn("synthetic-openrouter-key", json.dumps(report))

    def test_rate_limit_is_sanitized_and_not_retried(self):
        marker = "synthetic-provider-error-marker"
        headers = Message()
        headers["Retry-After"] = "45"
        error = urllib.error.HTTPError(API_URL, 429, marker, headers, io.BytesIO(marker.encode()))
        opener = FakeOpener([error])
        client = OpenRouterClient()
        with patch("tools.ai_executor.openrouter_client.urllib.request.build_opener", return_value=opener):
            with self.assertRaises(OpenRouterAPIError) as caught:
                self.invoke_client(client)
        self.assertEqual(caught.exception.error_code, "provider_http_429")
        self.assertEqual(caught.exception.status_code, 429)
        self.assertEqual(caught.exception.retry_after, "45")
        self.assertEqual(len(opener.requests), 1)
        self.assertNotIn(marker, str(caught.exception))
        self.assertNotIn(marker, json.dumps(client.last_usage_report.to_dict()))

    def test_network_failure_is_sanitized_and_not_retried(self):
        marker = "synthetic-network-error-marker"
        opener = FakeOpener([urllib.error.URLError(marker)])
        client = OpenRouterClient()
        with patch("tools.ai_executor.openrouter_client.urllib.request.build_opener", return_value=opener):
            with self.assertRaises(OpenRouterAPIError) as caught:
                self.invoke_client(client)
        self.assertEqual(caught.exception.error_code, "network_error")
        self.assertEqual(len(opener.requests), 1)
        self.assertNotIn(marker, str(caught.exception))
        report = client.last_usage_report.to_dict()
        self.assertEqual(report["error_code"], "network_error")
        self.assertNotIn(marker, json.dumps(report))

    def test_missing_key_fails_before_network(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}, clear=False):
            with patch("tools.ai_executor.openrouter_client.urllib.request.build_opener") as network:
                with self.assertRaises(ValueError):
                    OpenRouterClient()
            network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
