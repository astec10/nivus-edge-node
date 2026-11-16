#!/usr/bin/env python3
"""Nivus' narrow root broker for Ubuntu systemd-timesyncd configuration."""

from __future__ import annotations

import ipaddress
import json
import os
import pwd
import re
import socket
import stat
import struct
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_SERVERS = ["a.ntp.br", "time.google.com", "time.cloudflare.com"]
MANAGED_MARKER = "# Managed by Nivus Edge Node. Do not edit manually."
SOCKET_PATH = Path(os.environ.get("NIVUS_TIME_SYNC_SOCKET", "/run/nivus-time-sync/control.sock"))
CONFIG_PATH = Path(os.environ.get(
    "NIVUS_TIMESYNCD_CONFIG",
    "/etc/systemd/timesyncd.conf.d/90-nivus.conf",
))
BACKUP_ROOT = Path(os.environ.get(
    "NIVUS_TIME_SYNC_BACKUP_DIR",
    "/var/backups/nivus-compose/time-sync",
))
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
    "ntpsec.service",
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
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise TimeSyncError(
                "invalid_servers",
                "Use nomes DNS válidos, sem URL, porta ou endereço IP.",
            )
        if (
            not host
            or len(host) > 253
            or any(not DNS_LABEL.fullmatch(label) for label in host.split("."))
        ):
            raise TimeSyncError(
                "invalid_servers",
                "Use nomes DNS válidos, sem URL, porta ou endereço IP.",
            )
        servers.append(host)
    if len(set(servers)) != 3:
        raise TimeSyncError("invalid_servers", "Os três servidores NTP precisam ser diferentes.")
    return servers


def render_config(servers: list[str]) -> bytes:
    normalized = validate_servers(servers)
    return (
        f"{MANAGED_MARKER}\n"
        "[Time]\n"
        "NTP=\n"
        f"NTP={' '.join(normalized)}\n"
    ).encode("ascii")


def _run(args: list[str], timeout: float = 4.0) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
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


def _timesyncd_unit_loaded() -> bool:
    result = _run([SYSTEMCTL, "show", "--property=LoadState", "--value", "systemd-timesyncd.service"])
    return result.returncode == 0 and result.stdout.strip() == "loaded"


def read_host_status() -> dict:
    other_client = any(service_active(unit) for unit in OTHER_NTP_CLIENTS)
    timesyncd = service_active("systemd-timesyncd.service")
    unit_available = timesyncd or _timesyncd_unit_loaded()
    if other_client:
        state = "managed_elsewhere"
        can_configure = False
        message = "Outro cliente de hora está ativo; o Nivus preservou essa configuração."
    elif not unit_available:
        state = "unavailable"
        can_configure = False
        message = "systemd-timesyncd não está instalado ou disponível neste host."
    elif not timesyncd:
        state = "inactive"
        can_configure = True
        message = "systemd-timesyncd está instalado, mas parado. Aplicar as fontes iniciará esse serviço."
    else:
        state = "synchronized" if _ntp_synchronized() else "degraded"
        can_configure = True
        message = (
            "O Ubuntu informa que o relógio está sincronizado."
            if state == "synchronized"
            else "systemd-timesyncd está ativo, mas ainda não confirmou sincronização."
        )
    return {
        "state": state,
        "can_configure": can_configure,
        "configured_servers": _managed_config_servers(),
        "suggested_servers": list(DEFAULT_SERVERS),
        "has_rollback": _latest_backup_exists(),
        "message": message,
    }


def _require_existing_directory(path: Path) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise TimeSyncError("path_unavailable", "Diretório protegido indisponível.") from exc
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.geteuid()
        or info.st_mode & 0o022
    ):
        raise TimeSyncError(
            "unsafe_path",
            "Diretório NTP precisa pertencer ao serviço privilegiado e não pode permitir escrita a terceiros.",
        )


def _ensure_private_directory(path: Path) -> None:
    try:
        path.mkdir(parents=True, mode=0o700, exist_ok=True)
        info = path.lstat()
    except OSError as exc:
        raise TimeSyncError("path_unavailable", "Diretório protegido indisponível.") from exc
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.geteuid()
        or info.st_mode & 0o077
    ):
        raise TimeSyncError(
            "unsafe_path",
            "Diretório NTP privado precisa pertencer ao serviço privilegiado.",
        )
    os.chmod(path, 0o700)


