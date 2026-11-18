"""Generate one bounded proposal from an explicitly authorized GitHub issue."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.validate_ai_task import sections, validate
from tools.ai_executor.gemini_client import (
    DEFAULT_MODEL,
    GeminiAPIError,
    GeminiClient,
)


MAX_CONTEXT_FILE_BYTES = 12_000
MAX_CONTEXT_TOTAL_BYTES = 48_000
PROJECT_CONTEXT_PATHS = (
    "AGENTS.md",
    "CONTRIBUTING.md",
    "docs/AI_CONTEXT.md",
    "docs/PROJECT_STATUS.md",
    "docs/MODULE_MAP.md",
    "docs/PROJECT_ROADMAP.md",
    "docs/DECISIONS.md",
)


class WorkerError(RuntimeError):
    """Sanitized executor error intended for CI logs."""


def _field_lines(value: str) -> list[str]:
    result = []
    for line in value.splitlines():
        item = line.strip().strip("` ").strip()
        if item.startswith(("- ", "* ")):
            item = item[2:].strip().strip("` ").strip()
        if item and not item.startswith("```" ):
            result.append(item)
    return result


def _read_issue(issue: dict[str, Any]) -> tuple[dict[str, str], list[str], list[str]]:
    if "pull_request" in issue or issue.get("state") != "open":
        raise WorkerError("input_issue_not_open")
    labels = {
        item.get("name")
        for item in issue.get("labels", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    if not {"ai:queued", "ai:ready"}.issubset(labels):
        raise WorkerError("issue_missing_ai_queue_labels")

    body = issue.get("body")
    if not isinstance(body, str):
        raise WorkerError("issue_body_missing")
    problems = validate(body)
    if problems:
        raise WorkerError("issue_contract_invalid")
    values = sections(body)
    if values.get("External model budget") != "free-tier model call — public/synthetic content only":
        raise WorkerError("issue_does_not_authorize_free_tier")

    allowed_paths = _field_lines(values.get("Allowed paths", ""))
    acceptance = _field_lines(values.get("Acceptance criteria", ""))
    if not allowed_paths or not acceptance:
        raise WorkerError("issue_scope_missing")
    return values, allowed_paths, acceptance


def _safe_existing_file(repo_root: Path, relative_path: str) -> Path:
    rel = PurePosixPath(relative_path)
    if rel.is_absolute() or ".." in rel.parts or "\\" in relative_path:
        raise WorkerError("unsafe_path")
    target = repo_root.joinpath(*rel.parts)
    cursor = repo_root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise WorkerError("symlink_path_blocked")
    resolved = target.resolve(strict=False)
    if repo_root not in resolved.parents:
        raise WorkerError("path_escaped_workspace")
    return target


def _build_repository_context(repo_root: Path, allowed_paths: list[str]) -> tuple[str, dict[str, bool]]:
    parts: list[str] = []
    exists_by_path: dict[str, bool] = {}
    total_bytes = 0
    read_paths = list(dict.fromkeys([*PROJECT_CONTEXT_PATHS, *allowed_paths]))
    for path in read_paths:
        target = _safe_existing_file(repo_root, path)
        exists = target.exists()
        if not exists:
            if path in PROJECT_CONTEXT_PATHS:
                raise WorkerError("required_project_context_missing")
            exists_by_path[path] = False
            parts.append(f"FILE: {path}\nSTATE: not present\n")
            continue
        if not target.is_file():
            raise WorkerError("allowlisted_path_not_file")
        if target.stat().st_size > MAX_CONTEXT_FILE_BYTES:
            if path in PROJECT_CONTEXT_PATHS:
                parts.append(
                    f"FILE: {path}\nSTATE: omitted; exceeds the per-file context limit "
                    f"of {MAX_CONTEXT_FILE_BYTES} bytes\n"
                )
                continue
            raise WorkerError("allowlisted_file_too_large")
        try:
            content = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            raise WorkerError("allowlisted_file_not_utf8") from None
        encoded_size = len(content.encode("utf-8"))
        total_bytes += encoded_size
        if total_bytes > MAX_CONTEXT_TOTAL_BYTES:
            raise WorkerError("repository_context_too_large")
        parts.append(f"FILE: {path}\nSTATE: present\nCONTENT:\n{content}\n")
        if path in allowed_paths:
            exists_by_path[path] = True
    return "\n".join(parts), exists_by_path


def _apply_proposal(repo_root: Path, proposal: Any, allowed_paths: list[str], exists_by_path: dict[str, bool]) -> list[str]:
    allowed = set(allowed_paths)
    prepared: list[tuple[str, Path, Path, str, int]] = []
    for item in proposal.changes:
        if item.path not in allowed:
            raise WorkerError("proposal_path_outside_allowlist")
        target = _safe_existing_file(repo_root, item.path)
        exists_now = target.exists()
        if item.path not in exists_by_path or exists_now != exists_by_path[item.path]:
            raise WorkerError("file_state_changed_during_generation")
        if item.operation == "create" and exists_now:
            raise WorkerError("proposal_create_conflicts_with_existing_file")
        if item.operation == "update" and not exists_now:
            raise WorkerError("proposal_update_target_missing")
        if not isinstance(item.content, str):
            raise WorkerError("proposal_content_invalid")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.nivus-ai.tmp")
        if temporary.exists() or temporary.is_symlink():
            raise WorkerError("temporary_output_path_exists")
        mode = stat.S_IMODE(target.stat().st_mode) if exists_now else 0o644
        prepared.append((item.path, target, temporary, item.content, mode))

    if not prepared:
        raise WorkerError("proposal_has_no_changes")

    staged: list[Path] = []
    try:
        for _path, _target, temporary, content, mode in prepared:
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
            staged.append(temporary)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
            os.chmod(temporary, mode)
        for _path, target, temporary, _content, _mode in prepared:
            os.replace(temporary, target)
    except OSError:
        for temporary in staged:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        raise WorkerError("proposal_write_failed") from None

    return [path for path, _target, _temporary, _content, _mode in prepared]


def _write_report(path: Path | None, report: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def run(issue_file: Path, repo_root: Path, usage_report_path: Path | None) -> int:
    started_at = datetime.now(timezone.utc)
    report: dict[str, Any] = {
        "provider": "google-gemini",
        "model": DEFAULT_MODEL,
        "status": "preflight_failed",
        "budget_mode": os.getenv("NIVUS_AI_BUDGET_MODE", "not_enabled"),
        "started_at_utc": started_at.isoformat(),
        "duration_ms": 0,
        "interaction_id": None,
        "input_tokens": None,
        "output_tokens": None,
        "http_status": None,
        "retry_after": None,
    }
    client: GeminiClient | None = None
    try:
        issue = json.loads(issue_file.read_text(encoding="utf-8"))
        if not isinstance(issue, dict):
            raise WorkerError("issue_payload_invalid")
        values, allowed_paths, acceptance = _read_issue(issue)
        repo_root = repo_root.resolve(strict=True)
        repository_context, exists_by_path = _build_repository_context(repo_root, allowed_paths)
        client = GeminiClient()
        proposal = client.propose_changes(
            task_title=str(issue.get("title", "")),
            task_description="\n\n".join(
                f"{label}: {values.get(label, '')}"
                for label in ("Objective", "Module", "Risk", "Data classification")
            ),
            acceptance_criteria=acceptance,
            allowed_paths=allowed_paths,
            repository_context=repository_context,
        )
        report = {**proposal.usage_report.to_dict(), "worker_status": "proposal_received"}
        changed = _apply_proposal(repo_root, proposal, allowed_paths, exists_by_path)
        report["worker_status"] = "proposal_applied"
        print(f"Proposal prepared for {len(changed)} allowlisted file(s).")
        for item in changed:
            print(f"Changed: {item}")
        return 0
    except (WorkerError, GeminiAPIError, ValueError, OSError, json.JSONDecodeError) as exc:
        if client is not None and client.last_usage_report is not None:
            report = client.last_usage_report.to_dict()
        if isinstance(report, dict):
            report["worker_status"] = "failed"
            if client is None:
                report["status"] = "preflight_failed"
            elif client.last_usage_report is None:
                report["status"] = "worker_failed"
            report["error_code"] = exc.error_code if isinstance(exc, GeminiAPIError) else type(exc).__name__
            if client is None or client.last_usage_report is None:
                report["duration_ms"] = round((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        _write_report(usage_report_path, report)
        code = exc.error_code if isinstance(exc, GeminiAPIError) else str(exc)
        print(f"AI worker stopped safely: {code}", file=sys.stderr)
        return 1
    finally:
        _write_report(usage_report_path, report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue-file", required=True, type=Path)
    parser.add_argument("--repo-root", default=".", type=Path)
    parser.add_argument("--usage-report", type=Path)
    args = parser.parse_args()
    return run(args.issue_file, args.repo_root, args.usage_report)


if __name__ == "__main__":
    raise SystemExit(main())
