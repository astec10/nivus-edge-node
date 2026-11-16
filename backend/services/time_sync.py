"""Unprivileged client for the root-owned host time-sync controller."""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path


DEFAULT_SERVERS = ["a.ntp.br", "b.ntp.br", "c.ntp.br"]
SOCKET_PATH = Path(os.environ.get("NIVUS_TIME_SYNC_SOCKET", "/run/nivus-time-sync/control.sock"))
MAX_RESPONSE_BYTES = 8192


class TimeSyncControllerError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _request(payload: dict) -> dict:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(22)
            connection.connect(str(SOCKET_PATH))
            connection.sendall((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
            with connection.makefile("rb") as reader:
                response_line = reader.readline(MAX_RESPONSE_BYTES + 1)
    except (OSError, TimeoutError) as exc:
        raise TimeSyncControllerError(
            "controller_unavailable",
            "O controlador NTP do host não está disponível.",
        ) from exc

    if not response_line or len(response_line) > MAX_RESPONSE_BYTES or not response_line.endswith(b"\n"):
        raise TimeSyncControllerError(
            "invalid_response",
            "O controlador NTP devolveu uma resposta inválida.",
        )
    try:
        response = json.loads(response_line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TimeSyncControllerError(
            "invalid_response",
            "O controlador NTP devolveu uma resposta inválida.",
        ) from exc
    if not isinstance(response, dict):
        raise TimeSyncControllerError(
            "invalid_response",
            "O controlador NTP devolveu uma resposta inválida.",
        )
    if response.get("ok") is not True:
        code = response.get("code")
        message = response.get("message")
        if not isinstance(code, str) or not isinstance(message, str):
            raise TimeSyncControllerError(
                "invalid_response",
                "O controlador NTP devolveu uma resposta inválida.",
            )
        raise TimeSyncControllerError(code, message)
    return response


def get_host_time_sync_status() -> dict:
    try:
        return _request({"action": "status"})
    except TimeSyncControllerError as exc:
        return {
            "ok": False,
            "state": "unavailable",
            "can_configure": False,
            "configured_servers": [],
            "suggested_servers": list(DEFAULT_SERVERS),
            "has_rollback": False,
            "message": exc.message,
        }


def apply_host_time_sync(servers: list[str]) -> dict:
    return _request({"action": "apply", "servers": servers})


def rollback_host_time_sync() -> dict:
    return _request({"action": "rollback"})
