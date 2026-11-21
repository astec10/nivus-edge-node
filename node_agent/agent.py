"""Minimal HTTPS-only identity and heartbeat client for Nivus nodes."""

from __future__ import annotations

import argparse
import getpass
import json
import logging
import os
import re
import ssl
import stat
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from .telemetry import NodeTelemetryCollector

AGENT_VERSION = "0.1.0"
SCHEMA_VERSION = 1
DEFAULT_HEARTBEAT_SECONDS = 30
DEFAULT_TELEMETRY_INTERVAL_SECONDS = 30
MAX_RESPONSE_BYTES = 64 * 1024
MAX_BACKOFF_SECONDS = 60
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{40,128}$")
_NODE_ID_RE = re.compile(r"^[a-f0-9]{32}$")
_NAME_RE = re.compile(r"^[^\W_][\w .-]{0,47}$", re.UNICODE)
_LOG = logging.getLogger("nivus.node_agent")


class AgentError(Exception):
    """A safe-to-display agent error. Messages must never contain credentials."""


class ApiError(AgentError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"A API do Nó Master respondeu HTTP {status_code}.")


class AuthenticationRejected(ApiError):
    def __init__(self):
        super().__init__(401)
        self.args = ("Credencial do nó inválida ou revogada. Faça novo pareamento.",)


class SequenceConflict(ApiError):
    def __init__(self):
        super().__init__(409)
        self.args = ("A API rejeitou a sequência do heartbeat.",)


class RetryableApiError(ApiError):
    """A transient HTTP response that is safe to retry for idempotent metadata."""

    def __init__(self, status_code: int, retry_after_seconds: int | None = None):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(status_code)


class TransportError(AgentError):
    """A temporary TLS/network transport failure."""


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Do not forward node credentials to a redirect target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True, repr=False)
class NodeCredentials:
    master_url: str
    name: str
    node_id: str
    token: str
    ca_file: str | None = None

    def __repr__(self) -> str:
        return (
            "NodeCredentials("
            f"master_url={self.master_url!r}, name={self.name!r}, "
            f"node_id={self.node_id!r}, token=<redacted>, ca_file={self.ca_file!r})"
        )


