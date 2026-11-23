"""Encrypted provider configuration and explicit, prompt-free connectivity probes."""

import base64
import datetime as dt
import http.client
import ipaddress
import json
import os
import secrets
import socket
import ssl
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from database import get_db_connection


KEY_FILE = Path(os.environ.get(
    "NIVUS_PROVIDER_ENCRYPTION_KEY_FILE",
    "/run/secrets/provider_encryption_key",
))
LOCAL_PORTS = {
    "ollama": {11434},
    "openai-compatible": {1234, 8000, 9931},
}
PRESETS = {
    "openai": {
        "name": "OpenAI",
        "protocol": "openai-compatible",
        "endpoint_scope": "cloud",
        "base_url": "https://api.openai.com/v1",
        "auth_method": "bearer",
    },
    "anthropic": {
        "name": "Anthropic",
        "protocol": "anthropic",
        "endpoint_scope": "cloud",
        "base_url": "https://api.anthropic.com/v1",
        "auth_method": "x-api-key",
    },
    "gemini": {
        "name": "Google Gemini",
        "protocol": "gemini",
        "endpoint_scope": "cloud",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "auth_method": "google-api-key",
    },
    "ollama": {
        "name": "Ollama local",
        "protocol": "ollama",
        "endpoint_scope": "local",
        "base_url": "http://host.docker.internal:11434",
        "auth_method": "none",
    },
    "openrouter": {
        "name": "OpenRouter Free",
        "protocol": "openai-compatible",
        "endpoint_scope": "cloud",
        "base_url": "https://openrouter.ai/api/v1",
        "auth_method": "bearer",
        "fixed_model": "openrouter/free",
    },
    "llama_cpp": {
        "name": "llama.cpp local",
        "protocol": "openai-compatible",
        "endpoint_scope": "local",
        "base_url": "http://llama-cpp:9931/v1",
        "auth_method": "none",
    },
}


class ProviderSecretError(RuntimeError):
    """The provider encryption key is missing or cannot decrypt this record."""


def load_encryption_key() -> bytes:
    try:
        key = KEY_FILE.read_bytes()
    except OSError as error:
        raise ProviderSecretError("A chave mestra dos provedores não está disponível.") from error
    if len(key) != 32:
        raise ProviderSecretError("A chave mestra dos provedores tem tamanho inválido.")
    return key


def encrypt_credential(provider_id: str, secret: str) -> str:
    if not secret or len(secret) > 4096 or any(ord(char) < 32 for char in secret):
        raise ValueError("A credencial está vazia ou contém caracteres inválidos.")
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(load_encryption_key()).encrypt(
        nonce, secret.encode("utf-8"), provider_id.encode("ascii")
    )
    return base64.urlsafe_b64encode(b"\x01" + nonce + ciphertext).decode("ascii")


def decrypt_credential(provider_id: str, encrypted: str) -> str:
    try:
        packed = base64.urlsafe_b64decode(encrypted.encode("ascii"))
        if len(packed) < 1 + 12 + 16 or packed[0] != 1:
            raise ValueError("invalid ciphertext version")
        plaintext = AESGCM(load_encryption_key()).decrypt(
            packed[1:13], packed[13:], provider_id.encode("ascii")
        )
        return plaintext.decode("utf-8")
    except ProviderSecretError:
        raise
    except Exception as error:
        raise ProviderSecretError(
            "A credencial não pôde ser descriptografada. Verifique a chave mestra e o backup."
        ) from error


def provider_catalog() -> list[dict]:
    items = [
        {
            "id": provider_id,
            "name": spec["name"],
            "scope": spec["endpoint_scope"],
            "protocol": spec["protocol"],
            "base_url": spec["base_url"],
            "auth_method": spec["auth_method"],
            "manual": False,
        }
        for provider_id, spec in PRESETS.items()
    ]
    items.append({
        "id": "manual",
        "name": "Cadastro manual",
        "scope": "cloud_or_local",
        "protocol": "openai-compatible",
        "base_url": "",
        "auth_method": "bearer",
        "manual": True,
    })
    return items


