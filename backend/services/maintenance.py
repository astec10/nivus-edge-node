"""Volatile maintenance-mode state shared with the host telemetry agent."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from database import get_db_connection


DEFAULT_STATE_PATH = Path("/run/nivus-maintenance/state.json")
_state_lock = Lock()


class MaintenanceStateError(RuntimeError):
    """The shared maintenance state cannot be read or written safely."""


def state_path() -> Path:
    return Path(os.environ.get("NIVUS_MAINTENANCE_STATE_PATH", str(DEFAULT_STATE_PATH)))


def current_boot_id() -> str:
    try:
        value = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
    except OSError as exc:
        raise MaintenanceStateError("Identificador de inicialização indisponível.") from exc
    if not value or len(value) > 64:
        raise MaintenanceStateError("Identificador de inicialização inválido.")
    return value


def _default_state() -> dict:
    return {
        "enabled": False,
        "started_at": None,
        "updated_at": None,
        "actor": None,
        "boot_id": None,
        "paused_workloads": [],
    }


def read_maintenance_state(path: Path | None = None) -> dict:
    target = path or state_path()
    try:
        raw = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        return _default_state()
    except OSError as exc:
        raise MaintenanceStateError("Estado de manutenção indisponível.") from exc

    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MaintenanceStateError("Estado de manutenção inválido.") from exc
    if not isinstance(value, dict) or type(value.get("enabled")) is not bool:
        raise MaintenanceStateError("Estado de manutenção inválido.")
    actor = value.get("actor")
    if actor is not None and (not isinstance(actor, str) or len(actor) > 32):
        raise MaintenanceStateError("Responsável pelo estado de manutenção inválido.")
    return {
        "enabled": value["enabled"],
        "started_at": value.get("started_at") if value["enabled"] else None,
        "updated_at": value.get("updated_at"),
        "actor": actor,
        "boot_id": value.get("boot_id"),
        "paused_workloads": (
            ["host_telemetry", "mqtt_persistence"] if value["enabled"] else []
        ),
    }


def maintenance_enabled(path: Path | None = None) -> bool:
    """Fail open for collection if the control marker is malformed or unavailable."""
    try:
        return read_maintenance_state(path)["enabled"]
    except MaintenanceStateError:
        return False


def _write_state(state: dict, path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix=".maintenance-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(state, stream, separators=(",", ":"), ensure_ascii=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
                os.chmod(temporary_name, 0o644)
            os.replace(temporary_name, path)
        except Exception:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
            raise
    except OSError as exc:
        raise MaintenanceStateError("Não foi possível gravar o estado de manutenção.") from exc


def set_maintenance_mode(enabled: bool, actor: str) -> dict:
    if type(enabled) is not bool:
        raise ValueError("enabled must be a boolean")
    if not isinstance(actor, str) or not 1 <= len(actor) <= 32:
        raise ValueError("actor is invalid")

    with _state_lock:
        path = state_path()
        before = read_maintenance_state(path)
        if before["enabled"] == enabled:
            return before

        boot_id = current_boot_id()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        state = {
            "enabled": enabled,
            "started_at": now if enabled else None,
            "updated_at": now,
            "actor": actor,
            "boot_id": boot_id,
        }
        _write_state(state, path)
        conn = None
        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO maintenance_audit (actor, enabled, boot_id, reason) "
                "VALUES (?, ?, ?, 'user')",
                (actor, int(enabled), boot_id),
            )
            conn.commit()
        except Exception as exc:
            if before["updated_at"] is None and not before["enabled"]:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            else:
                _write_state(before, path)
            raise MaintenanceStateError("Não foi possível registrar a auditoria da manutenção.") from exc
        finally:
            if conn is not None:
                conn.close()
        return read_maintenance_state(path)


def record_boot_reset() -> bool:
    """Audit a maintenance session that ended because /run was cleared on reboot."""
    boot_id = current_boot_id()
    conn = get_db_connection()
    try:
        last = conn.execute(
            "SELECT enabled, boot_id FROM maintenance_audit ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if last is None or not last["enabled"] or last["boot_id"] == boot_id:
            return False
        conn.execute(
            "INSERT INTO maintenance_audit (actor, enabled, boot_id, reason) "
            "VALUES ('system', 0, ?, 'boot-reset')",
            (boot_id,),
        )
        conn.commit()
        return True
    finally:
        conn.close()
