"""Regression checks for the bounded public AI proposal worker."""

from __future__ import annotations

import json
import io
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import redirect_stderr

from scripts.validate_ai_task import runtime_minutes, validate
from tools.ai_executor import openrouter_client, worker
from tools.ai_executor.openrouter_client import ProposedFileChange


SAFE_ISSUE_BODY = """### Objective
Prepare a small public documentation proposal.

### Acceptance criteria
- The worker reads only project context and exact approved files.
- A human reviews the resulting pull request.

### Allowed paths
docs/example.md

### Module
docs and knowledge

### Risk
low

### Data classification
public source code and public documentation

### Maximum runtime in minutes
10

### External model budget
free-tier model call — public/synthetic content only

### Human owner
@maintainer

### Review gate
- [x] I understand that a human must review the PR and approve any production merge/deploy.
"""


def issue_payload(body: str = SAFE_ISSUE_BODY, labels: tuple[str, ...] = ("ai:queued", "ai:ready")) -> dict:
    return {
        "number": 123,
        "title": "Synthetic worker preflight",
        "state": "open",
        "labels": [{"name": name} for name in labels],
        "body": body,
    }


class ValidatorTests(unittest.TestCase):
    def test_accepts_public_task_and_enforces_explicit_model_authorization(self) -> None:
        self.assertEqual(validate(SAFE_ISSUE_BODY, require_free_tier=True), [])
        self.assertEqual(runtime_minutes(SAFE_ISSUE_BODY), 10)

    def test_rejects_runtime_above_enforced_limit(self) -> None:
        body = SAFE_ISSUE_BODY.replace("### Maximum runtime in minutes\n10", "### Maximum runtime in minutes\n16")
        self.assertTrue(any("1 e 15" in problem for problem in validate(body, require_free_tier=True)))

    def test_rejects_workflow_paths_and_duplicates(self) -> None:
        workflow_body = SAFE_ISSUE_BODY.replace("docs/example.md", ".github/workflows/worker.yml")
        duplicate_body = SAFE_ISSUE_BODY.replace("docs/example.md", "docs/example.md\ndocs/example.md")
        self.assertTrue(any("Workflows" in problem for problem in validate(workflow_body, require_free_tier=True)))
        self.assertTrue(any("duplicados" in problem for problem in validate(duplicate_body, require_free_tier=True)))