def normalize_base_url(value: str, scope: str, protocol: str) -> str:
    text = value.strip()
    if not text or len(text) > 512:
        raise ValueError("Informe uma URL-base válida.")
    try:
        parsed = urlsplit(text)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise ValueError("A URL-base é inválida.") from error
    if (
        not hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or any(part in {".", ".."} for part in parsed.path.split("/"))
        or "%" in parsed.path
        or "\\" in text
        or any(ord(char) < 32 for char in text)
    ):
        raise ValueError("A URL-base contém partes não permitidas.")

    if protocol == "ollama" and scope != "local":
        raise ValueError("Ollama é permitido somente como endpoint local.")
    if scope == "cloud":
        if parsed.scheme != "https" or port not in (None, 443):
            raise ValueError("Serviços de nuvem exigem HTTPS na porta 443.")
        if hostname.casefold() in {"localhost", "host.docker.internal"} or hostname.casefold().endswith(".local"):
            raise ValueError("Endpoint local não pode ser cadastrado como nuvem.")
    elif scope == "local":
        if parsed.scheme != "http":
            raise ValueError("Endpoints locais devem usar HTTP apenas na rede local.")
        expected_ports = LOCAL_PORTS.get(protocol)
        if not expected_ports:
            raise ValueError("Este protocolo não possui suporte local.")
        port = port or 80
        if port not in expected_ports:
            raise ValueError("A porta local não está na lista permitida para este protocolo.")
    else:
        raise ValueError("Escopo de endpoint inválido.")

    path = parsed.path.rstrip("/")
    normalized_host = hostname.casefold()
    url_host = f"[{normalized_host}]" if ":" in normalized_host else normalized_host
    return f"{parsed.scheme}://{url_host}" + (f":{port}" if port else "") + path


def _resolve_pinned_address(hostname: str, port: int, scope: str) -> str:
    try:
        answers = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except OSError as error:
        raise ConnectionError("O nome do endpoint não pôde ser resolvido.") from error
    addresses = sorted({answer[4][0].split("%", 1)[0] for answer in answers})
    if not addresses:
        raise ConnectionError("O endpoint não retornou endereços de rede.")
    parsed = [ipaddress.ip_address(address) for address in addresses]
    if scope == "cloud":
        if not all(address.is_global for address in parsed):
            raise ValueError("Endpoint de nuvem resolveu para um endereço não público.")
    else:
        if not all(
            address.is_private
            and not (
                address.is_loopback
                or address.is_link_local
                or address.is_multicast
                or address.is_unspecified
                or address.is_reserved
            )
            for address in parsed
        ):
            raise ValueError("Endpoint local deve resolver somente para endereços privados permitidos.")
    return addresses[0]


def _hostport(host: str, port: int, default_port: int) -> str:
    display_host = f"[{host}]" if ":" in host else host
    return display_host if port == default_port else f"{display_host}:{port}"


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def _get_hostport(self) -> str:
        return _hostport(self.host, self.port, self.default_port)

    def __init__(self, host: str, address: str, port: int, timeout: int):
        super().__init__(host, port=port, timeout=timeout)
        self._pinned_address = address

    def connect(self):
        self.sock = socket.create_connection(
            (self._pinned_address, self.port), self.timeout, self.source_address
        )


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def _get_hostport(self) -> str:
        return _hostport(self.host, self.port, self.default_port)

    def __init__(self, host: str, address: str, port: int, timeout: int):
        super().__init__(host, port=port, timeout=timeout, context=ssl.create_default_context())
        self._pinned_address = address

    def connect(self):
        raw_socket = socket.create_connection(
            (self._pinned_address, self.port), self.timeout, self.source_address
        )
        self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.host)