def _prepare_socket_directory(path: Path) -> None:
    try:
        path.mkdir(parents=True, mode=0o700, exist_ok=True)
        info = path.lstat()
    except OSError as exc:
        raise TimeSyncError("path_unavailable", "Diretório do socket NTP indisponível.") from exc
    if not stat.S_ISDIR(info.st_mode):
        raise TimeSyncError("unsafe_path", "O caminho do socket NTP não é um diretório.")
    if info.st_uid == 0:
        if info.st_mode & 0o022 or info.st_mode & 0o007:
            raise TimeSyncError("unsafe_path", "Diretório do socket NTP não é privado.")
    elif info.st_uid == RUNTIME_UID:
        if info.st_mode & 0o077:
            raise TimeSyncError("unsafe_path", "Diretório do socket NTP não é privado.")
    else:
        raise TimeSyncError("unsafe_path", "Diretório do socket NTP tem proprietário inesperado.")
    os.chown(path, RUNTIME_UID, RUNTIME_GID)
    os.chmod(path, 0o700)


def _systemd_timesync_uid() -> int:
    try:
        return pwd.getpwnam("systemd-timesync").pw_uid
    except KeyError as exc:
        raise TimeSyncError(
            "client_unavailable",
            "O usuário do systemd-timesyncd não está disponível no host.",
        ) from exc


def _acl_read_only_for_user(uid: int) -> bytes:
    undefined_id = 0xFFFFFFFF
    entries = (
        struct.pack("<HHI", 0x01, 0o6, undefined_id),
        struct.pack("<HHI", 0x02, 0o4, uid),
        struct.pack("<HHI", 0x04, 0o0, undefined_id),
        struct.pack("<HHI", 0x10, 0o4, undefined_id),
        struct.pack("<HHI", 0x20, 0o0, undefined_id),
    )
    return struct.pack("<I", 0x0002) + b"".join(entries)


def _atomic_write(
    path: Path,
    content: bytes,
    mode: int,
    *,
    readable_by_uid: int | None = None,
) -> None:
    _require_existing_directory(path.parent)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        os.fchmod(fd, mode)
        if readable_by_uid is not None:
            try:
                os.setxattr(fd, "system.posix_acl_access", _acl_read_only_for_user(readable_by_uid))
            except OSError as exc:
                raise TimeSyncError(
                    "acl_unavailable",
                    "O sistema de arquivos não oferece ACLs para leitura segura do NTP.",
                ) from exc
        with os.fdopen(fd, "wb") as target:
            target.write(content)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temp_path, path)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def _read_managed_config() -> bytes | None:
    if CONFIG_PATH.is_symlink():
        raise TimeSyncError(
            "config_conflict",
            "O arquivo NTP existente é um link simbólico; nada foi alterado.",
        )
    try:
        current = CONFIG_PATH.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise TimeSyncError(
            "config_unavailable",
            "Não foi possível ler a configuração NTP atual.",
        ) from exc
    first_line = current.splitlines()[:1]
    if not first_line or first_line[0].decode("ascii", errors="ignore").strip() != MANAGED_MARKER:
        raise TimeSyncError(
            "config_conflict",
            "Já existe uma configuração NTP nesse caminho que não pertence ao Nivus; nada foi alterado.",
        )
    return current


def _new_backup(previous: bytes | None) -> Path:
    _ensure_private_directory(BACKUP_ROOT)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = Path(tempfile.mkdtemp(prefix=f"{stamp}-", dir=BACKUP_ROOT))
    os.chmod(backup_dir, 0o700)
    metadata = {"previous_exists": previous is not None}
    _atomic_write(backup_dir / "state.json", (json.dumps(metadata) + "\n").encode(), 0o600)
    if previous is not None:
        _atomic_write(backup_dir / "previous.conf", previous, 0o600)
    return backup_dir


def _remember_backup(backup_dir: Path) -> bytes | None:
    if LATEST_BACKUP_FILE.is_symlink():
        raise TimeSyncError("backup_invalid", "O índice de backup NTP é inválido.")
    try:
        old_pointer = LATEST_BACKUP_FILE.read_bytes()
    except FileNotFoundError:
        old_pointer = None
    _atomic_write(LATEST_BACKUP_FILE, (str(backup_dir) + "\n").encode(), 0o600)
    return old_pointer


