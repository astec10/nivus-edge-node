#!/usr/bin/env python3
"""Nivus' narrow root broker for Ubuntu systemd-timesyncd configuration."""

from __future__ import annotations

import json
import os
import re
import socket
import struct
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_SERVERS = ["a.ntp.br", "b.ntp.br", "c.ntp.br"]
MANAGED_MARKER = "# Managed by Nivus Edge Node. Do not edit manually."
SOCKET_PATH = Path(os.environ.get("NIVUS_TIME_SYNC_SOCKET", "/run/nivus-time-sync/control.sock"))
CONFIG_PATH = Path(
    os.environ.get(
        "NIVUS_TIMESYNCD_CONFIG",
        "/etc/systemd/timesyncd.conf.d/90-nivus.conf",
    )
)
BACKUP_ROOT = Path(
    os.environ.get(
        "NIVUS_TIME_SYNC_BACKUP_DIR",
        "/var/backups/nivus-compose/time-sync",
    )
)
LATEST_BACKUP_FILE = BACKUP_ROOT / "latest"
SYSTEMCTL = os.environ.get("NIVUS_SYSTEMCTL", "/usr/bin/systemctl")
TIMEDATECTL = os.environ.get("NIVUS_TIMEDATECTL", "/usr/bin/timedatectl")
RUNTIME_UID = int(os.environ.get("NIVUS_RUNTIME_UID", "12001"))
RUNTIME_GID = int(os.environ.get("NIVUS_RUNTIME_GID", "12001"))
MAX_REQUEST_BYTES = 8192
OTHER_NTP_CLIENTS = (
    "chrony.service",
    "chronyd.service",
    "ntp.service",
    "ntpd.service",
    "openntpd.service",
)
DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class TimeSyncError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def validate_servers(value: object) -> list[str]:
    if not isinstance(value, list) or len(value) != 3:
        raise TimeSyncError("invalid_servers", "Informe exatamente três servidores NTP.")
    servers: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise TimeSyncError("invalid_servers", "Nome de servidor NTP inválido.")
        host = item.strip().lower().rstrip(".")
        if not host or len(host) > 253 or any(not DNS_LABEL.fullmatch(label) for label in host.split(".")):
            raise TimeSyncError("invalid_servers", "Use nomes DNS válidos, sem URL, porta ou endereço IP.")
        servers.append(host)
    if len(set(servers)) != 3:
        raise TimeSyncError("invalid_servers", "Os três servidores NTP precisam ser diferentes.")
    return servers


def render_config(servers: list[str]) -> bytes:
    normalized = validate_servers(servers)
    text = (
        f"{MANAGED_MARKER}\n"
        "[Time]\n"
        "NTP=\n"
        f"NTP={' '.join(normalized)}\n"
    )
    return text.encode("ascii")


def _run(args: list[str], timeout: float = 4.0) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, capture_output=True, text=True, check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return subprocess.CompletedProcess(args, 127, "", "")


def service_active(unit: str) -> bool:
    return _run([SYSTEMCTL, "is-active", "--quiet", unit]).returncode == 0


def _ntp_synchronized() -> bool:
    result = _run([TIMEDATECTL, "show", "--property=NTPSynchronized", "--value"])
    return result.returncode == 0 and result.stdout.strip().lower() == "yes"


def _managed_config_servers() -> list[str]:
    try:
        lines = CONFIG_PATH.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError):
        return []
    if not lines or lines[0].strip() != MANAGED_MARKER:
        return []
    servers: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("NTP="):
            value = stripped.partition("=")[2].strip()
            servers = value.split() if value else []
    try:
        return validate_servers(servers)
    except TimeSyncError:
        return []


def _latest_backup_exists() -> bool:
    try:
        return LATEST_BACKUP_FILE.is_file() and not LATEST_BACKUP_FILE.is_symlink()
    except OSError:
        return False


def read_host_status() -> dict:
    other_client = any(service_active(unit) for unit in OTHER_NTP_CLIENTS)
    timesyncd = service_active("systemd-timesyncd.service")
    if other_client:
        state = "managed_elsewhere"
        can_configure = False
    elif not timesyncd:
        state = "unavailable"
        can_configure = False
    else:
        state = "synchronized" if _ntp_synchronized() else "degraded"
        can_configure = True
    return {
        "state": state,
        "can_configure": can_configure,
        "configured_servers": _managed_config_servers(),
        "suggested_servers": list(DEFAULT_SERVERS),
        "has_rollback": _latest_backup_exists(),
    }