def _probe_url(base_url: str, protocol: str) -> tuple[str, str, int, str]:
    parsed = urlsplit(base_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if protocol == "ollama":
        suffix = "/api/tags"
    else:
        suffix = "/models"
    path = (parsed.path.rstrip("/") + suffix) or suffix
    if not path.startswith("/") or "\r" in path or "\n" in path:
        raise ValueError("Caminho de teste inválido.")
    return parsed.scheme, parsed.hostname or "", port, path


def _auth_headers(auth_method: str, secret: str | None, protocol: str) -> dict[str, str]:
    if auth_method == "none":
        return {}
    if not secret:
        raise ValueError("Cadastre uma chave antes de testar a conexão.")
    if auth_method == "bearer":
        return {"Authorization": f"Bearer {secret}"}
    if auth_method == "x-api-key":
        return {
            "x-api-key": secret,
            "anthropic-version": "2023-06-01",
        }
    if auth_method == "google-api-key":
        return {"x-goog-api-key": secret}
    raise ValueError("Método de autenticação não suportado.")


def probe_connection(connection: dict, secret: str | None) -> dict:
    scheme, hostname, port, path = _probe_url(
        connection["base_url"], connection["protocol"]
    )
    pinned = _resolve_pinned_address(hostname, port, connection["endpoint_scope"])
    headers = {
        "Accept": "application/json",
        "Connection": "close",
        "User-Agent": "Nivus-Provider-Test/1",
    }
    headers.update(
        _auth_headers(connection["auth_method"], secret, connection["protocol"])
    )
    timeout = min(max(int(connection["timeout_seconds"]), 2), 30)
    http_connection = (
        _PinnedHTTPSConnection(hostname, pinned, port, timeout)
        if scheme == "https"
        else _PinnedHTTPConnection(hostname, pinned, port, timeout)
    )
    try:
        http_connection.request("GET", path, headers=headers)
        response = http_connection.getresponse()
        status = response.status
        body = response.read(65537)
        if 300 <= status < 400:
            return {
                "success": False,
                "status": "redirect_blocked",
                "http_status": status,
                "model_count": None,
                "message": "O endpoint tentou redirecionar; o Nivus bloqueou o redirecionamento.",
            }
        if status in (401, 403):
            return {
                "success": False,
                "status": "credentials_rejected",
                "http_status": status,
                "model_count": None,
                "message": "O endpoint respondeu, mas não aceitou a autenticação.",
            }
        if status == 429:
            return {
                "success": False,
                "status": "rate_limited",
                "http_status": status,
                "model_count": None,
                "message": "O provedor limitou esta consulta. Aguarde antes de tentar novamente.",
            }
        if not 200 <= status < 300:
            return {
                "success": False,
                "status": "provider_error",
                "http_status": status,
                "model_count": None,
                "message": "O endpoint respondeu com erro. O corpo da resposta foi descartado.",
            }
        model_count = None
        if len(body) <= 65536:
            try:
                payload = json.loads(body.decode("utf-8"))
                models = payload.get("data", payload.get("models", payload.get("model")))
                if isinstance(models, list):
                    model_count = len(models)
                elif isinstance(models, str):
                    model_count = 1
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                pass
        return {
            "success": True,
            "status": "success",
            "http_status": status,
            "model_count": model_count,
            "message": "Conexão confirmada. Nenhum prompt foi enviado.",
        }
    except (TimeoutError, socket.timeout):
        return {
            "success": False,
            "status": "timeout",
            "http_status": None,
            "model_count": None,
            "message": "O endpoint não respondeu dentro do tempo configurado.",
        }
    except ssl.SSLCertVerificationError:
        return {
            "success": False,
            "status": "tls_error",
            "http_status": None,
            "model_count": None,
            "message": "A validação do certificado TLS falhou.",
        }
    except (OSError, http.client.HTTPException):
        return {
            "success": False,
            "status": "unreachable",
            "http_status": None,
            "model_count": None,
            "message": "Não foi possível alcançar o endpoint configurado.",
        }
    finally:
        http_connection.close()


def _audit(conn, provider_id: str | None, actor: str, action: str, outcome: str = "ok") -> None:
    conn.execute(
        """INSERT INTO ai_provider_audit
           (provider_id, actor, action, outcome, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (provider_id, actor, action, outcome, time.time()),
    )


def _public(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "provider_type": row["provider_type"],
        "protocol": row["protocol"],
        "endpoint_scope": row["endpoint_scope"],
        "base_url": row["base_url"],
        "model_name": row["model_name"],
        "responsible": row["responsible"],
        "purpose": row["purpose"],
        "auth_method": row["auth_method"],
        "credential_configured": bool(row["credential_ciphertext"]),
        "enabled": bool(row["enabled"]),
        "monthly_budget_usd": row["monthly_budget_usd"],
        "input_cost_per_million_usd": row["input_cost_per_million_usd"],
        "output_cost_per_million_usd": row["output_cost_per_million_usd"],
        "pricing_verified_on": row["pricing_verified_on"],
        "max_requests_per_hour": row["max_requests_per_hour"],
        "timeout_seconds": row["timeout_seconds"],
        "allowed_data_classes": json.loads(row["allowed_data_classes_json"]),
        "last_test_status": row["last_test_status"],
        "last_test_at": row["last_test_at"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_connections(actor: str) -> list[dict]:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM ai_provider_connections ORDER BY created_at DESC, id"
        ).fetchall()
        return [_public(row) for row in rows]
    finally:
        conn.close()


def create_connection(payload, actor: str) -> dict:
    provider_type = payload.provider_type
    secret = payload.api_key.get_secret_value() if payload.api_key else None
    if provider_type in PRESETS:
        spec = PRESETS[provider_type]
        if payload.base_url.rstrip("/") != spec["base_url"].rstrip("/"):
            raise ValueError("O endpoint dos provedores do catálogo é fixo.")
        if payload.auth_method != spec["auth_method"]:
            raise ValueError("O método de autenticação do provedor selecionado é fixo.")
        protocol = spec["protocol"]
        scope = spec["endpoint_scope"]
        base_url = spec["base_url"]
        name = spec["name"]
        auth_method = spec["auth_method"]
        if provider_type == "openrouter":
            if payload.model_name != spec["fixed_model"]:
                raise ValueError("OpenRouter Free aceita somente o modelo roteador openrouter/free.")
            if payload.input_cost_per_million_usd != 0 or payload.output_cost_per_million_usd != 0:
                raise ValueError("Registre preço zero para o preset OpenRouter Free.")
            if payload.pricing_verified_on is None:
                raise ValueError("Confirme a data da tabela de preço zero do OpenRouter Free.")
    elif provider_type == "manual":
        protocol = payload.protocol
        scope = payload.endpoint_scope
        base_url = normalize_base_url(payload.base_url, scope, protocol)
        name = payload.name.strip()
        auth_method = payload.auth_method
    else:
        raise ValueError("Provedor desconhecido.")

    if scope == "cloud" and any(
        item not in {"public", "synthetic"} for item in payload.allowed_data_classes
    ):
        raise ValueError("Conectores de nuvem aceitam somente dados públicos ou sintéticos.")
    if scope == "local" and auth_method != "none":
        raise ValueError("Endpoints locais não podem enviar chaves por HTTP.")
    if auth_method != "none" and not secret:
        raise ValueError("Informe a chave de API do provedor.")
    if auth_method == "none" and secret:
        raise ValueError("Remova a chave: este conector não usa autenticação.")

    provider_id = uuid.uuid4().hex
    encrypted = encrypt_credential(provider_id, secret) if secret else None
    now = time.time()
    conn = get_db_connection()
    try:
        conn.execute(
            """INSERT INTO ai_provider_connections
               (id, name, provider_type, protocol, endpoint_scope, base_url,
                model_name, responsible, purpose, auth_method, credential_ciphertext,
                enabled, monthly_budget_usd, input_cost_per_million_usd,
                output_cost_per_million_usd, pricing_verified_on,
                max_requests_per_hour, timeout_seconds, allowed_data_classes_json,
                last_test_status, last_test_at, created_by, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, 'not_tested',
                       NULL, ?, ?, ?)""",
            (
                provider_id,
                name,
                provider_type,
                protocol,
                scope,
                base_url,
                payload.model_name.strip(),
                payload.responsible.strip(),
                payload.purpose.strip(),
                auth_method,
                encrypted,
                payload.monthly_budget_usd,
                payload.input_cost_per_million_usd,
                payload.output_cost_per_million_usd,
                payload.pricing_verified_on.isoformat() if payload.pricing_verified_on else None,
                payload.max_requests_per_hour,
                payload.timeout_seconds,
                json.dumps(payload.allowed_data_classes, separators=(",", ":")),
                actor,
                now,
                now,
            ),
        )
        _audit(conn, provider_id, actor, "created")
        conn.commit()
        row = conn.execute(
            "SELECT * FROM ai_provider_connections WHERE id = ?", (provider_id,)
        ).fetchone()
        return _public(row)
    finally:
        conn.close()


def update_connection(provider_id: str, payload, actor: str) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise ValueError("Nenhuma alteração foi informada.")
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM ai_provider_connections WHERE id = ?", (provider_id,)
        ).fetchone()
        if row is None:
            raise KeyError(provider_id)
        merged = {
            "name": row["name"],
            "model_name": row["model_name"],
            "responsible": row["responsible"],
            "purpose": row["purpose"],
            "monthly_budget_usd": row["monthly_budget_usd"],
            "input_cost_per_million_usd": row["input_cost_per_million_usd"],
            "output_cost_per_million_usd": row["output_cost_per_million_usd"],
            "pricing_verified_on": row["pricing_verified_on"],
            "max_requests_per_hour": row["max_requests_per_hour"],
            "timeout_seconds": row["timeout_seconds"],
            "allowed_data_classes": json.loads(row["allowed_data_classes_json"]),
        }
        merged.update(changes)
        nullable_fields = {
            "monthly_budget_usd", "input_cost_per_million_usd",
            "output_cost_per_million_usd", "pricing_verified_on",
        }
        if any(value is None for key, value in changes.items() if key not in nullable_fields):
            raise ValueError("Um campo de configuração não pode ser apagado.")
        if row["provider_type"] == "openrouter" and merged["model_name"] != "openrouter/free":
            raise ValueError("OpenRouter Free aceita somente o modelo roteador openrouter/free.")
        if row["endpoint_scope"] == "cloud" and any(
            item not in {"public", "synthetic"} for item in merged["allowed_data_classes"]
        ):
            raise ValueError("Conectores de nuvem aceitam somente dados públicos ou sintéticos.")
        now = time.time()
        conn.execute(
            """UPDATE ai_provider_connections
               SET name=?, model_name=?, responsible=?, purpose=?, monthly_budget_usd=?,
                   input_cost_per_million_usd=?, output_cost_per_million_usd=?,
                   pricing_verified_on=?, max_requests_per_hour=?, timeout_seconds=?,
                   allowed_data_classes_json=?, updated_at=? WHERE id=?""",
            (
                merged["name"].strip(),
                merged["model_name"].strip(),
                merged["responsible"].strip(),
                merged["purpose"].strip(),
                merged["monthly_budget_usd"],
                merged["input_cost_per_million_usd"],
                merged["output_cost_per_million_usd"],
                merged["pricing_verified_on"].isoformat()
                if hasattr(merged["pricing_verified_on"], "isoformat")
                else merged["pricing_verified_on"],
                merged["max_requests_per_hour"],
                merged["timeout_seconds"],
                json.dumps(merged["allowed_data_classes"], separators=(",", ":")),
                now,
                provider_id,
            ),
        )
        _audit(conn, provider_id, actor, "updated")
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM ai_provider_connections WHERE id = ?", (provider_id,)
        ).fetchone()
        return _public(updated)
    finally:
        conn.close()


def replace_credential(provider_id: str, secret: str, actor: str) -> dict:
    encrypted = encrypt_credential(provider_id, secret)
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT id FROM ai_provider_connections WHERE id = ?", (provider_id,)
        ).fetchone()
        if row is None:
            raise KeyError(provider_id)
        now = time.time()
        conn.execute(
            """UPDATE ai_provider_connections
               SET credential_ciphertext=?, enabled=0, last_test_status='not_tested',
                   last_test_at=NULL, updated_at=? WHERE id=?""",
            (encrypted, now, provider_id),
        )
        _audit(conn, provider_id, actor, "credential_replaced")
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM ai_provider_connections WHERE id = ?", (provider_id,)
        ).fetchone()
        return _public(updated)
    finally:
        conn.close()


def _load_connection(provider_id: str):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM ai_provider_connections WHERE id = ?", (provider_id,)
    ).fetchone()
    conn.close()
    if row is None:
        raise KeyError(provider_id)
    return dict(row)


def _reserve_probe_slot(connection: dict, actor: str) -> dict | None:
    provider_id = connection["id"]
    now = time.time()
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        policy = conn.execute(
            """SELECT endpoint_scope, monthly_budget_usd, max_requests_per_hour
               FROM ai_provider_connections WHERE id=?""",
            (provider_id,),
        ).fetchone()
        if policy is None:
            raise KeyError(provider_id)
        if policy["endpoint_scope"] == "cloud" and (
            policy["monthly_budget_usd"] is None or policy["monthly_budget_usd"] <= 0
        ):
            _audit(conn, provider_id, actor, "connection_test_blocked", "budget_required")
            conn.commit()
            return {
                "success": False,
                "status": "budget_required",
                "http_status": None,
                "model_count": None,
                "message": "Defina um orçamento mensal maior que zero antes do teste de nuvem.",
            }

        probe_attempts = conn.execute(
            """SELECT COUNT(*) FROM ai_provider_audit
               WHERE provider_id=? AND action='connection_test_started' AND created_at>=?""",
            (provider_id, now - 3600),
        ).fetchone()[0]
        inference_attempts = conn.execute(
            """SELECT COUNT(*) FROM ai_execution_requests
               WHERE provider_id=? AND status!='blocked' AND created_at>=?""",
            (provider_id, now - 3600),
        ).fetchone()[0]
        if int(probe_attempts) + int(inference_attempts) >= int(policy["max_requests_per_hour"]):
            _audit(conn, provider_id, actor, "connection_test_blocked", "rate_limited")
            conn.commit()
            return {
                "success": False,
                "status": "rate_limited",
                "http_status": None,
                "model_count": None,
                "message": "O limite de testes por hora deste provedor foi atingido.",
            }

        _audit(conn, provider_id, actor, "connection_test_started")
        conn.commit()
        return None
    finally:
        conn.close()


def test_connection(provider_id: str, actor: str) -> dict:
    connection = _load_connection(provider_id)
    secret = (
        decrypt_credential(provider_id, connection["credential_ciphertext"])
        if connection["credential_ciphertext"]
        else None
    )
    blocked = _reserve_probe_slot(connection, actor)
    if blocked:
        now = time.time()
        conn = get_db_connection()
        try:
            conn.execute(
                """UPDATE ai_provider_connections
                   SET last_test_status=?, last_test_at=?,
                       enabled=CASE WHEN ?='budget_required' THEN 0 ELSE enabled END,
                       updated_at=? WHERE id=?""",
                (blocked["status"], now, blocked["status"], now, provider_id),
            )
            conn.commit()
        finally:
            conn.close()
        return blocked

    result = probe_connection(connection, secret)
    now = time.time()
    conn = get_db_connection()
    try:
        conn.execute(
            """UPDATE ai_provider_connections
               SET last_test_status=?, last_test_at=?, enabled=CASE WHEN ? THEN enabled ELSE 0 END,
                   updated_at=? WHERE id=?""",
            (result["status"], now, int(result["success"]), now, provider_id),
        )
        _audit(
            conn,
            provider_id,
            actor,
            "connection_tested",
            "success" if result["success"] else result["status"],
        )
        conn.commit()
    finally:
        conn.close()
    return result


def _cloud_pricing_is_current(row) -> bool:
    input_rate = row["input_cost_per_million_usd"]
    output_rate = row["output_cost_per_million_usd"]
    verified = row["pricing_verified_on"]
    if input_rate is None or output_rate is None or not verified:
        return False
    try:
        pricing_day = dt.date.fromisoformat(str(verified))
        today = dt.datetime.now(dt.timezone.utc).date()
    except ValueError:
        return False
    return 0 <= (today - pricing_day).days <= 90


def set_enabled(provider_id: str, enabled: bool, actor: str) -> dict:
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM ai_provider_connections WHERE id = ?", (provider_id,)
        ).fetchone()
        if row is None:
            raise KeyError(provider_id)
        if enabled:
            if row["last_test_status"] != "success":
                raise ValueError("Teste a conexão com sucesso antes de habilitar o provedor.")
            if row["endpoint_scope"] == "cloud" and (
                row["monthly_budget_usd"] is None or row["monthly_budget_usd"] <= 0
            ):
                raise ValueError("Defina um limite mensal maior que zero antes de habilitar nuvem.")
            if row["endpoint_scope"] == "cloud" and not _cloud_pricing_is_current(row):
                raise ValueError(
                    "Informe preços de entrada/saída por milhão de tokens e uma data recente antes de habilitar."
                )
            if not row["responsible"].strip() or not row["purpose"].strip():
                raise ValueError("Informe responsável e finalidade antes de habilitar.")
        now = time.time()
        conn.execute(
            "UPDATE ai_provider_connections SET enabled=?, updated_at=? WHERE id=?",
            (int(enabled), now, provider_id),
        )
        _audit(conn, provider_id, actor, "enabled" if enabled else "disabled")
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM ai_provider_connections WHERE id = ?", (provider_id,)
        ).fetchone()
        return _public(updated)
    finally:
        conn.close()


def delete_connection(provider_id: str, actor: str) -> bool:
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT id FROM ai_provider_connections WHERE id = ?", (provider_id,)
        ).fetchone()
        if row is None:
            return False
        conn.execute("DELETE FROM ai_provider_connections WHERE id = ?", (provider_id,))
        _audit(conn, provider_id, actor, "deleted")
        conn.commit()
        return True
    finally:
        conn.close()


def list_audit(limit: int = 50) -> list[dict]:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """SELECT provider_id, actor, action, outcome, created_at
               FROM ai_provider_audit ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