def _restore_pointer(old_pointer: bytes | None) -> None:
    if LATEST_BACKUP_FILE.is_symlink():
        raise TimeSyncError("backup_invalid", "O índice de backup NTP é inválido.")
    if old_pointer is None:
        try:
            LATEST_BACKUP_FILE.unlink()
        except FileNotFoundError:
            pass
    else:
        _atomic_write(LATEST_BACKUP_FILE, old_pointer, 0o600)


def _restart_timesyncd() -> bool:
    result = _run([SYSTEMCTL, "restart", "systemd-timesyncd.service"], timeout=15)
    if result.returncode != 0:
        return False
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        if service_active("systemd-timesyncd.service"):
            return True
        time.sleep(0.2)
    return False


def _restore_config(previous: bytes | None, timesync_uid: int | None = None) -> None:
    if CONFIG_PATH.is_symlink():
        raise TimeSyncError("config_conflict", "O arquivo NTP tornou-se um link simbólico.")
    if previous is None:
        try:
            CONFIG_PATH.unlink()
        except FileNotFoundError:
            pass
    else:
        _atomic_write(
            CONFIG_PATH,
            previous,
            0o600,
            readable_by_uid=timesync_uid if timesync_uid is not None else _systemd_timesync_uid(),
        )


def _ensure_configurable() -> None:
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


def apply_servers(value: object) -> dict:
    servers = validate_servers(value)
    _ensure_configurable()
    timesync_uid = _systemd_timesync_uid()
    previous = _read_managed_config()
    backup_dir = _new_backup(previous)
    old_pointer = _remember_backup(backup_dir)
    try:
        _ensure_configurable()
        _atomic_write(CONFIG_PATH, render_config(servers), 0o600, readable_by_uid=timesync_uid)
        if not _restart_timesyncd():
            raise TimeSyncError("restart_failed", "systemd-timesyncd não reiniciou.")
    except Exception as exc:
        if isinstance(exc, TimeSyncError) and exc.code == "acl_unavailable":
            try:
                _restore_pointer(old_pointer)
            except Exception as rollback_exc:
                raise TimeSyncError(
                    "rollback_failed",
                    "A escrita do ACL NTP falhou e o índice de backup não pôde ser restaurado.",
                ) from rollback_exc
            raise
        try:
            _restore_config(previous, timesync_uid)
            recovered = _restart_timesyncd()
            _restore_pointer(old_pointer)
        except Exception as rollback_exc:
            raise TimeSyncError(
                "rollback_failed",
                "A aplicação NTP falhou e a recuperação automática não pôde ser confirmada.",
            ) from rollback_exc
        if not recovered:
            raise TimeSyncError(
                "rollback_failed",
                "A aplicação NTP falhou e systemd-timesyncd não confirmou o retorno.",
            ) from exc
        if isinstance(exc, TimeSyncError):
            raise
        raise TimeSyncError("apply_failed", "Não foi possível aplicar a configuração NTP.") from exc

    result = read_host_status()
    result["ok"] = True
    result["message"] = (
        "Fontes NTP aplicadas. O estado pode ficar sem sincronização até uma fonte responder."
        if result["state"] != "synchronized"
        else "Fontes NTP aplicadas e relógio sincronizado."
    )
    return result


def _load_latest_backup() -> tuple[Path, dict]:
    if not _latest_backup_exists() or LATEST_BACKUP_FILE.is_symlink():
        raise TimeSyncError("no_rollback", "Não há backup NTP válido para restaurar.")
    try:
        target = Path(LATEST_BACKUP_FILE.read_text(encoding="utf-8").strip())
        resolved_root = BACKUP_ROOT.resolve(strict=True)
        resolved_target = target.resolve(strict=True)
        resolved_target.relative_to(resolved_root)
        info = target.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
            raise ValueError
        state_path = resolved_target / "state.json"
        previous_path = resolved_target / "previous.conf"
        if state_path.is_symlink() or previous_path.is_symlink():
            raise ValueError
        metadata = json.loads(state_path.read_text(encoding="utf-8"))
        if set(metadata) != {"previous_exists"} or not isinstance(metadata["previous_exists"], bool):
            raise ValueError
        if metadata["previous_exists"] != previous_path.is_file():
            raise ValueError
    except (OSError, ValueError, json.JSONDecodeError):
        raise TimeSyncError("backup_invalid", "O backup NTP não passou na validação.")
    return resolved_target, metadata