def _atomic_write(path: Path, content: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, mode=0o755, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as target:
            target.write(content)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temp_path, path)
        os.chmod(path, mode)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def _read_managed_config() -> bytes | None:
    try:
        current = CONFIG_PATH.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise TimeSyncError("config_unavailable", "Não foi possível ler a configuração NTP atual.") from exc
    first_line = current.splitlines()[:1]
    if not first_line or first_line[0].decode("ascii", errors="ignore").strip() != MANAGED_MARKER:
        raise TimeSyncError(
            "config_conflict",
            "Já existe uma configuração NTP nesse caminho que não pertence ao Nivus; nada foi alterado.",
        )
    return current


def _new_backup(previous: bytes | None) -> Path:
    BACKUP_ROOT.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(BACKUP_ROOT, 0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = Path(tempfile.mkdtemp(prefix=f"{stamp}-", dir=BACKUP_ROOT))
    os.chmod(backup_dir, 0o700)
    metadata = {"previous_exists": previous is not None}
    _atomic_write(backup_dir / "state.json", (json.dumps(metadata) + "\n").encode(), 0o600)
    if previous is not None:
        _atomic_write(backup_dir / "previous.conf", previous, 0o600)
    return backup_dir


def _remember_backup(backup_dir: Path) -> bytes | None:
    try:
        old_pointer = LATEST_BACKUP_FILE.read_bytes()
    except FileNotFoundError:
        old_pointer = None
    _atomic_write(LATEST_BACKUP_FILE, (str(backup_dir) + "\n").encode(), 0o600)
    return old_pointer


def _restore_pointer(old_pointer: bytes | None) -> None:
    if old_pointer is None:
        try:
            LATEST_BACKUP_FILE.unlink()
        except FileNotFoundError:
            pass
    else:
        _atomic_write(LATEST_BACKUP_FILE, old_pointer, 0o600)


def _restart_timesyncd() -> bool:
    result = _run([SYSTEMCTL, "restart", "systemd-timesyncd.service"], timeout=10)
    if result.returncode != 0:
        return False
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        if service_active("systemd-timesyncd.service"):
            return True
        time.sleep(0.2)
    return False


def _restore_config(previous: bytes | None) -> None:
    if previous is None:
        try:
            CONFIG_PATH.unlink()
        except FileNotFoundError:
            pass
    else:
        _atomic_write(CONFIG_PATH, previous, 0o644)


def apply_servers(value: object) -> dict:
    servers = validate_servers(value)
    status = read_host_status()
    if status["state"] == "managed_elsewhere":
        raise TimeSyncError(
            "client_conflict",
            "Outro cliente NTP está ativo; o Nivus não modificou a configuração do host.",
        )
    if not status["can_configure"]:
        raise TimeSyncError(
            "client_unavailable",
            "systemd-timesyncd não está ativo; o Nivus não instalou nem substituiu outro cliente NTP.",
        )

    previous = _read_managed_config()
    backup_dir = _new_backup(previous)
    old_pointer = _remember_backup(backup_dir)
    try:
        _atomic_write(CONFIG_PATH, render_config(servers), 0o644)
        if not _restart_timesyncd():
            raise TimeSyncError("restart_failed", "systemd-timesyncd não reiniciou.")
    except Exception as exc:
        _restore_config(previous)
        _restart_timesyncd()
        _restore_pointer(old_pointer)
        if isinstance(exc, TimeSyncError):
            raise
        raise TimeSyncError("apply_failed", "Não foi possível aplicar a configuração NTP.") from exc

    result = read_host_status()
    result["ok"] = True
    result["message"] = (
        "Fontes NTP aplicadas. O estado pode ficar degradado enquanto nenhuma fonte responde."
        if result["state"] != "synchronized"
        else "Fontes NTP aplicadas e relógio sincronizado."
    )
    return result


def _load_latest_backup() -> tuple[Path, dict]:
    if not _latest_backup_exists():
        raise TimeSyncError("no_rollback", "Não há backup NTP para restaurar.")
    try:
        target = Path(LATEST_BACKUP_FILE.read_text(encoding="utf-8").strip())
        resolved_root = BACKUP_ROOT.resolve(strict=True)
        resolved_target = target.resolve(strict=True)
        resolved_target.relative_to(resolved_root)
        if target.is_symlink() or not resolved_target.is_dir():
            raise ValueError
        metadata = json.loads((resolved_target / "state.json").read_text(encoding="utf-8"))
        if set(metadata) != {"previous_exists"} or not isinstance(metadata["previous_exists"], bool):
            raise ValueError
    except (OSError, ValueError, json.JSONDecodeError):
        raise TimeSyncError("backup_invalid", "O backup NTP não passou na validação.")
    return resolved_target, metadata


def rollback_last() -> dict:
    backup_dir, metadata = _load_latest_backup()
    current = _read_managed_config()
    previous = (backup_dir / "previous.conf").read_bytes() if metadata["previous_exists"] else None
    if metadata["previous_exists"]:
        if not previous or not previous.startswith((MANAGED_MARKER + "\n").encode("ascii")):
            raise TimeSyncError("backup_invalid", "O conteúdo do backup NTP não passou na validação.")
    _restore_config(previous)
    if not _restart_timesyncd():
        _restore_config(current)
        _restart_timesyncd()
        raise TimeSyncError("rollback_failed", "O rollback NTP falhou; a configuração anterior foi recuperada.")
    try:
        LATEST_BACKUP_FILE.unlink()
    except FileNotFoundError:
        pass
    result = read_host_status()
    result["ok"] = True
    result["message"] = "A configuração NTP anterior foi restaurada."
    return result


def _peer_allowed(connection: socket.socket) -> bool:
    try:
        pid, uid, gid = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
    except (OSError, struct.error):
        return False
    return uid == 0 or (uid == RUNTIME_UID and gid == RUNTIME_GID)


def _dispatch(request: object) -> dict:
    if not isinstance(request, dict):
        raise TimeSyncError("invalid_request", "Solicitação NTP inválida.")
    action = request.get("action")
    if action == "status":
        return {"ok": True, **read_host_status()}
    if action == "apply":
        return apply_servers(request.get("servers"))
    if action == "rollback":
        return rollback_last()
    raise TimeSyncError("invalid_request", "Ação NTP não permitida.")


def _handle_connection(connection: socket.socket) -> None:
    try:
        if not _peer_allowed(connection):
            response = {"ok": False, "code": "forbidden", "message": "Cliente NTP local não autorizado."}
        else:
            connection.settimeout(8)
            reader = connection.makefile("rb")
            line = reader.readline(MAX_REQUEST_BYTES + 1)
            if not line or len(line) > MAX_REQUEST_BYTES or not line.endswith(b"\n"):
                response = {"ok": False, "code": "invalid_request", "message": "Solicitação NTP inválida."}
            else:
                try:
                    request = json.loads(line.decode("utf-8"))
                    response = _dispatch(request)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    response = {"ok": False, "code": "invalid_request", "message": "Solicitação NTP inválida."}
                except TimeSyncError as exc:
                    response = {"ok": False, "code": exc.code, "message": exc.message}
                finally:
                    reader.close()
        payload = (json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8")
        connection.sendall(payload[:MAX_REQUEST_BYTES])
    except (OSError, TimeoutError):
        return


def serve() -> None:
    if os.geteuid() != 0:
        raise SystemExit("O controlador de hora precisa executar como root.")
    if not 0 < RUNTIME_UID < 65536 or not 0 < RUNTIME_GID < 65536:
        raise SystemExit("UID/GID de runtime inválido.")
    socket_dir = SOCKET_PATH.parent
    socket_dir.mkdir(parents=True, mode=0o750, exist_ok=True)
    os.chown(socket_dir, 0, RUNTIME_GID)
    os.chmod(socket_dir, 0o750)
    if SOCKET_PATH.exists() or SOCKET_PATH.is_symlink():
        if not SOCKET_PATH.is_socket():
            raise SystemExit("O caminho do socket NTP já existe e não é um socket.")
        SOCKET_PATH.unlink()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(SOCKET_PATH))
    os.chown(SOCKET_PATH, 0, RUNTIME_GID)
    os.chmod(SOCKET_PATH, 0o660)
    server.listen(8)
    while True:
        connection, _ = server.accept()
        with connection:
            _handle_connection(connection)


if __name__ == "__main__":
    serve()