def validate_master_url(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise AgentError("Informe a URL HTTPS do Nó Master.")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise AgentError("A URL do Nó Master é inválida.") from None
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise AgentError("O agente exige HTTPS com certificado confiável.")
    if parsed.username is not None or parsed.password is not None:
        raise AgentError("Não inclua usuário ou senha na URL do Nó Master.")
    if parsed.query or parsed.fragment or "\\" in parsed.path:
        raise AgentError("A URL do Nó Master contém componentes não permitidos.")
    if any(part in {".", ".."} for part in parsed.path.split("/")):
        raise AgentError("A URL do Nó Master contém caminho inválido.")
    if port is not None and not 1 <= port <= 65535:
        raise AgentError("A porta HTTPS do Nó Master é inválida.")
    return value.rstrip("/")


def _normalize_name(value: str) -> str:
    if not isinstance(value, str):
        raise AgentError("Informe um nome amigável para o nó.")
    clean = unicodedata.normalize("NFC", " ".join(value.split()))
    if not _NAME_RE.fullmatch(clean):
        raise AgentError("O nome deve ter até 48 caracteres alfanuméricos, espaços, ponto, hífen ou sublinhado.")
    return clean


def _require_posix_secret_files() -> None:
    if os.name != "posix" or not hasattr(os, "O_NOFOLLOW"):
        raise AgentError("O armazenamento seguro das credenciais requer Linux/POSIX.")


def _private_directory(path: Path, create: bool) -> Path:
    _require_posix_secret_files()
    directory = path.expanduser().parent
    if create:
        directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    try:
        info = directory.lstat()
    except OSError:
        raise AgentError("Não foi possível acessar a pasta privada das credenciais.") from None
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise AgentError("A pasta das credenciais precisa ser um diretório real.")
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise AgentError("A pasta das credenciais deve pertencer ao usuário do agente e usar permissões 0700.")
    return directory


def ensure_credentials_target(path: Path) -> Path:
    target = path.expanduser()
    _private_directory(target, create=True)
    try:
        target.lstat()
    except FileNotFoundError:
        return target
    except OSError:
        raise AgentError("Não foi possível verificar o arquivo de credenciais.") from None
    raise AgentError("O arquivo de credenciais já existe; não será sobrescrito.")


def _validate_credentials_values(value: dict) -> NodeCredentials:
    expected = {"master_url", "name", "node_id", "token", "ca_file"}
    if not isinstance(value, dict) or set(value) != expected:
        raise AgentError("O arquivo de credenciais está malformado.")
    master_url = validate_master_url(value["master_url"])
    name = _normalize_name(value["name"])
    node_id = value["node_id"]
    token = value["token"]
    ca_file = value["ca_file"]
    if not isinstance(node_id, str) or not _NODE_ID_RE.fullmatch(node_id):
        raise AgentError("O arquivo de credenciais está malformado.")
    if not isinstance(token, str) or not _TOKEN_RE.fullmatch(token):
        raise AgentError("O arquivo de credenciais está malformado.")
    if ca_file is not None:
        if not isinstance(ca_file, str) or not ca_file:
            raise AgentError("O arquivo de credenciais está malformado.")
        ca_path = Path(ca_file)
        try:
            ca_info = ca_path.stat()
        except OSError:
            raise AgentError("O certificado CA configurado não está disponível.") from None
        if not stat.S_ISREG(ca_info.st_mode):
            raise AgentError("O certificado CA configurado não é um arquivo regular.")
        ca_file = str(ca_path)
    return NodeCredentials(master_url, name, node_id, token, ca_file)


def load_credentials(path: Path) -> NodeCredentials:
    target = path.expanduser()
    _private_directory(target, create=False)
    flags = os.O_RDONLY | os.O_NOFOLLOW
    try:
        fd = os.open(target, flags)
    except OSError:
        raise AgentError("Não foi possível abrir o arquivo privado de credenciais.") from None
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) & 0o077
            or info.st_size > 8192
        ):
            raise AgentError("O arquivo de credenciais deve ser regular, privado e pertencer ao usuário do agente.")
        with os.fdopen(fd, "r", encoding="utf-8", closefd=False) as stream:
            value = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise AgentError("O arquivo privado de credenciais está ilegível.") from None
    finally:
        os.close(fd)
    return _validate_credentials_values(value)


