"""Bounded, audited inference requests using administrator-configured providers.

This is a runtime connector. It never executes model output as code and never
stores prompts or generated content. Provider calls are single-shot and have no
automatic fallback or retry.
"""
from __future__ import annotations

import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from types import SimpleNamespace
from uuid import uuid5
import http.client
import json
import re
import socket
import ssl
import threading
import time
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from urllib.parse import urlsplit

from database import get_db_connection
from services import ai_providers


MAX_OUTPUT_TOKENS = 2048
MAX_PROMPT_UTF8_BYTES = 48_000
MAX_RESPONSE_BYTES = 65_536
INPUT_TOKEN_OVERHEAD = 2048
PRICING_MAX_AGE_DAYS = 90
MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class InferenceRequestError(RuntimeError):
    def __init__(self, code: str, http_status: int, message: str):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.public_message = message


class _CancelledDuringCall(Exception):
    pass


@dataclass
class _RequestContext:
    actor: str
    cancelled: threading.Event = field(default_factory=threading.Event)
    connection: http.client.HTTPConnection | None = None
    request_sent: bool = False


_ACTIVE_LOCK = threading.RLock()
_ACTIVE: dict[str, _RequestContext] = {}
_PARALLEL_LOCK = threading.Lock()
_ACTIVE_PARALLEL_CALLS = 0
_MAX_PARALLEL_CALLS = 3


def _micro_usd(value: float | int | str | Decimal) -> int:
    amount = Decimal(str(value)) * Decimal(1_000_000)
    return int(amount.quantize(Decimal("1"), rounding=ROUND_CEILING))


def _cost_micro_usd(
    input_tokens: int, output_tokens: int, input_rate: float, output_rate: float
) -> int:
    amount = (
        Decimal(input_tokens) * Decimal(str(input_rate))
        + Decimal(output_tokens) * Decimal(str(output_rate))
    ) / Decimal(1_000_000)
    return int((amount * Decimal(1_000_000)).quantize(Decimal("1"), rounding=ROUND_CEILING))


def _budget_micro_usd(value: float | int | str | Decimal) -> int:
    amount = Decimal(str(value)) * Decimal(1_000_000)
    return int(amount.quantize(Decimal("1"), rounding=ROUND_FLOOR))


def _usd(micro_usd: int | None) -> float:
    return round((micro_usd or 0) / 1_000_000, 6)


def _month_start(now: float) -> float:
    value = dt.datetime.fromtimestamp(now, dt.timezone.utc)
    return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp()


def _raise(code: str, http_status: int, message: str) -> None:
    raise InferenceRequestError(code, http_status, message)


def _record_blocked(
    request_id: str,
    task_id: str,
    provider_id: str,
    actor: str,
    model_name: str,
    data_class: str,
    code: str,
) -> None:
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        exists = conn.execute(
            "SELECT 1 FROM ai_execution_requests WHERE request_id=?", (request_id,)
        ).fetchone()
        if exists is None:
            now = time.time()
            conn.execute(
                """INSERT INTO ai_execution_requests
                   (request_id, task_id, provider_id, actor, model_name, data_class,
                    status, reserved_cost_micro_usd, settled_cost_micro_usd,
                    failure_code, created_at, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'blocked', 0, 0, ?, ?, ?)""",
                (request_id, task_id, provider_id, actor, model_name, data_class, code, now, now),
            )
            ai_providers._audit(conn, provider_id, actor, "inference_blocked", code)
            conn.commit()
    finally:
        conn.close()


def _pricing_is_current(connection: dict) -> bool:
    input_rate = connection.get("input_cost_per_million_usd")
    output_rate = connection.get("output_cost_per_million_usd")
    verified = connection.get("pricing_verified_on")
    if input_rate is None or output_rate is None or not verified:
        return False
    try:
        pricing_day = dt.date.fromisoformat(str(verified))
    except ValueError:
        return False
    today = dt.datetime.now(dt.timezone.utc).date()
    return 0 <= (today - pricing_day).days <= PRICING_MAX_AGE_DAYS


def _target(connection: dict) -> dict:
    model = str(connection["model_name"]).strip()
    protocol = connection["protocol"]
    if connection.get("provider_type") == "openrouter" and model != "openrouter/free":
        raise ValueError("OpenRouter Free aceita somente o modelo roteador openrouter/free.")
    if not MODEL_PATTERN.fullmatch(model):
        raise ValueError("O nome do modelo contém caracteres não permitidos.")

    parsed = urlsplit(connection["base_url"])
    if protocol == "openai-compatible":
        suffix = "/chat/completions"
    elif protocol == "anthropic":
        suffix = "/messages"
    elif protocol == "gemini":
        suffix = "/interactions"
    elif protocol == "ollama":
        suffix = "/api/chat"
    else:
        raise ValueError("Protocolo de inferência não suportado.")

    base_path = parsed.path.rstrip("/")
    path = base_path + suffix
    if not path.startswith("/") or "\r" in path or "\n" in path:
        raise ValueError("Caminho de inferência inválido.")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    pinned_address = ai_providers._resolve_pinned_address(
        parsed.hostname or "", port, connection["endpoint_scope"]
    )
    return {
        "scheme": parsed.scheme,
        "hostname": parsed.hostname or "",
        "port": port,
        "path": path,
        "pinned_address": pinned_address,
    }


