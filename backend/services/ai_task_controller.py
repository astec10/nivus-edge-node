"""Persistent, low-resource coordinator for the public GitHub AI task queue.

This service observes and authorizes GitHub Issues. It never checks out, builds,
or executes task code; the existing GitHub-hosted workflow owns that work.
"""

from __future__ import annotations

import datetime as dt
import http.client
import json
import logging
import re
import threading
import time
from urllib.parse import quote

from database import get_db_connection
from scripts.validate_ai_task import validate as validate_ai_task
from services import ai_providers


logger = logging.getLogger("nivus.ai_task_controller")
GITHUB_API_HOST = "api.github.com"
GITHUB_API_VERSION = "2022-11-28"
GITHUB_TOKEN_CONTEXT = "nivus-github-task-controller-v1"
MAX_GITHUB_RESPONSE_BYTES = 2_000_000
DEFAULT_REPOSITORY = "astec10/nivus-edge-node"
_REPOSITORY_PATTERN = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,99})$"
)


class TaskControllerError(RuntimeError):
    def __init__(self, code: str, public_message: str, http_status: int = 422):
        super().__init__(code)
        self.code = code
        self.public_message = public_message
        self.http_status = http_status


_state_lock = threading.Lock()
_authorize_lock = threading.Lock()
_poll_lock = threading.Lock()
_wake_event = threading.Event()
_stop_event = threading.Event()
_thread: threading.Thread | None = None
_state = {
    "state": "stopped",
    "last_poll_at": None,
    "last_success_at": None,
    "last_error_code": None,
    "tasks": [],
}


def _settings_row():
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM ai_task_controller_settings WHERE id=1"
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT OR IGNORE INTO ai_task_controller_settings (id, repository) VALUES (1, ?)",
                (DEFAULT_REPOSITORY,),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM ai_task_controller_settings WHERE id=1"
            ).fetchone()
        return row
    finally:
        conn.close()


