import logging
import os
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_log_directory() -> Path:
    configured = os.environ.get("NIVUS_LOG_DIR")
    if configured:
        return Path(configured)
    database_path = Path(os.environ.get("NIVUS_DB_PATH", Path(__file__).resolve().parents[1] / "nivus.db"))
    return database_path.parent / "logs"


def configure_service_logger(service: str) -> logging.Logger:
    log_directory = get_log_directory()
    logger = logging.getLogger(f"nivus.{service}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not any(getattr(handler, "_nivus_log_handler", False) for handler in logger.handlers):
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler._nivus_log_handler = True
        logger.addHandler(stream_handler)
        try:
            log_directory.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_directory / f"{service}.log",
                maxBytes=1_000_000,
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError:
            logger.warning("Persistência de logs indisponível; usando saída do container.")

    return logger


def read_application_logs(limit: int) -> dict:
    entries = []
    for service in ("api", "worker"):
        path = get_log_directory() / f"{service}.log"
        tail = deque(maxlen=limit)
        try:
            with path.open("r", encoding="utf-8", errors="replace") as log_file:
                tail.extend(line.rstrip("\r\n") for line in log_file)
        except FileNotFoundError:
            continue
        except OSError:
            continue
        entries.extend((line.split(" ", 1)[0], f"[{service.upper()}] {line}") for line in tail)

    entries.sort(key=lambda entry: entry[0])
    logs = [message for _, message in entries[-limit:]]
    return {
        "logs": logs,
        "source": "Nivus API e worker MQTT",
        "status": "ok" if logs else "empty",
    }