def _insert_blocked(
    conn,
    request_id: str,
    task_id: str,
    provider_id: str,
    actor: str,
    model_name: str,
    data_class: str,
    code: str,
    now: float,
) -> None:
    conn.execute(
        """INSERT INTO ai_execution_requests
           (request_id, task_id, provider_id, actor, model_name, data_class,
            status, reserved_cost_micro_usd, settled_cost_micro_usd,
            failure_code, created_at, completed_at)
           VALUES (?, ?, ?, ?, ?, ?, 'blocked', 0, 0, ?, ?, ?)""",
        (request_id, task_id, provider_id, actor, model_name, data_class, code, now, now),
    )
    ai_providers._audit(conn, provider_id, actor, "inference_blocked", code)


def _reserve_request(
    payload,
    actor: str,
    connection: dict,
    reserved_cost: int,
) -> int:
    request_id = str(payload.request_id)
    provider_id = payload.provider_id
    task_id = payload.task_id
    now = time.time()
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute(
            "SELECT 1 FROM ai_execution_requests WHERE request_id=?", (request_id,)
        ).fetchone():
            raise InferenceRequestError(
                "duplicate_request", 409,
                "Este identificador de solicitação já foi usado; gere um ID novo para tentar novamente.",
            )

        row = conn.execute(
            "SELECT * FROM ai_provider_connections WHERE id=?", (provider_id,)
        ).fetchone()
        if row is None:
            _insert_blocked(conn, request_id, task_id, provider_id, actor, connection["model_name"],
                            payload.data_class, "provider_not_found", now)
            conn.commit()
            _raise("provider_not_found", 404, "Provedor não encontrado.")
        current = dict(row)
        policy_fields = (
            "model_name", "base_url", "protocol", "endpoint_scope", "auth_method",
            "credential_ciphertext", "enabled", "last_test_status",
            "allowed_data_classes_json", "monthly_budget_usd",
            "input_cost_per_million_usd", "output_cost_per_million_usd",
            "pricing_verified_on", "max_requests_per_hour", "timeout_seconds",
        )
        if any(current.get(name) != connection.get(name) for name in policy_fields):
            _insert_blocked(conn, request_id, task_id, provider_id, actor, connection["model_name"],
                            payload.data_class, "provider_configuration_changed", now)
            conn.commit()
            _raise("provider_configuration_changed", 409,
                   "A configuração do provedor mudou durante a solicitação. Atualize a lista e tente novamente.")
        if not current["enabled"]:
            _insert_blocked(conn, request_id, task_id, provider_id, actor, current["model_name"],
                            payload.data_class, "provider_disabled", now)
            conn.commit()
            _raise("provider_disabled", 409, "O provedor está desabilitado.")
        if current["last_test_status"] != "success":
            _insert_blocked(conn, request_id, task_id, provider_id, actor, current["model_name"],
                            payload.data_class, "provider_not_tested", now)
            conn.commit()
            _raise("provider_not_tested", 409, "Teste e habilite o provedor antes de executar.")
        allowed = json.loads(current["allowed_data_classes_json"])
        if payload.data_class not in allowed:
            _insert_blocked(conn, request_id, task_id, provider_id, actor, current["model_name"],
                            payload.data_class, "data_class_blocked", now)
            conn.commit()
            _raise("data_class_blocked", 403,
                   "A classe de dados desta tarefa não está permitida para o provedor.")
        if current["endpoint_scope"] == "cloud":
            if payload.data_class not in {"public", "synthetic"}:
                _insert_blocked(conn, request_id, task_id, provider_id, actor, current["model_name"],
                                payload.data_class, "cloud_data_class_blocked", now)
                conn.commit()
                _raise("cloud_data_class_blocked", 403,
                       "Provedores de nuvem aceitam somente dados públicos ou sintéticos.")
            if current["monthly_budget_usd"] is None or current["monthly_budget_usd"] <= 0:
                _insert_blocked(conn, request_id, task_id, provider_id, actor, current["model_name"],
                                payload.data_class, "monthly_budget_required", now)
                conn.commit()
                _raise("monthly_budget_required", 409, "Configure um orçamento mensal maior que zero.")
            if not _pricing_is_current(current):
                _insert_blocked(conn, request_id, task_id, provider_id, actor, current["model_name"],
                                payload.data_class, "pricing_required", now)
                conn.commit()
                _raise("pricing_required", 409,
                       "Informe preços por milhão de tokens e confirme a data da tabela de preços.")
            if payload.task_budget_usd <= 0:
                _insert_blocked(conn, request_id, task_id, provider_id, actor, current["model_name"],
                                payload.data_class, "task_budget_required", now)
                conn.commit()
                _raise("task_budget_required", 409, "Defina um orçamento positivo para a tarefa.")

        task_budget_micro = _budget_micro_usd(payload.task_budget_usd)
        task = conn.execute(
            "SELECT actor, budget_micro_usd FROM ai_execution_tasks WHERE task_id=?",
            (task_id,),
        ).fetchone()
        if task is not None and (
            task["actor"] != actor or int(task["budget_micro_usd"]) != task_budget_micro
        ):
            _insert_blocked(conn, request_id, task_id, provider_id, actor, current["model_name"],
                            payload.data_class, "task_policy_mismatch", now)
            conn.commit()
            _raise("task_policy_mismatch", 409,
                   "O identificador da tarefa já está associado a outra pessoa ou orçamento.")

        hourly_probes = conn.execute(
            """SELECT COUNT(*) FROM ai_provider_audit
               WHERE provider_id=? AND action='connection_test_started' AND created_at>=?""",
            (provider_id, now - 3600),
        ).fetchone()[0]
        hourly_inference = conn.execute(
            """SELECT COUNT(*) FROM ai_execution_requests
               WHERE provider_id=? AND status!='blocked' AND created_at>=?""",
            (provider_id, now - 3600),
        ).fetchone()[0]
        if int(hourly_probes) + int(hourly_inference) >= int(current["max_requests_per_hour"]):
            _insert_blocked(conn, request_id, task_id, provider_id, actor, current["model_name"],
                            payload.data_class, "hourly_limit", now)
            conn.commit()
            _raise("hourly_limit", 429, "O limite de solicitações por hora deste provedor foi atingido.")

        month_start = _month_start(now)
        monthly_spent = conn.execute(
            """SELECT COALESCE(SUM(COALESCE(settled_cost_micro_usd,
                                           reserved_cost_micro_usd)), 0)
               FROM ai_execution_requests
               WHERE provider_id=? AND status!='blocked' AND created_at>=?""",
            (provider_id, month_start),
        ).fetchone()[0]
        task_spent = conn.execute(
            """SELECT COALESCE(SUM(COALESCE(settled_cost_micro_usd,
                                           reserved_cost_micro_usd)), 0)
               FROM ai_execution_requests
               WHERE task_id=? AND status!='blocked'""",
            (task_id,),
        ).fetchone()[0]
        monthly_limit = (
            _budget_micro_usd(current["monthly_budget_usd"])
            if current["endpoint_scope"] == "cloud" else None
        )
        if monthly_limit is not None and int(monthly_spent) + reserved_cost > monthly_limit:
            _insert_blocked(conn, request_id, task_id, provider_id, actor, current["model_name"],
                            payload.data_class, "monthly_budget_exceeded", now)
            conn.commit()
            _raise("monthly_budget_exceeded", 409,
                   "A reserva estimada excede o saldo mensal configurado.")
        if int(task_spent) + reserved_cost > task_budget_micro:
            _insert_blocked(conn, request_id, task_id, provider_id, actor, current["model_name"],
                            payload.data_class, "task_budget_exceeded", now)
            conn.commit()
            _raise("task_budget_exceeded", 409,
                   "A reserva estimada excede o orçamento restante desta tarefa.")

        if task is None:
            conn.execute(
                """INSERT INTO ai_execution_tasks (task_id, actor, budget_micro_usd, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (task_id, actor, task_budget_micro, now, now),
            )
        conn.execute(
            """INSERT INTO ai_execution_requests
               (request_id, task_id, provider_id, actor, model_name, data_class,
                status, reserved_cost_micro_usd, settled_cost_micro_usd,
                created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'reserved', ?, NULL, ?)""",
            (request_id, task_id, provider_id, actor, current["model_name"],
             payload.data_class, reserved_cost, now),
        )
        ai_providers._audit(conn, provider_id, actor, "inference_started")
        conn.commit()
        return reserved_cost
    finally:
        conn.close()


def _request_body(
    protocol: str, model: str, prompt: str, max_output_tokens: int,
    provider_type: str | None = None,
) -> dict:
    if protocol == "openai-compatible":
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": max_output_tokens,
            "stream": False,
        }
        if provider_type == "openrouter":
            if model != "openrouter/free":
                raise ValueError("OpenRouter Free aceita somente o modelo roteador openrouter/free.")
            body["provider"] = {
                "data_collection": "deny",
                "allow_fallbacks": False,
            }
        return body
    if protocol == "anthropic":
        return {
            "model": model,
            "max_tokens": max_output_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
    if protocol == "gemini":
        return {
            "model": model,
            "input": prompt,
            "store": False,
            "generation_config": {"max_output_tokens": max_output_tokens},
        }
    if protocol == "ollama":
        return {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": max_output_tokens},
        }
    raise ValueError("Protocolo de inferência não suportado.")


def _provider_output(protocol: str, payload: dict) -> tuple[str, int | None, int | None]:
    input_tokens = output_tokens = None
    usage = payload.get("usage")
    if protocol == "openai-compatible":
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("missing completion")
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, list):
            output = "".join(
                str(item.get("text", "")) for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            )
        else:
            output = content if isinstance(content, str) else ""
        if isinstance(usage, dict):
            input_tokens = usage.get("prompt_tokens")
            output_tokens = usage.get("completion_tokens")
    elif protocol == "anthropic":
        content = payload.get("content")
        output = "".join(
            str(item.get("text", "")) for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ) if isinstance(content, list) else ""
        usage = payload.get("usage")
        if isinstance(usage, dict):
            input_tokens = usage.get("input_tokens")
            output_tokens = usage.get("output_tokens")
    elif protocol == "gemini":
        if payload.get("status") != "completed":
            raise ValueError("interaction not completed")
        steps = payload.get("steps")
        if not isinstance(steps, list):
            raise ValueError("missing interaction steps")
        parts = []
        for step in steps:
            if not isinstance(step, dict) or step.get("type") != "model_output":
                continue
            content = step.get("content")
            if isinstance(content, list):
                parts.extend(
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict) and item.get("type") == "text"
                )
        output = "".join(str(part) for part in parts)
        usage = payload.get("usage")
        if isinstance(usage, dict):
            input_tokens = usage.get("total_input_tokens")
            output_tokens = usage.get("total_output_tokens")
            thought_tokens = usage.get("total_thought_tokens")
            if (
                isinstance(thought_tokens, int) and not isinstance(thought_tokens, bool)
                and thought_tokens >= 0
            ):
                try:
                    reported_output = int(output_tokens)
                except (TypeError, ValueError):
                    reported_output = 0
                if isinstance(output_tokens, bool) or reported_output < 0:
                    reported_output = 0
                output_tokens = reported_output + thought_tokens
    elif protocol == "ollama":
        message = payload.get("message", {})
        output = message.get("content", "") if isinstance(message, dict) else ""
        input_tokens = payload.get("prompt_eval_count")
        output_tokens = payload.get("eval_count")
    else:
        raise ValueError("unsupported protocol")

    if not isinstance(output, str) or not output.strip():
        raise ValueError("empty completion")

    def token_count(value):
        if isinstance(value, bool):
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None

    return output, token_count(input_tokens), token_count(output_tokens)


class _CancellableHTTP(ai_providers._PinnedHTTPConnection):
    def __init__(self, host, address, port, timeout, context):
        super().__init__(host, address, port, timeout)
        self._request_context = context

    def connect(self):
        if self._request_context.cancelled.is_set():
            raise _CancelledDuringCall()
        super().connect()
        with _ACTIVE_LOCK:
            self._request_context.connection = self
            cancelled = self._request_context.cancelled.is_set()
        if cancelled:
            self.close()
            raise _CancelledDuringCall()


class _CancellableHTTPS(ai_providers._PinnedHTTPSConnection):
    def __init__(self, host, address, port, timeout, context):
        super().__init__(host, address, port, timeout)
        self._request_context = context

    def connect(self):
        if self._request_context.cancelled.is_set():
            raise _CancelledDuringCall()
        super().connect()
        with _ACTIVE_LOCK:
            self._request_context.connection = self
            cancelled = self._request_context.cancelled.is_set()
        if cancelled:
            self.close()
            raise _CancelledDuringCall()


def _perform_provider_request(
    connection: dict,
    secret: str | None,
    target: dict,
    prompt: str,
    max_output_tokens: int,
    context: _RequestContext,
    request_id: str,
) -> dict:
    protocol = connection["protocol"]
    body = json.dumps(
        _request_body(
            protocol, connection["model_name"], prompt, max_output_tokens,
            connection.get("provider_type"),
        ),
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    host = target["hostname"]
    port = target["port"]
    timeout = min(max(int(connection["timeout_seconds"]), 2), 60)
    http_connection = (
        _CancellableHTTPS(host, target["pinned_address"], port, timeout, context)
        if target["scheme"] == "https"
        else _CancellableHTTP(host, target["pinned_address"], port, timeout, context)
    )
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Connection": "close",
        "User-Agent": "Nivus-Runtime-Executor/1",
    }
    headers.update(ai_providers._auth_headers(
        connection["auth_method"], secret, protocol
    ))
    try:
        if context.cancelled.is_set():
            raise _CancelledDuringCall()
        conn = get_db_connection()
        try:
            conn.execute(
                """UPDATE ai_execution_requests SET request_sent=1
                   WHERE request_id=? AND status IN ('reserved','cancel_requested')""",
                (request_id,),
            )
            conn.commit()
        finally:
            conn.close()
        with _ACTIVE_LOCK:
            context.request_sent = True
        if context.cancelled.is_set():
            raise _CancelledDuringCall()
        http_connection.request("POST", target["path"], body=body, headers=headers)
        response = http_connection.getresponse()
        content_length = response.getheader("Content-Length")
        if content_length:
            try:
                if int(content_length) > MAX_RESPONSE_BYTES:
                    raise InferenceRequestError(
                        "response_too_large", 502, "A resposta do provedor excedeu o limite permitido."
                    )
            except ValueError:
                raise InferenceRequestError(
                    "invalid_response", 502, "O provedor retornou um cabeçalho inválido."
                )
        if http_connection.sock:
            http_connection.sock.settimeout(timeout)
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise InferenceRequestError(
                "response_too_large", 502, "A resposta do provedor excedeu o limite permitido."
            )
        if 300 <= response.status < 400:
            raise InferenceRequestError(
                "redirect_blocked", 502, "O provedor tentou redirecionar a chamada; o Nivus bloqueou."
            )
        if response.status == 429:
            raise InferenceRequestError(
                "provider_rate_limited", 429, "O provedor limitou a chamada."
            )
        if response.status in (401, 403):
            raise InferenceRequestError(
                "credentials_rejected", 502, "O provedor recusou a credencial cadastrada."
            )
        if not 200 <= response.status < 300:
            raise InferenceRequestError(
                "provider_error", 502, "O provedor respondeu com erro; o corpo foi descartado."
            )
        try:
            document = json.loads(raw.decode("utf-8"))
            output, input_tokens, output_tokens = _provider_output(protocol, document)
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            raise InferenceRequestError(
                "invalid_response", 502, "A resposta do provedor não contém uma conclusão válida."
            )
        if context.cancelled.is_set():
            raise _CancelledDuringCall()
        if secret:
            output = output.replace(secret, "[SEGREDO REMOVIDO]")
        return {
            "output": output,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "http_status": response.status,
        }
    finally:
        http_connection.close()
        with _ACTIVE_LOCK:
            if context.connection is http_connection:
                context.connection = None


def _finish_request(
    request_id: str,
    actor: str,
    status: str,
    reserved_cost: int,
    settled_cost: int,
    input_tokens: int | None,
    output_tokens: int | None,
    duration_ms: int,
    failure_code: str | None,
) -> None:
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT provider_id FROM ai_execution_requests WHERE request_id=? AND actor=?",
            (request_id, actor),
        ).fetchone()
        if row is None:
            conn.rollback()
            return
        conn.execute(
            """UPDATE ai_execution_requests
               SET status=?, reserved_cost_micro_usd=?, settled_cost_micro_usd=?,
                   input_tokens=?, output_tokens=?, duration_ms=?, failure_code=?, completed_at=?
               WHERE request_id=? AND actor=? AND status IN ('reserved','cancel_requested')""",
            (status, reserved_cost, settled_cost, input_tokens, output_tokens,
             duration_ms, failure_code, time.time(), request_id, actor),
        )
        ai_providers._audit(conn, row["provider_id"], actor, "inference_finished", status)
        conn.commit()
    finally:
        conn.close()


def execute(payload, actor: str) -> dict:
    request_id = str(payload.request_id)
    provider_id = payload.provider_id
    context = _RequestContext(actor=actor)
    with _ACTIVE_LOCK:
        if request_id in _ACTIVE:
            _raise("duplicate_request", 409, "Esta solicitação já está em execução.")
        _ACTIVE[request_id] = context

    reserved = 0
    reserved_ok = False
    started = time.monotonic()
    model_name = "unknown"
    try:
        db = get_db_connection()
        try:
            if db.execute(
                "SELECT 1 FROM ai_execution_requests WHERE request_id=?",
                (request_id,),
            ).fetchone():
                _raise(
                    "duplicate_request", 409,
                    "Este identificador de solicitação já foi usado; gere um ID novo para tentar novamente.",
                )
        finally:
            db.close()
        prompt_bytes = payload.prompt.encode("utf-8")
        if not payload.prompt.strip() or len(prompt_bytes) > MAX_PROMPT_UTF8_BYTES:
            _record_blocked(request_id, payload.task_id, provider_id, actor,
                            model_name, payload.data_class, "prompt_size")
            _raise("prompt_size", 422, "A instrução está vazia ou excede 48 KB UTF-8.")
        if payload.max_output_tokens > MAX_OUTPUT_TOKENS:
            _record_blocked(request_id, payload.task_id, provider_id, actor,
                            model_name, payload.data_class, "output_limit")
            _raise("output_limit", 422, "O limite de saída do executor é 2048 tokens.")
        try:
            connection = ai_providers._load_connection(provider_id)
            model_name = connection["model_name"]
        except KeyError:
            _record_blocked(request_id, payload.task_id, provider_id, actor,
                            model_name, payload.data_class, "provider_not_found")
            _raise("provider_not_found", 404, "Provedor não encontrado.")
        if not connection["enabled"]:
            _record_blocked(request_id, payload.task_id, provider_id, actor,
                            model_name, payload.data_class, "provider_disabled")
            _raise("provider_disabled", 409, "O provedor está desabilitado.")
        if connection["last_test_status"] != "success":
            _record_blocked(request_id, payload.task_id, provider_id, actor,
                            model_name, payload.data_class, "provider_not_tested")
            _raise("provider_not_tested", 409, "Teste e habilite o provedor antes de executar.")
        allowed = json.loads(connection["allowed_data_classes_json"])
        if payload.data_class not in allowed:
            _record_blocked(request_id, payload.task_id, provider_id, actor,
                            model_name, payload.data_class, "data_class_blocked")
            _raise("data_class_blocked", 403,
                   "A classe de dados desta tarefa não está permitida para o provedor.")
        if connection["endpoint_scope"] == "cloud":
            if payload.data_class not in {"public", "synthetic"}:
                _record_blocked(request_id, payload.task_id, provider_id, actor,
                                model_name, payload.data_class, "cloud_data_class_blocked")
                _raise("cloud_data_class_blocked", 403,
                       "Provedores de nuvem aceitam somente dados públicos ou sintéticos.")
            if not _pricing_is_current(connection):
                _record_blocked(request_id, payload.task_id, provider_id, actor,
                                model_name, payload.data_class, "pricing_required")
                _raise("pricing_required", 409,
                       "Informe preços por milhão de tokens e confirme a data da tabela de preços.")
            if connection["monthly_budget_usd"] is None or connection["monthly_budget_usd"] <= 0:
                _record_blocked(request_id, payload.task_id, provider_id, actor,
                                model_name, payload.data_class, "monthly_budget_required")
                _raise("monthly_budget_required", 409, "Configure um orçamento mensal maior que zero.")
            if payload.task_budget_usd <= 0:
                _record_blocked(request_id, payload.task_id, provider_id, actor,
                                model_name, payload.data_class, "task_budget_required")
                _raise("task_budget_required", 409, "Defina um orçamento positivo para a tarefa.")
        if connection["auth_method"] != "none" and not connection.get("credential_ciphertext"):
            _record_blocked(request_id, payload.task_id, provider_id, actor,
                            model_name, payload.data_class, "credential_missing")
            _raise("credential_missing", 503, "A credencial do provedor não está configurada.")
        try:
            secret = (
                ai_providers.decrypt_credential(provider_id, connection["credential_ciphertext"])
                if connection.get("credential_ciphertext") else None
            )
        except ai_providers.ProviderSecretError:
            _record_blocked(request_id, payload.task_id, provider_id, actor,
                            model_name, payload.data_class, "credential_unavailable")
            _raise("credential_unavailable", 503,
                   "A credencial não pode ser recuperada; confirme a chave mestra do provedor.")
        try:
            target = _target(connection)
        except (ValueError, ConnectionError, OSError):
            _record_blocked(request_id, payload.task_id, provider_id, actor,
                            model_name, payload.data_class, "endpoint_unavailable")
            _raise("endpoint_unavailable", 422,
                   "O endpoint não passou pela validação de rede segura.")
        if context.cancelled.is_set():
            _record_blocked(request_id, payload.task_id, provider_id, actor,
                            model_name, payload.data_class, "cancelled_before_call")
            _raise("cancelled", 409, "A solicitação foi cancelada antes do envio.")
        input_bound = len(prompt_bytes) + INPUT_TOKEN_OVERHEAD
        if connection["endpoint_scope"] == "cloud":
            reserved = _cost_micro_usd(
                input_bound, payload.max_output_tokens,
                connection["input_cost_per_million_usd"],
                connection["output_cost_per_million_usd"],
            )
        else:
            input_rate = connection.get("input_cost_per_million_usd") or 0
            output_rate = connection.get("output_cost_per_million_usd") or 0
            reserved = _cost_micro_usd(
                input_bound, payload.max_output_tokens, input_rate, output_rate
            )
        reserved = _reserve_request(payload, actor, connection, reserved)
        reserved_ok = True
        if context.cancelled.is_set():
            _finish_request(request_id, actor, "cancelled", reserved,
                            reserved if context.request_sent else 0, None, None,
                            int((time.monotonic() - started) * 1000), "cancelled_before_call")
            _raise("cancelled", 409, "A solicitação foi cancelada antes do envio.")

        try:
            result = _perform_provider_request(
                connection, secret, target, payload.prompt,
                payload.max_output_tokens, context, request_id,
            )
        except _CancelledDuringCall:
            cost = reserved if context.request_sent else 0
            _finish_request(request_id, actor, "cancelled", reserved, cost, None, None,
                            int((time.monotonic() - started) * 1000), "cancelled")
            _raise("cancelled", 409, "A solicitação foi cancelada; uma chamada já enviada pode ter sido cobrada.")
        except InferenceRequestError as error:
            status = "cancelled" if context.cancelled.is_set() else error.code
            if context.cancelled.is_set():
                _finish_request(request_id, actor, "cancelled", reserved,
                                reserved if context.request_sent else 0, None, None,
                                int((time.monotonic() - started) * 1000), "cancelled")
                _raise("cancelled", 409,
                       "A solicitação foi cancelada; uma chamada já enviada pode ter sido cobrada.")
            _finish_request(request_id, actor, status, reserved, reserved, None, None,
                            int((time.monotonic() - started) * 1000), error.code)
            raise
        except (TimeoutError, socket.timeout):
            _finish_request(request_id, actor, "timeout", reserved, reserved, None, None,
                            int((time.monotonic() - started) * 1000), "timeout")
            _raise("timeout", 504,
                   "O provedor excedeu o timeout. A reserva foi mantida porque a cobrança é incerta.")
        except (OSError, ssl.SSLError, http.client.HTTPException):
            if context.cancelled.is_set():
                _finish_request(request_id, actor, "cancelled", reserved,
                                reserved if context.request_sent else 0, None, None,
                                int((time.monotonic() - started) * 1000), "cancelled")
                _raise("cancelled", 409,
                       "A solicitação foi cancelada; uma chamada já enviada pode ter sido cobrada.")
            _finish_request(request_id, actor, "unknown", reserved, reserved, None, None,
                            int((time.monotonic() - started) * 1000), "transport_unknown")
            _raise("transport_unknown", 502,
                   "A conexão terminou sem confirmação. A reserva foi mantida por segurança.")

        if context.cancelled.is_set():
            _finish_request(request_id, actor, "cancelled", reserved, reserved,
                            result["input_tokens"], result["output_tokens"],
                            int((time.monotonic() - started) * 1000), "cancelled")
            _raise("cancelled", 409,
                   "A solicitação foi cancelada; o provedor pode ter concluído e cobrado a chamada.")
        input_tokens = result["input_tokens"]
        output_tokens = result["output_tokens"]
        actual_cost = reserved
        if (
            connection["endpoint_scope"] == "cloud"
            and input_tokens is not None and output_tokens is not None
        ):
            actual_cost = _cost_micro_usd(
                input_tokens, output_tokens,
                connection["input_cost_per_million_usd"],
                connection["output_cost_per_million_usd"],
            )
        settled = max(reserved, actual_cost)
        _finish_request(request_id, actor, "succeeded", reserved, settled,
                        input_tokens, output_tokens,
                        int((time.monotonic() - started) * 1000), None)
        return {
            "request_id": request_id,
            "task_id": payload.task_id,
            "provider_id": provider_id,
            "model": model_name,
            "status": "succeeded",
            "output": result["output"],
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "reserved_cost_usd": _usd(reserved),
                "accounted_cost_usd": _usd(settled),
                "pricing_verified_on": connection.get("pricing_verified_on"),
            },
            "duration_ms": int((time.monotonic() - started) * 1000),
            "note": "Custo estimado localmente; confira também o limite de gastos na conta do provedor.",
        }
    except InferenceRequestError:
        raise
    except Exception:
        if reserved_ok:
            _finish_request(request_id, actor, "unknown", reserved, reserved, None, None,
                            int((time.monotonic() - started) * 1000), "internal_error")
        _record_blocked(request_id, payload.task_id, provider_id, actor,
                        model_name, payload.data_class, "internal_error")
        _raise("internal_error", 500, "O executor encontrou um erro; detalhes foram omitidos.")
    finally:
        with _ACTIVE_LOCK:
            current = _ACTIVE.get(request_id)
            if current is context:
                if current.connection:
                    try:
                        current.connection.close()
                    except OSError:
                        pass
                _ACTIVE.pop(request_id, None)



def execute_parallel(payload, actor: str) -> dict:
    """Run up to three selected profiles with one shared task budget and no retries."""
    global _ACTIVE_PARALLEL_CALLS
    provider_ids = list(payload.provider_ids)
    conn = get_db_connection()
    try:
        placeholders = ",".join("?" for _ in provider_ids)
        rows = conn.execute(
            f"SELECT id, endpoint_scope FROM ai_provider_connections WHERE id IN ({placeholders})",
            provider_ids,
        ).fetchall()
        local_count = sum(1 for row in rows if row["endpoint_scope"] == "local")
    finally:
        conn.close()
    if local_count > 1:
        _raise(
            "parallel_local_limit", 422,
            "Selecione no máximo um provedor local por lote para proteger os recursos do notebook.",
        )

    def run_one(provider_id: str) -> dict:
        child_id = uuid5(payload.request_id, "nivus-provider:" + provider_id)
        child = SimpleNamespace(
            request_id=child_id,
            task_id=payload.task_id,
            provider_id=provider_id,
            prompt=payload.prompt,
            data_class=payload.data_class,
            task_budget_usd=payload.task_budget_usd,
            max_output_tokens=payload.max_output_tokens,
        )
        try:
            result = execute(child, actor)
            return {
                "provider_id": provider_id,
                "request_id": str(child_id),
                "status": "succeeded",
                "result": result,
            }
        except InferenceRequestError as error:
            return {
                "provider_id": provider_id,
                "request_id": str(child_id),
                "status": "failed",
                "error": {"code": error.code, "message": error.public_message},
            }
        except Exception:
            return {
                "provider_id": provider_id,
                "request_id": str(child_id),
                "status": "failed",
                "error": {
                    "code": "internal_error",
                    "message": "O provedor encontrou um erro; detalhes foram omitidos.",
                },
            }

    with _PARALLEL_LOCK:
        if _ACTIVE_PARALLEL_CALLS + len(provider_ids) > _MAX_PARALLEL_CALLS:
            _raise(
                "parallel_capacity", 429,
                "O executor paralelo está ocupado. Aguarde a conclusão do lote ativo e tente novamente.",
            )
        _ACTIVE_PARALLEL_CALLS += len(provider_ids)

    try:
        completed: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=min(3, len(provider_ids)), thread_name_prefix="nivus-ai") as pool:
            futures = {pool.submit(run_one, provider_id): provider_id for provider_id in provider_ids}
            for future in as_completed(futures):
                provider_id = futures[future]
                completed[provider_id] = future.result()
        results = [completed[provider_id] for provider_id in provider_ids]
        success_count = sum(1 for item in results if item["status"] == "succeeded")
        failure_count = len(results) - success_count
        return {
        "request_id": str(payload.request_id),
        "task_id": payload.task_id,
        "status": (
            "succeeded" if failure_count == 0
            else "partial" if success_count > 0
            else "failed"
        ),
        "results": results,
        "success_count": success_count,
        "failure_count": failure_count,
            "note": "Chamadas paralelas sem retry ou fallback; cada provedor usa o mesmo teto agregado de tarefa.",
        }
    finally:
        with _PARALLEL_LOCK:
            _ACTIVE_PARALLEL_CALLS -= len(provider_ids)


def cancel_request(request_id: str, actor: str) -> bool:
    context = None
    with _ACTIVE_LOCK:
        context = _ACTIVE.get(request_id)
        if context is not None:
            if context.actor != actor:
                return False
            context.cancelled.set()
            if context.connection is not None:
                try:
                    context.connection.close()
                except OSError:
                    pass

    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT actor, provider_id, status FROM ai_execution_requests WHERE request_id=?",
            (request_id,),
        ).fetchone()
        if row is None:
            conn.commit()
            return context is not None
        if row["actor"] != actor:
            conn.rollback()
            return False
        if row["status"] not in {"reserved", "cancel_requested"}:
            conn.commit()
            # The worker can observe cancellation and finalize before this
            # endpoint reads the row. Make that concurrent cancellation idempotent.
            return (
                context is not None
                and context.cancelled.is_set()
                and row["status"] == "cancelled"
            )
        if row["status"] == "reserved":
            conn.execute(
                """UPDATE ai_execution_requests
                   SET status='cancel_requested', cancel_requested_at=?
                   WHERE request_id=? AND status='reserved'""",
                (time.time(), request_id),
            )
            ai_providers._audit(conn, row["provider_id"], actor, "inference_cancel_requested")
        conn.commit()
        return True
    finally:
        conn.close()


def list_audit(limit: int = 50) -> list[dict]:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """SELECT request_id, task_id, provider_id, actor, model_name, data_class,
                      status, reserved_cost_micro_usd, settled_cost_micro_usd,
                      input_tokens, output_tokens, duration_ms, failure_code,
                      created_at, completed_at
               FROM ai_execution_requests ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [
            {
                **dict(row),
                "reserved_cost_usd": _usd(row["reserved_cost_micro_usd"]),
                "accounted_cost_usd": _usd(row["settled_cost_micro_usd"]),
            }
            for row in rows
        ]
    finally:
        conn.close()
