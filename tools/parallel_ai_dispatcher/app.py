"""FastAPI boundary for the external Nivus AI development-task queue."""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from pydantic import ValidationError
from redis.asyncio import Redis

from scripts.validate_parallel_ai_task import allowed_paths, sections, selected_skills, validate

from .models import (
    AgentRegistration,
    AgentRegistrationResponse,
    AgentStatus,
    AgentSpecialty,
    ClaimedTask,
    TaskPayload,
    TaskState,
    TaskLeaseRequest,
    TaskResultSubmission,
)
from .redis_dispatcher import RedisDispatcher


LOGGER = logging.getLogger("nivus.parallel_ai_dispatcher")
MAX_WEBHOOK_BODY_BYTES = 1_048_576
QUEUE_LABEL = "parallel-ai:queued"


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"A variável obrigatória {name} não foi configurada")
    return value


def _csv_env(name: str) -> frozenset[str]:
    values = frozenset(item.strip().casefold() for item in _required_env(name).split(",") if item.strip())
    if not values:
        raise RuntimeError(f"A variável {name} precisa conter pelo menos um valor")
    return values


@dataclass(frozen=True)
class Settings:
    redis_url: str
    github_webhook_secret: str
    admin_token: str
    allowed_repositories: frozenset[str]
    allowed_actors: frozenset[str]
    lease_seconds: int
    heartbeat_ttl_seconds: int
    reaper_interval_seconds: int

    @classmethod
    def from_env(cls) -> "Settings":
        webhook_secret = _required_env("GITHUB_WEBHOOK_SECRET")
        admin_token = _required_env("DISPATCHER_ADMIN_TOKEN")
        if len(webhook_secret.encode("utf-8")) < 32:
            raise RuntimeError("GITHUB_WEBHOOK_SECRET precisa ter pelo menos 32 bytes")
        if len(admin_token) < 32:
            raise RuntimeError("DISPATCHER_ADMIN_TOKEN precisa ter pelo menos 32 caracteres")
        try:
            lease_seconds = int(os.environ.get("DISPATCHER_LEASE_SECONDS", "120"))
            heartbeat_ttl_seconds = int(os.environ.get("DISPATCHER_HEARTBEAT_TTL_SECONDS", "90"))
            reaper_interval_seconds = int(os.environ.get("DISPATCHER_REAPER_INTERVAL_SECONDS", "5"))
        except ValueError as exc:
            raise RuntimeError("Configuração inválida de intervalos do dispatcher") from exc
        if not 30 <= lease_seconds <= 3_600:
            raise RuntimeError("DISPATCHER_LEASE_SECONDS deve estar entre 30 e 3600")
        if not 30 <= heartbeat_ttl_seconds <= 600:
            raise RuntimeError("DISPATCHER_HEARTBEAT_TTL_SECONDS deve estar entre 30 e 600")
        if not 1 <= reaper_interval_seconds <= 60:
            raise RuntimeError("DISPATCHER_REAPER_INTERVAL_SECONDS deve estar entre 1 e 60")
        return cls(
            redis_url=_required_env("DISPATCHER_REDIS_URL"),
            github_webhook_secret=webhook_secret,
            admin_token=admin_token,
            allowed_repositories=_csv_env("GITHUB_WEBHOOK_ALLOWED_REPOSITORIES"),
            allowed_actors=_csv_env("GITHUB_WEBHOOK_ALLOWED_ACTORS"),
            lease_seconds=lease_seconds,
            heartbeat_ttl_seconds=heartbeat_ttl_seconds,
            reaper_interval_seconds=reaper_interval_seconds,
        )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _reaper_loop(dispatcher: RedisDispatcher, interval: int) -> None:
    while True:
        try:
            reaped = await dispatcher.reap_expired_leases()
            if reaped:
                LOGGER.warning("Leases expirados recuperados: %s", reaped)
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.error("Falha no ciclo de recuperação de leases")
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(application: FastAPI):
    settings = Settings.from_env()
    client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
    )
    try:
        await client.ping()
    except Exception:
        await client.aclose()
        raise RuntimeError("Não foi possível conectar ao Redis configurado") from None
    application.state.settings = settings
    application.state.redis = client
    application.state.dispatcher = RedisDispatcher(client, lease_seconds=settings.lease_seconds)
    reaper = asyncio.create_task(
        _reaper_loop(application.state.dispatcher, settings.reaper_interval_seconds),
        name="nivus-dispatcher-lease-reaper",
    )
    try:
        yield
    finally:
        reaper.cancel()
        try:
            await reaper
        except asyncio.CancelledError:
            pass
        await client.aclose()


app = FastAPI(
    title="Nivus Parallel AI Dispatcher",
    version="0.1.0",
    description=(
        "Fila externa para tarefas de desenvolvimento do Nivus. Não executa modelos, "
        "não altera o runtime dos nós de borda e não aprova nem mescla pull requests."
    ),
    lifespan=lifespan,
)


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _dispatcher(request: Request) -> RedisDispatcher:
    return request.app.state.dispatcher