def _audit(actor: str, repository: str, issue_number: int | None, action: str, outcome: str) -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            """INSERT INTO ai_task_controller_audit
               (actor, repository, issue_number, action, outcome, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (actor[:80], repository[:141], issue_number, action[:40], outcome[:40], time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def get_config() -> dict:
    row = _settings_row()
    return {
        "repository": row["repository"],
        "enabled": bool(row["enabled"]),
        "poll_interval_seconds": row["poll_interval_seconds"],
        "max_authorizations_per_day": row["max_authorizations_per_day"],
        "credential_configured": bool(row["credential_ciphertext"]),
        "last_test_status": row["last_test_status"],
        "last_test_at": row["last_test_at"],
    }


def _get_token(row=None) -> str:
    row = row or _settings_row()
    encrypted = row["credential_ciphertext"]
    if not encrypted:
        raise TaskControllerError(
            "github_token_missing", "Cadastre o token GitHub antes de testar a conexão.", 409
        )
    try:
        return ai_providers.decrypt_credential(GITHUB_TOKEN_CONTEXT, encrypted)
    except ai_providers.ProviderSecretError:
        raise TaskControllerError(
            "encryption_key_unavailable",
            "A chave mestra de credenciais não está disponível ou não corresponde ao backup.",
            503,
        ) from None


def update_settings(payload, actor: str) -> dict:
    # Lock order is always authorization then polling so stale reads cannot replace config state.
    with _authorize_lock, _poll_lock:
        return _update_settings_locked(payload, actor)


def _update_settings_locked(payload, actor: str) -> dict:
    row = _settings_row()
    repository = payload.repository.strip()
    if not _REPOSITORY_PATTERN.fullmatch(repository):
        raise ValueError("Informe o repositório no formato proprietário/nome.")

    old_token = row["credential_ciphertext"]
    token_changed = payload.github_token is not None
    if token_changed:
        raw_token = payload.github_token.get_secret_value().strip()
        if not raw_token:
            raise ValueError("O token GitHub não pode ficar vazio.")
        encrypted = ai_providers.encrypt_credential(GITHUB_TOKEN_CONTEXT, raw_token)
    else:
        encrypted = old_token

    repository_changed = repository.casefold() != row["repository"].casefold()
    credentials_changed = repository_changed or token_changed
    conn = get_db_connection()
    try:
        conn.execute(
            """UPDATE ai_task_controller_settings
               SET repository=?, poll_interval_seconds=?, max_authorizations_per_day=?, credential_ciphertext=?,
                   enabled=CASE WHEN ? THEN 0 ELSE enabled END,
                   last_test_status=CASE WHEN ? THEN 'not_tested' ELSE last_test_status END,
                   last_test_at=CASE WHEN ? THEN NULL ELSE last_test_at END,
                   updated_by=?, updated_at=?
               WHERE id=1""",
            (
                repository,
                payload.poll_interval_seconds,
                payload.max_authorizations_per_day,
                encrypted,
                int(credentials_changed),
                int(credentials_changed),
                int(credentials_changed),
                actor[:80],
                time.time(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    _audit(actor, repository, None, "configuration_saved", "ok")
    if credentials_changed:
        _set_state(
            state="disabled", last_poll_at=None, last_success_at=None,
            last_error_code=None, tasks=[],
        )
    _wake_event.set()
    return get_config()


def _github_request(method: str, path: str, token: str | None, payload: dict | None = None):
    if not path.startswith("/repos/") or "\r" in path or "\n" in path:
        raise TaskControllerError("invalid_github_path", "Caminho da API GitHub inválido.")
    try:
        address = ai_providers._resolve_pinned_address(GITHUB_API_HOST, 443, "cloud")
        connection = ai_providers._PinnedHTTPSConnection(
            GITHUB_API_HOST, address, 443, timeout=10
        )
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8") if payload is not None else None
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Nivus-Edge-Task-Controller",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        response_body = response.read(MAX_GITHUB_RESPONSE_BYTES + 1)
        if len(response_body) > MAX_GITHUB_RESPONSE_BYTES:
            raise TaskControllerError(
                "github_response_too_large", "A resposta do GitHub excedeu o limite seguro.", 502
            )
        if response.status == 401:
            if token is None:
                raise TaskControllerError(
                    "repository_visibility_unverified",
                    "Não foi possível confirmar a visibilidade pública do repositório.",
                    503,
                )
            raise TaskControllerError(
                "github_auth_failed", "O GitHub recusou o token configurado.", 401
            )
        if response.status == 403:
            remaining = response.getheader("X-RateLimit-Remaining")
            if remaining == "0":
                raise TaskControllerError(
                    "github_rate_limited", "O limite temporário da API GitHub foi atingido.", 429
                )
            if token is None:
                raise TaskControllerError(
                    "repository_visibility_unverified",
                    "Não foi possível confirmar a visibilidade pública do repositório.",
                    503,
                )
            raise TaskControllerError(
                "github_permission_denied",
                "O token não tem a permissão Issues necessária para esta ação.",
                403,
            )
        if response.status == 404:
            raise TaskControllerError(
                "github_not_found", "Repositório ou Issue não encontrado com este token.", 404
            )
        if response.status == 422:
            raise TaskControllerError(
                "github_validation_failed", "O GitHub recusou a alteração solicitada.", 422
            )
        if not 200 <= response.status < 300:
            raise TaskControllerError(
                "github_http_error", "A API GitHub retornou um erro temporário.", 502
            )
        if not response_body:
            return None
        try:
            return json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise TaskControllerError(
                "github_response_invalid", "A resposta da API GitHub não era JSON válido.", 502
            ) from None
    except TaskControllerError:
        raise
    except (OSError, http.client.HTTPException, ValueError):
        raise TaskControllerError(
            "github_unreachable", "Não foi possível alcançar api.github.com por HTTPS.", 503
        ) from None
    finally:
        try:
            connection.close()
        except (UnboundLocalError, AttributeError):
            pass


def _require_public_repository(repository: str) -> None:
    """Verify repository visibility anonymously before touching its Issues."""
    owner, name = _repo_parts(repository)
    path = f"/repos/{owner}/{name}"
    try:
        details = _github_request("GET", path, None)
    except TaskControllerError as error:
        if error.code == "github_not_found":
            raise TaskControllerError(
                "repository_not_public",
                "O repositório precisa existir e ser público para este controlador.",
                422,
            ) from None
        raise
    if not isinstance(details, dict) or details.get("private") is not False:
        raise TaskControllerError(
            "repository_not_public",
            "O repositório precisa existir e ser público para este controlador.",
            422,
        )


def test_connection(actor: str) -> dict:
    # Serialize settings checks/changes with explicit issue authorization.
    with _authorize_lock:
        return _test_connection_locked(actor)


def _test_connection_locked(actor: str) -> dict:
    row = _settings_row()
    repository = row["repository"]
    try:
        token = _get_token(row)
        _require_public_repository(repository)
        owner, name = repository.split("/", 1)
        path = (
            f"/repos/{quote(owner, safe='')}/{quote(name, safe='')}/issues"
            "?state=open&labels=ai%3Aqueued&per_page=1"
        )
        result = _github_request("GET", path, token)
        if not isinstance(result, list):
            raise TaskControllerError(
                "github_response_invalid", "A API GitHub retornou um formato inesperado.", 502
            )
        outcome = "success"
        message = "Conexão validada. Nenhuma Issue foi alterada nem modelo chamado."
        status = 200
    except TaskControllerError as error:
        outcome = error.code
        message = error.public_message
        status = error.http_status
    conn = get_db_connection()
    try:
        conn.execute(
            """UPDATE ai_task_controller_settings SET last_test_status=?, last_test_at=?,
               updated_by=?, updated_at=? WHERE id=1""",
            (outcome, time.time(), actor[:80], time.time()),
        )
        conn.commit()
    finally:
        conn.close()
    _audit(actor, repository, None, "connection_tested", outcome)
    if outcome != "success":
        raise TaskControllerError(outcome, message, status)
    _wake_event.set()
    return {"status": outcome, "message": message, **get_config()}


def set_enabled(enabled: bool, actor: str) -> dict:
    # Wait for in-flight reads before disabling or clearing the cached queue.
    with _authorize_lock, _poll_lock:
        return _set_enabled_locked(enabled, actor)


def _set_enabled_locked(enabled: bool, actor: str) -> dict:
    row = _settings_row()
    if enabled and not row["credential_ciphertext"]:
        raise TaskControllerError(
            "github_token_missing", "Cadastre e teste um token GitHub antes de habilitar.", 409
        )
    if enabled and (
        row["last_test_status"] != "success"
        or row["last_test_at"] is None
        or row["last_test_at"] < time.time() - 86400
    ):
        raise TaskControllerError(
            "github_connection_not_tested",
            "Teste a conexão novamente. A validação precisa ter menos de 24 horas.",
            409,
        )
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE ai_task_controller_settings SET enabled=?, updated_by=?, updated_at=? WHERE id=1",
            (int(enabled), actor[:80], time.time()),
        )
        conn.commit()
    finally:
        conn.close()
    _audit(actor, row["repository"], None, "controller_toggled", "enabled" if enabled else "disabled")
    _set_state(
        state="starting" if enabled else "disabled",
        last_poll_at=None, last_success_at=None, last_error_code=None, tasks=[],
    )
    _wake_event.set()
    return get_config()


def _repo_parts(repository: str) -> tuple[str, str]:
    owner, name = repository.split("/", 1)
    return quote(owner, safe=""), quote(name, safe="")


def _issue_labels(issue: dict) -> set[str]:
    labels = issue.get("labels")
    if not isinstance(labels, list):
        return set()
    return {
        item["name"] for item in labels
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }


def _task_summary(issue: dict) -> dict | None:
    if "pull_request" in issue or not isinstance(issue.get("number"), int):
        return None
    labels = _issue_labels(issue)
    if not labels.intersection({"ai:queued", "ai:ready"}):
        return None
    queued = "ai:queued" in labels
    ready = "ai:ready" in labels
    valid = False
    if queued and isinstance(issue.get("body"), str):
        valid = not validate_ai_task(issue["body"], require_free_tier=True)
    return {
        "number": issue["number"],
        "title": str(issue.get("title", "Issue sem título"))[:200],
        "url": str(issue.get("html_url", ""))[:500],
        "created_at": str(issue.get("created_at", ""))[:40],
        "queue_state": "authorized" if ready else ("queued" if queued else "unknown"),
        "can_authorize": queued and not ready and valid and issue.get("state") == "open",
        "validation_status": "valid" if valid else ("already_authorized" if ready else "invalid"),
    }


def _fetch_tasks(row, token: str) -> list[dict]:
    owner, name = _repo_parts(row["repository"])
    collected: dict[int, dict] = {}
    for label in ("ai:queued", "ai:ready"):
        _require_public_repository(row["repository"])
        path = (
            f"/repos/{owner}/{name}/issues?state=open&labels={quote(label, safe='')}"
            "&per_page=50"
        )
        response = _github_request("GET", path, token)
        if not isinstance(response, list):
            raise TaskControllerError(
                "github_response_invalid", "A API GitHub retornou uma lista inesperada.", 502
            )
        for issue in response:
            if not isinstance(issue, dict):
                continue
            summary = _task_summary(issue)
            if summary:
                collected[summary["number"]] = summary
    return sorted(collected.values(), key=lambda item: item["number"], reverse=True)


def _set_state(**changes) -> None:
    with _state_lock:
        _state.update(changes)


def get_status() -> dict:
    config = get_config()
    with _state_lock:
        snapshot = dict(_state)
        snapshot["tasks"] = list(_state["tasks"])
    if not config["enabled"]:
        snapshot["state"] = "disabled"
    elif not config["credential_configured"]:
        snapshot["state"] = "not_configured"
    snapshot.update({
        "enabled": config["enabled"],
        "repository": config["repository"],
        "poll_interval_seconds": config["poll_interval_seconds"],
        "credential_configured": config["credential_configured"],
        "last_test_status": config["last_test_status"],
    })
    return snapshot


def poll_once() -> dict:
    """Serialize UI refreshes with the resident poll loop."""
    with _poll_lock:
        return _poll_once_locked()


def _poll_once_locked() -> dict:
    row = _settings_row()
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    if not row["enabled"]:
        _set_state(state="disabled", last_poll_at=now, last_error_code=None, tasks=[])
        return get_status()
    try:
        token = _get_token(row)
        tasks = _fetch_tasks(row, token)
    except TaskControllerError as error:
        state_changes = {
            "state": "degraded",
            "last_poll_at": now,
            "last_error_code": error.code,
        }
        if error.code in {"repository_not_public", "repository_visibility_unverified"}:
            state_changes["tasks"] = []
        _set_state(**state_changes)
        logger.warning("GitHub queue poll failed: %s", error.code)
        return get_status()
    _set_state(
        state="online",
        last_poll_at=now,
        last_success_at=now,
        last_error_code=None,
        tasks=tasks,
    )
    return get_status()


def refresh_now() -> dict:
    if not get_config()["enabled"]:
        raise TaskControllerError(
            "controller_disabled", "Habilite o controlador antes de consultar a fila.", 409
        )
    return poll_once()


def authorize_issue(issue_number: int, confirm_free_tier_call: bool, actor: str) -> dict:
    if not confirm_free_tier_call:
        raise TaskControllerError(
            "explicit_authorization_required",
            "Confirme que revisou a Issue e autoriza uma única chamada free-tier.",
            422,
        )
    if not 1 <= issue_number <= 2_147_483_647:
        raise TaskControllerError("invalid_issue_number", "Número de Issue inválido.", 422)

    with _authorize_lock, _poll_lock:
        row = _settings_row()
        if not row["enabled"]:
            raise TaskControllerError(
                "controller_disabled", "Habilite o controlador antes de autorizar uma Issue.", 409
            )
        token = _get_token(row)
        try:
            _require_public_repository(row["repository"])
        except TaskControllerError as error:
            _audit(actor, row["repository"], issue_number, "authorization_blocked", error.code)
            raise
        owner, name = _repo_parts(row["repository"])
        issue_path = f"/repos/{owner}/{name}/issues/{issue_number}"
        issue = _github_request("GET", issue_path, token)
        if not isinstance(issue, dict) or "pull_request" in issue or issue.get("state") != "open":
            raise TaskControllerError(
                "issue_not_open", "Somente uma Issue aberta pode ser autorizada.", 409
            )

        labels = _issue_labels(issue)
        if "ai:ready" in labels:
            _audit(actor, row["repository"], issue_number, "authorization_checked", "already_ready")
            return {
                "status": "already_authorized",
                "message": "Esta Issue já está autorizada. Nenhuma nova chamada foi solicitada.",
                "issue_number": issue_number,
                "url": issue.get("html_url", ""),
            }
        if "ai:queued" not in labels:
            raise TaskControllerError(
                "issue_not_queued", "A Issue não está mais na fila ai:queued.", 409
            )
        body = issue.get("body")
        if not isinstance(body, str) or validate_ai_task(body, require_free_tier=True):
            _audit(actor, row["repository"], issue_number, "authorization_blocked", "invalid_contract")
            raise TaskControllerError(
                "issue_contract_invalid",
                "A Issue precisa cumprir o formulário, o escopo público/sintético e o limite free-tier.",
                422,
            )

        conn = get_db_connection()
        try:
            recent_authorizations = conn.execute(
                """SELECT COUNT(*) FROM ai_task_controller_audit
                   WHERE action='authorization_requested' AND outcome='started'
                     AND created_at >= ?""",
                (time.time() - 86400,),
            ).fetchone()[0]
        finally:
            conn.close()
        if recent_authorizations >= row["max_authorizations_per_day"]:
            raise TaskControllerError(
                "daily_authorization_limit",
                "O limite diário de autorizações da dashboard foi atingido. Ajuste o limite ou aguarde 24 horas.",
                429,
            )

        try:
            _require_public_repository(row["repository"])
        except TaskControllerError as error:
            _audit(actor, row["repository"], issue_number, "authorization_blocked", error.code)
            raise

        _audit(actor, row["repository"], issue_number, "authorization_requested", "started")
        try:
            _github_request(
                "POST",
                f"{issue_path}/labels",
                token,
                {"labels": ["ai:ready"]},
            )
        except TaskControllerError as post_error:
            # A POST may have reached GitHub before a network timeout. Inspect the Issue before
            # reporting the outcome; never repeat the POST automatically.
            try:
                _require_public_repository(row["repository"])
                refreshed = _github_request("GET", issue_path, token)
            except TaskControllerError:
                _audit(actor, row["repository"], issue_number, "authorization_requested", "outcome_unknown")
                raise TaskControllerError(
                    "authorization_outcome_unknown",
                    "A resposta da autorização foi interrompida. Atualize a fila antes de tentar de novo.",
                    503,
                ) from None
            if "ai:ready" not in _issue_labels(refreshed if isinstance(refreshed, dict) else {}):
                _audit(actor, row["repository"], issue_number, "authorization_requested", post_error.code)
                raise post_error

        _audit(actor, row["repository"], issue_number, "authorization_requested", "confirmed")
        _wake_event.set()
        return {
            "status": "authorized",
            "message": "Issue marcada ai:ready. O workflow GitHub inicia a proposta em runner efêmero; o Nivus não chamou o modelo nem executou código.",
            "issue_number": issue_number,
            "url": issue.get("html_url", ""),
        }


def list_audit(limit: int = 20) -> list[dict]:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """SELECT repository, issue_number, action, outcome, created_at
               FROM ai_task_controller_audit ORDER BY id DESC LIMIT ?""",
            (max(1, min(int(limit), 100)),),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _poll_loop() -> None:
    while not _stop_event.is_set():
        try:
            config = get_config()
            if config["enabled"] and config["credential_configured"]:
                poll_once()
                delay = get_config()["poll_interval_seconds"]
            else:
                _set_state(
                    state="disabled" if not config["enabled"] else "not_configured",
                    last_error_code=None,
                    tasks=[],
                )
                delay = max(30, config["poll_interval_seconds"])
        except Exception:
            # Keep the resident coordinator alive after an unexpected poll or DB error.
            logger.exception("Unexpected GitHub queue poll failure.")
            _set_state(
                state="degraded",
                last_poll_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                last_error_code="internal_error",
            )
            delay = 60
        _wake_event.wait(delay)
        _wake_event.clear()


def start() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(
        target=_poll_loop, name="nivus-ai-task-controller", daemon=True
    )
    _thread.start()


def stop() -> None:
    _stop_event.set()
    _wake_event.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=6)