class WorkerTests(unittest.TestCase):
    def test_worker_requires_both_queue_labels(self) -> None:
        with self.assertRaisesRegex(worker.WorkerError, "issue_missing_ai_queue_labels"):
            worker._read_issue(issue_payload(labels=("ai:queued",)))

    def test_worker_rejects_intake_only_task_for_execution(self) -> None:
        body = SAFE_ISSUE_BODY.replace(
            "free-tier model call — public/synthetic content only",
            "no model call — intake only",
        )
        with self.assertRaisesRegex(worker.WorkerError, "issue_does_not_authorize_free_tier"):
            worker._read_issue(issue_payload(body=body))

    def test_proposal_cannot_write_outside_the_allowlist(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nivus-ai-path-") as tmp:
            root = Path(tmp)
            allowed = root / "docs" / "example.md"
            allowed.parent.mkdir()
            allowed.write_text("before\n", encoding="utf-8")
            proposal = SimpleNamespace(
                changes=(ProposedFileChange("outside.md", "create", "blocked\n"),)
            )
            with self.assertRaisesRegex(worker.WorkerError, "proposal_path_outside_allowlist"):
                worker._apply_proposal(root, proposal, ["docs/example.md"], {"docs/example.md": True})
            self.assertEqual(allowed.read_text(encoding="utf-8"), "before\n")
            self.assertFalse((root / "outside.md").exists())

    def test_update_changes_only_the_allowlisted_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nivus-ai-write-") as tmp:
            root = Path(tmp)
            target = root / "docs" / "example.md"
            target.parent.mkdir()
            target.write_text("before\n", encoding="utf-8")
            proposal = SimpleNamespace(
                changes=(ProposedFileChange("docs/example.md", "update", "after\n"),)
            )
            changed = worker._apply_proposal(root, proposal, ["docs/example.md"], {"docs/example.md": True})
            self.assertEqual(changed, ["docs/example.md"])
            self.assertEqual(target.read_text(encoding="utf-8"), "after\n")

    def test_partial_proposal_write_rolls_back_already_replaced_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nivus-ai-rollback-") as tmp:
            root = Path(tmp)
            first = root / "docs" / "first.md"
            second = root / "docs" / "second.md"
            first.parent.mkdir()
            first.write_text("first before\n", encoding="utf-8")
            second.write_text("second before\n", encoding="utf-8")
            proposal = SimpleNamespace(
                changes=(
                    ProposedFileChange("docs/first.md", "update", "first after\n"),
                    ProposedFileChange("docs/second.md", "update", "second after\n"),
                )
            )
            original_replace = worker.os.replace
            replace_calls = 0

            def fail_second_replace(source, destination):
                nonlocal replace_calls
                replace_calls += 1
                if replace_calls == 2:
                    raise OSError("simulated replacement failure")
                return original_replace(source, destination)

            with patch.object(worker.os, "replace", side_effect=fail_second_replace):
                with self.assertRaisesRegex(worker.WorkerError, "proposal_write_failed"):
                    worker._apply_proposal(
                        root,
                        proposal,
                        ["docs/first.md", "docs/second.md"],
                        {"docs/first.md": True, "docs/second.md": True},
                    )

            self.assertEqual(first.read_text(encoding="utf-8"), "first before\n")
            self.assertEqual(second.read_text(encoding="utf-8"), "second before\n")
            self.assertEqual(list(first.parent.glob(".*.nivus-ai*")), [])


    def test_missing_api_key_fails_before_network_and_report_contains_metadata_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nivus-ai-no-key-") as tmp:
            root = Path(tmp)
            for relative in worker.PROJECT_CONTEXT_PATHS:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("public synthetic context\n", encoding="utf-8")
            target = root / "docs" / "example.md"
            target.write_text("public synthetic source\n", encoding="utf-8")
            issue_file = root / "issue.json"
            issue_file.write_text(json.dumps(issue_payload()), encoding="utf-8")
            usage_file = root / "usage.json"
            with patch.dict(os.environ, {"NIVUS_AI_BUDGET_MODE": "free-tier"}, clear=True):
                with patch.object(openrouter_client.urllib.request, "build_opener") as network:
                    result = worker.run(issue_file, root, usage_file)
                network.assert_not_called()
            self.assertEqual(result, 1)
            report = json.loads(usage_file.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "preflight_failed")
            self.assertEqual(report["worker_status"], "failed")
            self.assertIsNone(report["input_tokens"])
            self.assertIsNone(report["output_tokens"])
            self.assertFalse({"prompt", "response", "api_key", "content"}.intersection(report))

    def test_io_failure_report_and_logs_do_not_echo_local_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nivus-ai-private-path-") as tmp:
            root = Path(tmp)
            issue_file = root / "private-directory" / "missing-issue.json"
            usage_file = root / "usage.json"
            stderr = io.StringIO()
            with patch.object(openrouter_client.urllib.request, "build_opener") as network:
                with redirect_stderr(stderr):
                    result = worker.run(issue_file, root, usage_file)

            network.assert_not_called()
            report = json.loads(usage_file.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertEqual(report["status"], "preflight_failed")
            self.assertEqual(report["error_code"], "worker_io_error")
            self.assertNotIn(str(root), stderr.getvalue())
            self.assertNotIn(str(issue_file), stderr.getvalue())

    def test_provider_error_logs_stable_code_instead_of_none(self) -> None:
        class FailedClient:
            last_usage_report = None

            def __init__(self):
                self.last_usage_report = None

            def propose_changes(self, **_kwargs):
                raise openrouter_client.OpenRouterAPIError(
                    "OpenRouter API returned HTTP 503",
                    error_code="provider_http_503",
                    status_code=503,
                )

        with tempfile.TemporaryDirectory(prefix="nivus-ai-error-code-") as tmp:
            root = Path(tmp)
            for relative in worker.PROJECT_CONTEXT_PATHS:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("public synthetic context\n", encoding="utf-8")
            (root / "docs" / "example.md").write_text("public synthetic source\n", encoding="utf-8")
            issue_file = root / "issue.json"
            issue_file.write_text(json.dumps(issue_payload()), encoding="utf-8")
            usage_file = root / "usage.json"
            stderr = io.StringIO()
            with patch.object(worker, "OpenRouterClient", FailedClient), redirect_stderr(stderr):
                result = worker.run(issue_file, root, usage_file)

            report = json.loads(usage_file.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertEqual(report["error_code"], "provider_http_503")
            self.assertIn("AI worker stopped safely: provider_http_503", stderr.getvalue())
            self.assertNotIn("None", stderr.getvalue())


class WorkflowDispatchTests(unittest.TestCase):
    def test_authorized_intake_uses_one_worker_dispatch_path(self) -> None:
        repository_root = Path(__file__).resolve().parents[2]
        intake = (repository_root / ".github" / "workflows" / "ai-task-intake.yml").read_text(encoding="utf-8")
        worker_workflow = (repository_root / ".github" / "workflows" / "ai-proposal-worker.yml").read_text(encoding="utf-8")

        self.assertIn("ai:ready", intake)
        self.assertNotIn("gh workflow run ai-proposal-worker.yml", intake)
        self.assertNotIn("actions: write", intake)
        self.assertIn("types: [labeled]", worker_workflow)
        self.assertIn("github.event.label.name == 'ai:ready'", worker_workflow)

    def test_failure_cleanup_covers_proposal_ci_and_pr_publication(self) -> None:
        repository_root = Path(__file__).resolve().parents[2]
        worker_workflow = (repository_root / ".github" / "workflows" / "ai-proposal-worker.yml").read_text(encoding="utf-8")
        cleanup = worker_workflow.split("  clear-ready-on-failure:", 1)[1].split("  validate-proposal:", 1)[0]

        self.assertIn("needs: [propose, validate-proposal, open-draft-pr]", cleanup)
        self.assertIn("needs.propose.result == 'failure'", cleanup)
        self.assertIn("needs.validate-proposal.result == 'failure'", cleanup)
        self.assertIn("needs.open-draft-pr.result == 'failure'", cleanup)
        self.assertIn("No automatic retry was started.", cleanup)

    def test_pull_request_runs_mocked_openrouter_tests_without_provider_secret(self) -> None:
        repository_root = Path(__file__).resolve().parents[2]
        worker_workflow = (repository_root / ".github" / "workflows" / "ai-proposal-worker.yml").read_text(encoding="utf-8")
        test_job = worker_workflow.split("  test-openrouter-worker:", 1)[1].split("\n  duplicate_guard:", 1)[0]

        self.assertIn("pull_request:", worker_workflow.split("workflow_dispatch:", 1)[0])
        self.assertIn("python -m unittest tools.ai_executor.test_openrouter_client tools.ai_executor.test_worker", test_job)
        self.assertIn("inputs.reviewed_and_authorized == false", test_job)
        self.assertNotIn("OPENROUTER_API_KEY", test_job)
        self.assertNotIn("secrets.", test_job)


if __name__ == "__main__":
    unittest.main()
