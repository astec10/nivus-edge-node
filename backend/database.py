import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "nivus.db"
DB_PATH = Path(os.environ.get("NIVUS_DB_PATH", str(DEFAULT_DB_PATH)))


def get_db_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=15000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db_connection()
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node TEXT,
                timestamp INTEGER,
                cpu_percent REAL,
                memory_percent REAL,
                disk_percent REAL,
                temperature REAL,
                power_consumption REAL
            );
            CREATE TABLE IF NOT EXISTS actuator_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                topic TEXT,
                command TEXT
            );
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS alerts_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                alert_type TEXT,
                value REAL,
                threshold REAL,
                telemetry_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS login_attempts (
                username TEXT PRIMARY KEY,
                failures INTEGER DEFAULT 0,
                locked_until DATETIME
            );
            """
        )

        # Migrate existing databases without modifying existing alert records.
        alert_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(alerts_history)")
        }
        if "telemetry_id" not in alert_columns:
            conn.execute("ALTER TABLE alerts_history ADD COLUMN telemetry_id INTEGER")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_alert_telemetry_type "
            "ON alerts_history(telemetry_id, alert_type) WHERE telemetry_id IS NOT NULL"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp "
            "ON telemetry(timestamp)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?)",
            ("temp_threshold", "75"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?)",
            ("cpu_threshold", "90"),
        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
