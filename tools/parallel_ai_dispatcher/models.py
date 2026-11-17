"""Validated contracts for the provider-neutral parallel AI task queue."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import PurePosixPath
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


KNOWN_SKILLS = frozenset(
    {
        "nivus-project-guide",
        "nivus-ai-dev-workflow",
        "nivus-ai-provider-connectors",
        "nivus-backend-api",
        "nivus-dashboard-ui",
        "nivus-edge-operations",
        "nivus-hardware-telemetry",
        "nivus-home-automation",
        "nivus-local-ai-knowledge",
        "nivus-node-registry",
        "nivus-task-orchestration",
    }
)

_SENSITIVE_PATH_PARTS = frozenset(
    {
        ".env",
        ".git",
        ".venv",
        "secrets",
        "data",
        "logs",
        "node_modules",
        "authorized_keys",
        "known_hosts",
        "id_rsa",
        "id_ed25519",
        "id_ecdsa",
        "id_dsa",
    }
)
_SENSITIVE_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".sqlite", ".sqlite3", ".db", ".log")
_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SECRET_RE = re.compile(
    r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{16,}"
)
_PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")


class TaskStatus(str, Enum):
    PENDING = "pending"
    LEASED = "leased"
    RUNNING = "running"
    RESULT_PENDING_REVIEW = "result_pending_review"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentSpecialty(str, Enum):
    CODING = "coding"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    ORCHESTRATION = "orchestration"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentRegistration(StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    provider: Annotated[str, Field(min_length=1, max_length=80)]
    model: Annotated[str, Field(min_length=1, max_length=120)]
    specialties: list[AgentSpecialty] = Field(default_factory=list, max_length=10)
    skill_ids: list[str] = Field(default_factory=list, max_length=11)
    max_concurrent_tasks: int = Field(default=1, ge=1, le=16)
    backend_type: Annotated[str, Field(default="remote-api", min_length=1, max_length=40)]

    @field_validator("name", "provider", "model", "backend_type")
    @classmethod
    def trim_registration_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("o campo não pode ficar vazio")
        return normalized

    @field_validator("skill_ids")
    @classmethod
    def validate_skill_ids(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("skill_ids não pode conter duplicatas")
        unknown = set(values) - KNOWN_SKILLS
        if unknown:
            raise ValueError(f"skill_ids desconhecidas: {', '.join(sorted(unknown))}")
        return values


class AgentMapping(AgentRegistration):
    agent_id: Annotated[str, Field(pattern=r"^agent-[a-f0-9]{16}$")]


class AgentStatus(AgentMapping):
    is_online: bool
    active_tasks: int = Field(ge=0)


class AgentRegistrationResponse(StrictModel):
    agent: AgentMapping
    agent_token: Annotated[str, Field(min_length=32, max_length=128)]
    token_displayed_once: Literal[True] = True


class TaskPayload(StrictModel):
    issue_number: int = Field(gt=0)
    repository: Annotated[str, Field(min_length=3, max_length=200)]
    title: Annotated[str, Field(min_length=1, max_length=256)]
    body: Annotated[str, Field(min_length=1, max_length=20_000)]
    issue_url: Annotated[str, Field(min_length=1, max_length=500)]
    labels: list[str] = Field(default_factory=list, max_length=50)
    required_specialty: AgentSpecialty | None = None
    required_skills: list[str] = Field(default_factory=list, max_length=11)
    allowed_paths: list[str] = Field(min_length=1, max_length=100)
    human_owner: Annotated[str, Field(min_length=2, max_length=40)]

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title não pode ficar vazio")
        return normalized

    @field_validator("repository")
    @classmethod
    def validate_repository(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository deve usar o formato owner/repository")
        return value

    @field_validator("issue_url")
    @classmethod
    def validate_issue_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "github.com"
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("issue_url deve ser uma URL HTTPS do GitHub")
        return value

    @field_validator("required_skills")
    @classmethod
    def validate_required_skills(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("required_skills não pode conter duplicatas")
        unknown = set(values) - KNOWN_SKILLS
        if unknown:
            raise ValueError(f"skills desconhecidas: {', '.join(sorted(unknown))}")
        return values

    @field_validator("allowed_paths")
    @classmethod
    def validate_allowed_paths(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("allowed_paths não pode conter duplicatas")
        for value in values:
            parts = value.split("/")
            path = PurePosixPath(value)
            folded = [part.casefold() for part in parts]
            if (
                not value
                or value.startswith("/")
                or "\\" in value
                or ":" in value
                or path.as_posix() != value
                or any(part in {"", ".", ".."} for part in parts)
                or any(char in value for char in "*?[]")
                or value.casefold().startswith(".github/workflows/")
                or any(part in _SENSITIVE_PATH_PARTS for part in folded)
                or value.casefold().endswith(_SENSITIVE_SUFFIXES)
            ):
                raise ValueError(f"caminho não permitido: {value}")
        return values


class TaskResult(StrictModel):
    summary: Annotated[str, Field(min_length=1, max_length=4_000)]
    pull_request_url: Annotated[str, Field(min_length=1, max_length=500)]

    @field_validator("pull_request_url")
    @classmethod
    def validate_pull_request_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "github.com"
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or not re.fullmatch(r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pull/[1-9][0-9]*/?", parsed.path)
        ):
            raise ValueError("pull_request_url deve apontar para um PR HTTPS do GitHub")
        return value

    @field_validator("summary")
    @classmethod
    def reject_secret_material(cls, value: str) -> str:
        if _SECRET_RE.search(value) or _PRIVATE_KEY_RE.search(value):
            raise ValueError("summary contém conteúdo semelhante a credencial")
        normalized = value.strip()
        if not normalized:
            raise ValueError("summary não pode ficar vazio")
        return normalized


class TaskState(StrictModel):
    task_id: Annotated[str, Field(pattern=r"^[0-9a-f-]{36}$")]
    payload: TaskPayload
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent_id: str | None = None
    attempt: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1, le=10)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lease_expires_at: datetime | None = None
    result: TaskResult | None = None
    failure_reason: Annotated[str | None, Field(max_length=1_000)] = None


class ClaimedTask(StrictModel):
    task: TaskState
    lease_token: Annotated[str, Field(min_length=32, max_length=128)]


class TaskLeaseRequest(StrictModel):
    lease_token: Annotated[str, Field(min_length=32, max_length=128)]


class TaskResultSubmission(StrictModel):
    lease_token: Annotated[str, Field(min_length=32, max_length=128)]
    result: TaskResult