def _write_credentials(path: Path, credentials: NodeCredentials) -> None:
    target = ensure_credentials_target(path)
    payload = {
        "master_url": credentials.master_url,
        "name": credentials.name,
        "node_id": credentials.node_id,
        "token": credentials.token,
        "ca_file": credentials.ca_file,
    }
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    try:
        fd = os.open(target, flags, 0o600)
    except OSError:
        raise AgentError("Não foi possível criar o arquivo exclusivo de credenciais.") from None
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(fd)
        directory_fd = os.open(target.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        try:
            target.unlink()
        except OSError:
            pass
        raise AgentError("Não foi possível gravar com segurança as credenciais recebidas.") from None
    finally:
        os.close(fd)


class NivusApiClient:
    def __init__(
        self,
        master_url: str,
        ca_file: str | None = None,
        timeout: float = 10,
        opener=None,
    ):
        self.master_url = validate_master_url(master_url)
        if timeout <= 0 or timeout > 60:
            raise AgentError("O timeout precisa estar entre 0 e 60 segundos.")
        if ca_file is not None:
            ca_path = Path(ca_file).expanduser()
            try:
                ca_info = ca_path.stat()
            except OSError:
                raise AgentError("O certificado CA configurado não está disponível.") from None
            if not stat.S_ISREG(ca_info.st_mode):
                raise AgentError("O certificado CA configurado não é um arquivo regular.")
            ca_file = str(ca_path)
        self.timeout = timeout
        self.ca_file = ca_file
        if opener is None:
            try:
                context = ssl.create_default_context(cafile=ca_file)
            except (OSError, ssl.SSLError):
                raise AgentError("Não foi possível carregar o certificado CA informado.") from None
            self.opener = urllib.request.build_opener(
                urllib.request.HTTPSHandler(context=context),
                NoRedirectHandler(),
            )
        else:
            self.opener = opener

    @staticmethod
    def _raise_status(status: int, retry_after_seconds: int | None = None) -> None:
        if status == 401:
            raise AuthenticationRejected()
        if status == 409:
            raise SequenceConflict()
        if status in {408, 425, 429} or 500 <= status <= 599:
            raise RetryableApiError(status, retry_after_seconds)
        raise ApiError(status)

    @staticmethod
    def _retry_after(headers) -> int | None:
        if headers is None:
            return None
        raw = headers.get("Retry-After")
        if raw is None:
            return None
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return None
        return max(1, min(value, MAX_BACKOFF_SECONDS))

    def post_json(self, path: str, payload: dict, headers: dict | None = None) -> dict:
        if not path.startswith("/api/nodes/") or path.startswith("//"):
            raise AgentError("Caminho de API inválido.")
        request_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if headers:
            request_headers.update(headers)
        request = urllib.request.Request(
            self.master_url + path,
            data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            headers=request_headers,
            method="POST",
        )
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                status = int(response.status)
                response_headers = getattr(response, "headers", None)
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as error:
            self._raise_status(int(error.code), self._retry_after(error.headers))
        except urllib.error.URLError as error:
            reason = getattr(error, "reason", None)
            if isinstance(reason, ssl.SSLCertVerificationError):
                raise AgentError("O certificado HTTPS do Nó Master não é confiável; configure a CA correta.") from None
            raise TransportError("Falha temporária de rede ao acessar o Nó Master.") from None
        except (TimeoutError, ConnectionError, ssl.SSLError):
            raise TransportError("Falha temporária de rede ao acessar o Nó Master.") from None
        if not 200 <= status < 300:
            self._raise_status(status, self._retry_after(response_headers))
        if len(raw) > MAX_RESPONSE_BYTES:
            raise AgentError("A resposta da API excedeu o limite permitido.")
        try:
            result = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            raise AgentError("A API retornou uma resposta inválida.") from None
        if not isinstance(result, dict):
            raise AgentError("A API retornou uma resposta inválida.")
        return result


def pair_node(
    master_url: str,
    name: str,
    credentials_path: Path,
    code_reader: Callable[[str], str] = getpass.getpass,
    ca_file: str | None = None,
    opener=None,
) -> str:
    normalized_url = validate_master_url(master_url)
    normalized_name = _normalize_name(name)
    target = ensure_credentials_target(credentials_path)
    normalized_ca = None
    if ca_file:
        ca_path = Path(ca_file).expanduser()
        try:
            ca_info = ca_path.stat()
        except OSError:
            raise AgentError("O certificado CA configurado não está disponível.") from None
        if not stat.S_ISREG(ca_info.st_mode):
            raise AgentError("O certificado CA configurado não é um arquivo regular.")
        normalized_ca = str(ca_path.resolve())
    code = code_reader("Código de pareamento (entrada oculta): ")
    if not isinstance(code, str) or not _TOKEN_RE.fullmatch(code):
        raise AgentError("O código de pareamento informado é inválido.")
    client = NivusApiClient(normalized_url, normalized_ca, opener=opener)
    result = client.post_json(
        "/api/nodes/enroll",
        {"name": normalized_name},
        {"X-Nivus-Enrollment-Code": code},
    )
    values = {
        "master_url": normalized_url,
        "name": result.get("name", normalized_name),
        "node_id": result.get("node_id"),
        "token": result.get("token"),
        "ca_file": normalized_ca,
    }
    credentials = _validate_credentials_values(values)
    _write_credentials(target, credentials)
    return credentials.node_id


class NivusNodeAgent:
    def __init__(
        self,
        credentials: NodeCredentials,
        client: NivusApiClient | None = None,
        interval: int = DEFAULT_HEARTBEAT_SECONDS,
        sleep_fn: Callable[[float], None] = time.sleep,
        telemetry_collector: NodeTelemetryCollector | None = None,
        monotonic_fn: Callable[[], float] = time.monotonic,
    ):
        if not 5 <= interval <= 600:
            raise AgentError("O intervalo do heartbeat deve estar entre 5 e 600 segundos.")
        self.credentials = credentials
        self.client = client or NivusApiClient(
            credentials.master_url,
            ca_file=credentials.ca_file,
        )
        self.interval = interval
        self.sleep_fn = sleep_fn
        self.telemetry_collector = telemetry_collector or NodeTelemetryCollector()
        self.monotonic_fn = monotonic_fn

    def _renew_session(self) -> tuple[str, int]:
        result = self.client.post_json(
            "/api/nodes/session",
            {},
            {"X-Nivus-Node-Token": self.credentials.token},
        )
        session_id = result.get("session_id")
        sequence = result.get("next_sequence")
        if not isinstance(session_id, str) or not _TOKEN_RE.fullmatch(session_id):
            raise AgentError("A API retornou uma sessão inválida.")
        if type(sequence) is not int or sequence < 0:
            raise AgentError("A API retornou uma sequência inválida.")
        return session_id, sequence

    def _heartbeat(self, session_id: str, sequence: int) -> None:
        self.client.post_json(
            "/api/nodes/heartbeat",
            {
                "session_id": session_id,
                "sequence": sequence,
                "agent_version": AGENT_VERSION,
                "schema_version": SCHEMA_VERSION,
                "capabilities": list(self.telemetry_collector.capabilities),
            },
            {"X-Nivus-Node-Token": self.credentials.token},
        )

    def _send_telemetry(self, session_id: str, sequence: int, batch: dict) -> None:
        self.client.post_json(
            "/api/nodes/telemetry",
            {
                "session_id": session_id,
                "sequence": sequence,
                "schema_version": batch["schema_version"],
                "observed_at": batch["observed_at"],
                "samples": batch["samples"],
            },
            {"X-Nivus-Node-Token": self.credentials.token},
        )

    def _wait(self, seconds: float, stop_event=None) -> bool:
        if stop_event is not None:
            return not stop_event.wait(seconds)
        self.sleep_fn(seconds)
        return True

    def run(self, stop_event=None, max_heartbeats: int | None = None) -> int:
        if max_heartbeats is not None and max_heartbeats < 1:
            raise AgentError("O limite de heartbeats deve ser positivo.")
        session_id = None
        sequence = 0
        backoff = 1
        conflicts = 0
        sent = 0
        heartbeat_done = False
        pending_telemetry = None
        next_telemetry_at = 0.0

        while stop_event is None or not stop_event.is_set():
            if session_id is None:
                try:
                    session_id, sequence = self._renew_session()
                    backoff = 1
                    heartbeat_done = False
                    pending_telemetry = None
                except AuthenticationRejected:
                    raise
                except (RetryableApiError, TransportError) as error:
                    _LOG.warning("O Nó Master está temporariamente indisponível; nova tentativa programada.")
                    retry_after = getattr(error, "retry_after_seconds", None) or 0
                    if not self._wait(max(backoff, retry_after), stop_event):
                        break
                    backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
                    continue

            if not heartbeat_done:
                try:
                    self._heartbeat(session_id, sequence)
                except AuthenticationRejected:
                    raise
                except SequenceConflict:
                    conflicts += 1
                    if conflicts > 3:
                        raise AgentError(
                            "A sequência do nó conflitou repetidamente; confira se outro agente usa a mesma credencial."
                        )
                    session_id = None
                    continue
                except (RetryableApiError, TransportError) as error:
                    _LOG.warning("O Nó Master está temporariamente indisponível; nova tentativa programada.")
                    retry_after = getattr(error, "retry_after_seconds", None) or 0
                    if not self._wait(max(backoff, retry_after), stop_event):
                        break
                    backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
                    continue

                sequence += 1
                heartbeat_done = True
                if (
                    self.telemetry_collector.capabilities
                    and self.monotonic_fn() >= next_telemetry_at
                ):
                    pending_telemetry = self.telemetry_collector.collect()

            if pending_telemetry is not None:
                try:
                    self._send_telemetry(session_id, sequence, pending_telemetry)
                except AuthenticationRejected:
                    raise
                except SequenceConflict:
                    conflicts += 1
                    if conflicts > 3:
                        raise AgentError(
                            "A sequência do nó conflitou repetidamente; confira se outro agente usa a mesma credencial."
                        )
                    session_id = None
                    continue
                except (RetryableApiError, TransportError) as error:
                    _LOG.warning("A telemetria do nó está temporariamente indisponível; nova tentativa programada.")
                    retry_after = getattr(error, "retry_after_seconds", None) or 0
                    if not self._wait(max(backoff, retry_after), stop_event):
                        break
                    backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
                    continue
                sequence += 1
                next_telemetry_at = self.monotonic_fn() + DEFAULT_TELEMETRY_INTERVAL_SECONDS

            conflicts = 0
            backoff = 1
            heartbeat_done = False
            pending_telemetry = None
            sent += 1
            if max_heartbeats is not None and sent >= max_heartbeats:
                return sent
            if not self._wait(self.interval, stop_event):
                break
        return sent


def default_credentials_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    root = Path(config_home).expanduser() if config_home else Path.home() / ".config"
    if not root.is_absolute():
        root = Path.home() / ".config"
    return root / "nivus-node-agent" / "credentials.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agente mínimo de identidade e heartbeat do Nivus.")
    commands = parser.add_subparsers(dest="command", required=True)

    pair = commands.add_parser("pair", help="Consome um código de pareamento de uso único.")
    pair.add_argument("--master-url", required=True, help="URL HTTPS do Nó Master.")
    pair.add_argument("--name", required=True, help="Nome amigável do nó.")
    pair.add_argument("--credentials", type=Path, default=default_credentials_path())
    pair.add_argument("--ca-file", help="Certificado CA confiável para o Nó Master.")
    pair.set_defaults(handler=_run_pair)

    run = commands.add_parser("run", help="Envia heartbeats até receber Ctrl+C ou erro permanente.")
    run.add_argument("--credentials", type=Path, default=default_credentials_path())
    run.add_argument("--interval", type=int, default=DEFAULT_HEARTBEAT_SECONDS)
    run.set_defaults(handler=_run_agent)
    return parser


def _require_unprivileged_user() -> None:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise AgentError("Execute o agente como usuário sem privilégios de root.")


def _run_pair(args) -> int:
    _require_unprivileged_user()
    node_id = pair_node(
        args.master_url,
        args.name,
        args.credentials,
        ca_file=args.ca_file,
    )
    print(f"Nó pareado: {node_id}. Credenciais salvas com permissões restritas.")
    return 0


def _run_agent(args) -> int:
    _require_unprivileged_user()
    credentials = load_credentials(args.credentials)
    agent = NivusNodeAgent(credentials, interval=args.interval)
    _LOG.info("Agente iniciado para o nó %s.", credentials.node_id)
    agent.run()
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (AgentError, ValueError, EOFError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Agente encerrado pelo operador.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