def _bearer_value(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, separator, value = authorization.partition(" ")
    if not separator or scheme.casefold() != "bearer" or not value.strip():
        return None
    return value.strip()


async def require_admin(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    supplied = _bearer_value(authorization)
    if supplied is None or not hmac.compare_digest(supplied, _settings(request).admin_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credencial administrativa inválida")


async def require_agent(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    supplied = _bearer_value(authorization)
    if supplied is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credencial de agente ausente")
    agent_id = await _dispatcher(request).authenticate_agent(supplied)
    if agent_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credencial de agente inválida ou revogada")
    return agent_id


AgentAccess = Annotated[str, Depends(require_agent)]


def _verify_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
    if not signature_header or not re.fullmatch(r"sha256=[0-9a-fA-F]{64}", signature_header):
        return False
    digest = hmac.new(secret.encode("utf-8"), body, "sha256").hexdigest()
    return hmac.compare_digest(f"sha256={digest}", signature_header)


async def _read_limited_body(request: Request) -> bytes:
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_WEBHOOK_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Payload excede o limite")
        chunks.append(chunk)
    return b"".join(chunks)


def _issue_to_payload(issue: dict, repository: str) -> TaskPayload:
    raw_body = issue.get("body")
    issue_body = raw_body if isinstance(raw_body, str) else ""
    problems = validate(issue_body, confirmed_public_or_synthetic=True)
    if problems:
        raise HTTPException(
            status_code=422,
            detail={"message": "Issue não atende ao contrato da fila", "problems": problems},
        )
    values = sections(issue_body)
    labels = [
        label.get("name")
        for label in issue.get("labels", [])
        if isinstance(label, dict) and isinstance(label.get("name"), str)
    ]
    specialty: AgentSpecialty | None = None
    for label in labels:
        if label.casefold().startswith("specialty:"):
            raw_value = label.split(":", 1)[1].strip().casefold()
            try:
                specialty = AgentSpecialty(raw_value)
            except ValueError as exc:
                raise HTTPException(
                    status_code=422,
                    detail="A Issue contém uma label specialty desconhecida",
                ) from exc
            break
    owner = values.get("Responsável humano pela revisão", "")
    owner_match = re.search(r"@[A-Za-z0-9-]{1,39}", owner)
    if not owner_match:
        raise HTTPException(status_code=422, detail="Responsável humano inválido")
    try:
        parsed = TaskPayload(
            issue_number=issue["number"],
            repository=repository,
            title=issue.get("title") or "Tarefa paralela de IA",
            body=issue_body,
            issue_url=issue["html_url"],
            labels=labels,
            required_specialty=specialty,
            required_skills=sorted(selected_skills(values.get("Skills/documentação de domínio", ""))),
            allowed_paths=allowed_paths(values.get("Módulo responsável e arquivos permitidos", "")),
            human_owner=owner_match.group(0),
        )
    except (KeyError, TypeError, ValidationError):
        raise HTTPException(status_code=422, detail="Payload de Issue inválido") from None
    issue_url = urlsplit(issue.get("html_url", ""))
    expected_path = f"/{repository}/issues/{issue.get('number', '')}".casefold()
    if issue_url.hostname != "github.com" or issue_url.path.casefold() != expected_path:
        raise HTTPException(status_code=422, detail="URL da Issue não corresponde ao repositório e número recebidos")
    return parsed


@app.get("/healthz", summary="Verifica a conexão com o Redis")
async def healthz(request: Request) -> dict[str, str]:
    try:
        await request.app.state.redis.ping()
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis indisponível") from None
    return {"status": "ok"}


@app.post(
    "/webhooks/github",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Admite Issue enfileirada após validação HMAC-SHA256",
)
async def github_webhook(
    request: Request,
    response: Response,
    signature: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None,
    event: Annotated[str | None, Header(alias="X-GitHub-Event")] = None,
    delivery: Annotated[str | None, Header(alias="X-GitHub-Delivery")] = None,
) -> dict[str, object]:
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_WEBHOOK_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Payload excede o limite")
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().casefold()
    if content_type != "application/json":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Use Content-Type application/json")
    body_bytes = await _read_limited_body(request)
    settings = _settings(request)
    if not _verify_signature(settings.github_webhook_secret, body_bytes, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura GitHub ausente ou inválida")
    if not event or event.casefold() != "issues":
        return {"message": "Evento ignorado", "queued": False}
    if not delivery:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-GitHub-Delivery ausente")
    try:
        delivery_id = str(uuid.UUID(delivery))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-GitHub-Delivery inválido") from exc
    try:
        payload = json.loads(body_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON inválido") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload JSON inválido")
    if payload.get("action") != "labeled":
        return {"message": "Ação ignorada", "queued": False}
    sender = payload.get("sender") or {}
    actor_value = sender.get("login") if isinstance(sender, dict) else None
    actor = actor_value.casefold() if isinstance(actor_value, str) else ""
    if actor not in settings.allowed_actors:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Emissor não autorizado")
    repository_data = payload.get("repository") or {}
    repository_value = repository_data.get("full_name") if isinstance(repository_data, dict) else None
    repository = repository_value.casefold() if isinstance(repository_value, str) else ""
    if repository not in settings.allowed_repositories:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Repositório não autorizado")
    label = payload.get("label") or {}
    label_value = label.get("name") if isinstance(label, dict) else None
    label_name = label_value.casefold() if isinstance(label_value, str) else ""
    if label_name != QUEUE_LABEL:
        return {"message": "Label ignorada", "queued": False}
    issue = payload.get("issue")
    if not isinstance(issue, dict) or "pull_request" in issue or issue.get("state") != "open":
        return {"message": "Evento não representa uma Issue aberta", "queued": False}
    if not isinstance(repository_value, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Repositório ausente")
    task_payload = _issue_to_payload(issue, repository_value)
    task, created = await _dispatcher(request).enqueue(task_payload, delivery_id)
    response.headers["X-Nivus-Task-Id"] = task.task_id
    return {
        "message": "Tarefa admitida na fila" if created else "Evento duplicado; estado existente retornado",
        "queued": created,
        "task_id": task.task_id,
        "status": task.status.value,
    }


@app.post("/admin/agents", response_model=AgentRegistrationResponse, dependencies=[Depends(require_admin)])
async def register_agent(
    registration: AgentRegistration,
    dispatcher: Annotated[RedisDispatcher, Depends(_dispatcher)],
) -> dict[str, object]:
    profile, token = await dispatcher.register_agent(registration)
    return {"agent": profile, "agent_token": token, "token_displayed_once": True}


@app.get("/admin/agents", response_model=list[AgentStatus], dependencies=[Depends(require_admin)])
async def list_agents(dispatcher: Annotated[RedisDispatcher, Depends(_dispatcher)]) -> list[AgentStatus]:
    return await dispatcher.list_agents()


@app.delete("/admin/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
async def revoke_agent(agent_id: str, dispatcher: Annotated[RedisDispatcher, Depends(_dispatcher)]) -> Response:
    if not re.fullmatch(r"agent-[a-f0-9]{16}", agent_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agente não encontrado")
    if not await dispatcher.revoke_agent(agent_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agente não encontrado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/admin/tasks/{task_id}", response_model=TaskState, dependencies=[Depends(require_admin)])
async def get_task(task_id: str, dispatcher: Annotated[RedisDispatcher, Depends(_dispatcher)]) -> TaskState:
    task = await dispatcher.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada")
    return task


@app.post("/agent/heartbeat")
async def agent_heartbeat(
    agent_id: AgentAccess,
    request: Request,
) -> dict[str, object]:
    try:
        await _dispatcher(request).heartbeat(agent_id, ttl_seconds=_settings(request).heartbeat_ttl_seconds)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Agente revogado") from exc
    return {"agent_id": agent_id, "last_seen": _utcnow(), "online_ttl_seconds": _settings(request).heartbeat_ttl_seconds}


@app.post("/agent/tasks/claim", response_model=ClaimedTask | None)
async def claim_task(agent_id: AgentAccess, request: Request) -> ClaimedTask | None:
    claimed = await _dispatcher(request).claim_next(agent_id)
    if claimed is None:
        return None
    return claimed


@app.post("/agent/tasks/{task_id}/start", status_code=status.HTTP_204_NO_CONTENT)
async def start_task(task_id: str, lease: TaskLeaseRequest, agent_id: AgentAccess, request: Request) -> Response:
    if not await _dispatcher(request).start_task(agent_id, task_id, lease.lease_token):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Lease inválido, expirado ou já iniciado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/agent/tasks/{task_id}/renew", response_model=TaskState)
async def renew_task_lease(
    task_id: str,
    lease: TaskLeaseRequest,
    agent_id: AgentAccess,
    request: Request,
) -> TaskState:
    task = await _dispatcher(request).renew_lease(agent_id, task_id, lease.lease_token)
    if task is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Lease inválido ou expirado")
    return task


@app.post("/agent/tasks/{task_id}/result", response_model=TaskState)
async def submit_task_result(
    task_id: str,
    submission: TaskResultSubmission,
    agent_id: AgentAccess,
    request: Request,
) -> TaskState:
    task = await _dispatcher(request).get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada")
    parsed = urlsplit(submission.result.pull_request_url)
    expected_prefix = f"/{task.payload.repository}/pull/".casefold()
    if not parsed.path.casefold().startswith(expected_prefix):
        raise HTTPException(status_code=422, detail="PR não corresponde ao repositório da tarefa")
    updated = await _dispatcher(request).submit_result(agent_id, task_id, submission.lease_token, submission.result)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Lease inválido ou expirado")
    return updated
