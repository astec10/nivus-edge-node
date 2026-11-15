"""Offline regression tests for the Gemini background interaction adapter."""

from __future__ import annotations

import json
import os
import urllib.error
import unittest
from email.message import Message
from unittest.mock import patch

from tools.ai_executor.gemini_client import API_URL, GeminiAPIError, GeminiClient


def completed_response() -> dict:
    proposal = {
        "summary": "Add a short public note.",
        "changes": [
            {
                "path": "docs/example.md",
                "operation": "create",
                "content": "# Example\n\nPublic synthetic content.\n",
            }
        ],
    }
    return {
        "id": "interaction-123",
        "status": "completed",
        "steps": [
            {
                "type": "model_output",
                "content": [{"type": "text", "text": json.dumps(proposal)}],
            }
        ],
        "usage": {"total_input_tokens": 120, "total_output_tokens": 80},
    }


class FakeHTTPResponse:
    def __init__(self, payload: dict | bytes):
        self.raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, _limit: int) -> bytes:
        return self.raw


class FakeOpener:
    def __init__(self, results: list[dict | bytes | Exception]):
        self.results = list(results)
        self.requests = []

    def open(self, request, timeout: int):
        self.requests.append((request, timeout))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return FakeHTTPResponse(result)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class GeminiClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.budget_env = patch.dict(os.environ, {"NIVUS_AI_BUDGET_MODE": "free-tier"})
        self.budget_env.start()
        self.addCleanup(self.budget_env.stop)

    def test_background_flow_polls_then_deletes_before_returning_proposal(self) -> None:
        opener = FakeOpener(
            [
                {"id": "interaction-123", "status": "in_progress"},
                completed_response(),
                b"",
            ]
        )
        client = GeminiClient(api_key="synthetic-test-key", poll_interval_seconds=1)
        with patch("tools.ai_executor.gemini_client.urllib.request.build_opener", return_value=opener), patch(
            "tools.ai_executor.gemini_client.time.sleep", return_value=None
        ):
            proposal = client.propose_changes(
                task_title="Synthetic documentation task",
                task_description="Add a public note.",
                acceptance_criteria=["The note explains the feature."],
                allowed_paths=["docs/example.md"],
                repository_context="Public synthetic repository context.",
            )

        self.assertEqual(proposal.summary, "Add a short public note.")
        self.assertEqual([request.get_method() for request, _timeout in opener.requests], ["POST", "GET", "DELETE"])
        body = json.loads(opener.requests[0][0].data.decode("utf-8"))
        self.assertTrue(body["background"])
        self.assertTrue(body["store"])
        self.assertNotIn("synthetic-test-key", opener.requests[0][0].data.decode("utf-8"))
        report = client.last_usage_report.to_dict()
        self.assertEqual(report["status"], "proposal_ready")
        self.assertTrue(report["interaction_deleted"])
        self.assertEqual(report["input_tokens"], 120)
        self.assertEqual(report["output_tokens"], 80)

    def test_provider_http_error_has_stable_code_and_no_retry(self) -> None:
        headers = Message()
        opener = FakeOpener([urllib.error.HTTPError(API_URL, 503, "unavailable", headers, None)])
        client = GeminiClient(api_key="synthetic-test-key")
        with patch("tools.ai_executor.gemini_client.urllib.request.build_opener", return_value=opener):
            with self.assertRaises(GeminiAPIError) as caught:
                client.propose_changes(
                    task_title="Synthetic task",
                    task_description="A public test.",
                    acceptance_criteria=["Return a proposal."],
                    allowed_paths=["docs/example.md"],
                    repository_context="Public synthetic context.",
                )

        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(caught.exception.error_code, "provider_http_503")
        self.assertEqual(len(opener.requests), 1)
        self.assertEqual(client.last_usage_report.to_dict()["error_code"], "provider_http_503")

    def test_terminal_provider_failure_is_reported_and_deleted(self) -> None:
        opener = FakeOpener(
            [
                {"id": "interaction-123", "status": "in_progress"},
                {"id": "interaction-123", "status": "failed"},
                b"",  # Best-effort cancellation after the last observed status was in progress.
                b"",  # Delete the stored interaction.
            ]
        )
        client = GeminiClient(api_key="synthetic-test-key", poll_interval_seconds=1)
        with patch("tools.ai_executor.gemini_client.urllib.request.build_opener", return_value=opener), patch(
            "tools.ai_executor.gemini_client.time.sleep", return_value=None
        ):
            with self.assertRaises(GeminiAPIError) as caught:
                client.propose_changes(
                    task_title="Synthetic task",
                    task_description="A public test.",
                    acceptance_criteria=["Return a proposal."],
                    allowed_paths=["docs/example.md"],
                    repository_context="Public synthetic context.",
                )

        self.assertEqual(caught.exception.error_code, "interaction_failed")
        self.assertEqual([request.get_method() for request, _timeout in opener.requests], ["POST", "GET", "POST", "DELETE"])
        report = client.last_usage_report.to_dict()
        self.assertEqual(report["status"], "interaction_error")
        self.assertTrue(report["interaction_deleted"])

    def test_delete_failure_is_visible_in_report_without_logging_response_content(self) -> None:
        headers = Message()
        opener = FakeOpener(
            [
                {"id": "interaction-123", "status": "in_progress"},
                completed_response(),
                urllib.error.HTTPError(f"{API_URL}/interaction-123", 403, "forbidden", headers, None),
            ]
        )
        client = GeminiClient(api_key="synthetic-test-key", poll_interval_seconds=1)
        with patch("tools.ai_executor.gemini_client.urllib.request.build_opener", return_value=opener), patch(
            "tools.ai_executor.gemini_client.time.sleep", return_value=None
        ):
            proposal = client.propose_changes(
                task_title="Synthetic documentation task",
                task_description="Add a public note.",
                acceptance_criteria=["The note explains the feature."],
                allowed_paths=["docs/example.md"],
                repository_context="Public synthetic repository context.",
            )

        self.assertEqual(proposal.summary, "Add a short public note.")
        report = client.last_usage_report.to_dict()
        self.assertFalse(report["interaction_deleted"])
        self.assertEqual(report["status"], "proposal_ready")
        self.assertNotIn("forbidden", json.dumps(report))

    def test_timeout_cancels_and_deletes_without_retrying_post(self) -> None:
        opener = FakeOpener(
            [
                {"id": "interaction-123", "status": "in_progress"},
                {"id": "interaction-123", "status": "in_progress"},
                b"",  # Cancel the still-running interaction.
                b"",  # Delete the stored interaction.
            ]
        )
        clock = FakeClock()
        client = GeminiClient(
            api_key="synthetic-test-key",
            interaction_timeout_seconds=30,
            poll_interval_seconds=20,
        )
        with patch("tools.ai_executor.gemini_client.urllib.request.build_opener", return_value=opener), patch(
            "tools.ai_executor.gemini_client.time.monotonic", side_effect=clock.monotonic
        ), patch("tools.ai_executor.gemini_client.time.sleep", side_effect=clock.sleep):
            with self.assertRaises(GeminiAPIError) as caught:
                client.propose_changes(
                    task_title="Synthetic task",
                    task_description="A public test.",
                    acceptance_criteria=["Return a proposal."],
                    allowed_paths=["docs/example.md"],
                    repository_context="Public synthetic context.",
                )

        self.assertEqual(caught.exception.error_code, "interaction_timeout")
        self.assertEqual([request.get_method() for request, _timeout in opener.requests], ["POST", "GET", "POST", "DELETE"])
        self.assertEqual(sum(request.get_method() == "POST" for request, _timeout in opener.requests), 2)
        report = client.last_usage_report.to_dict()
        self.assertEqual(report["error_code"], "interaction_timeout")
        self.assertTrue(report["interaction_deleted"])


if __name__ == "__main__":
    unittest.main()