def rollback_last() -> dict:
    backup_dir, metadata = _load_latest_backup()
    _ensure_configurable()
    current = _read_managed_config()
    previous_path = backup_dir / "previous.conf"
    previous = previous_path.read_bytes() if metadata["previous_exists"] else None
    if metadata["previous_exists"]:
        if not previous or not previous.startswith((MANAGED_MARKER + "\n").encode("ascii")):
            raise TimeSyncError("backup_invalid", "O conteúdo do backup NTP não passou na validação.")
    _restore_config(previous)
    if not _restart_timesyncd():
        try:
            _restore_config(current)
            recovered = _restart_timesyncd()
        except Exception as exc:
            raise TimeSyncError(
                "rollback_failed",
                "O rollback NTP falhou e a configuração ativa não pôde ser recuperada.",
            ) from exc
        if not recovered:
            raise TimeSyncError(
                "rollback_failed",
                "O rollback NTP falhou; o estado do cliente de hora não foi confirmado.",
            )
        raise TimeSyncError(
            "rollback_failed",
            "O rollback NTP falhou; a configuração anterior à tentativa foi recuperada.",
        )
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
        credentials = connection.getsockopt(
            socket.SOL_SOCKET,
            socket.SO_PEERCRED,
            struct.calcsize("3i"),
        )
        _, uid, gid = struct.unpack("3i", credentials)
    except (OSError, struct.error):
        return False
    return uid == 0 or (uid == RUNTIME_UID and gid == RUNTIME_GID)


def _dispatch(request: object) -> dict:
    if not isinstance(request, dict):
        raise TimeSyncError("invalid_request", "Solicitação NTP inválida.")
    action = request.get("action")
    if action == "status" and set(request) == {"action"}:
        return {"ok": True, **read_host_status()}
    if action == "apply" and set(request) == {"action", "servers"}:
        return apply_servers(request["servers"])
    if action == "rollback" and set(request) == {"action"}:
        return rollback_last()
    raise TimeSyncError("invalid_request", "Ação NTP não permitida.")


def _handle_connection(connection: socket.socket) -> None:
    try:
        if not _peer_allowed(connection):
            response = {
                "ok": False,
                "code": "forbidden",
                "message": "Cliente NTP local não autorizado.",
            }
        else:
            connection.settimeout(20)
            with connection.makefile("rb") as reader:
                line = reader.readline(MAX_REQUEST_BYTES + 1)
            if not line or len(line) > MAX_REQUEST_BYTES or not line.endswith(b"\n"):
                response = {
                    "ok": False,
                    "code": "invalid_request",
                    "message": "Solicitação NTP inválida.",
                }
            else:
                try:
                    request = json.loads(line.decode("utf-8"))
                    response = _dispatch(request)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    response = {
                        "ok": False,
                        "code": "invalid_request",
                        "message": "Solicitação NTP inválida.",
                    }
                except TimeSyncError as exc:
                    response = {"ok": False, "code": exc.code, "message": exc.message}
        payload = (json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8")
        if len(payload) > MAX_REQUEST_BYTES:
            payload = b'{"ok":false,"code":"response_too_large","message":"Resposta NTP excedeu o limite."}\n'
        connection.sendall(payload)
    except (OSError, TimeoutError):
        return
    except Exception:
        try:
            connection.sendall(b'{"ok":false,"code":"internal_error","message":"Falha interna no controlador NTP."}\n')
        except OSError:
            return


def serve() -> None:
    if os.geteuid() != 0:
        raise SystemExit("O controlador de hora precisa executar como root.")
    if not 0 < RUNTIME_UID < 65536 or not 0 < RUNTIME_GID < 65536:
        raise SystemExit("UID/GID de runtime inválido.")
    socket_dir = SOCKET_PATH.parent
    _prepare_socket_directory(socket_dir)
    if os.path.lexists(SOCKET_PATH):
        raise SystemExit("O socket NTP já existe; o controlador recusou substituir o caminho.")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(str(SOCKET_PATH))
        os.chown(SOCKET_PATH, RUNTIME_UID, RUNTIME_GID)
        os.chmod(SOCKET_PATH, 0o600)
        server.listen(8)
        while True:
            connection, _ = server.accept()
            with connection:
                _handle_connection(connection)
    finally:
        server.close()
        try:
            SOCKET_PATH.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    serve()
