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
                host_battery_percent REAL,
                host_battery_power_plugged INTEGER,
                host_battery_source TEXT,
                temperature REAL,
                temperature_source TEXT,
                cpu_hotspot_temperature REAL,
                cpu_hotspot_source TEXT,
                motherboard_temperature REAL,
                motherboard_temperature_source TEXT,
                gpu_temperature REAL,
                gpu_temperature_source TEXT,
                gpu_hotspot_temperature REAL,
                gpu_hotspot_source TEXT,
                power_consumption REAL
            );
            CREATE TABLE IF NOT EXISTS actuator_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                topic TEXT,
                command TEXT,
                source TEXT NOT NULL DEFAULT 'manual'
            );
            CREATE TABLE IF NOT EXISTS mobile_battery_devices (
                device_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                token_sha256 TEXT NOT NULL UNIQUE,
                active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_battery_percent INTEGER CHECK (last_battery_percent BETWEEN 0 AND 100),
                last_observed_at REAL,
                last_off_attempt_at REAL,
                low_battery_latched INTEGER NOT NULL DEFAULT 0 CHECK (low_battery_latched IN (0, 1))
            );
            CREATE TABLE IF NOT EXISTS mobile_battery_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                received_at TEXT NOT NULL,
                observed_at REAL NOT NULL,
                battery_percent INTEGER NOT NULL CHECK (battery_percent BETWEEN 0 AND 100),
                action TEXT NOT NULL,
                broker_accepted INTEGER NOT NULL DEFAULT 0 CHECK (broker_accepted IN (0, 1)),
                FOREIGN KEY (device_id) REFERENCES mobile_battery_devices(device_id)
            );
            CREATE INDEX IF NOT EXISTS idx_mobile_battery_events_device_id
                ON mobile_battery_events(device_id, id DESC);
            CREATE TABLE IF NOT EXISTS node_enrollments (
                enrollment_id TEXT PRIMARY KEY,
                token_sha256 TEXT NOT NULL UNIQUE,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                consumed_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_node_enrollments_expiry
                ON node_enrollments(expires_at);
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                token_sha256 TEXT NOT NULL UNIQUE,
                active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                created_at REAL NOT NULL,
                last_seen REAL,
                revoked_at REAL,
                session_sha256 TEXT,
                last_sequence INTEGER NOT NULL DEFAULT -1 CHECK (last_sequence >= -1),
                agent_version TEXT,
                schema_version INTEGER,
                capabilities_json TEXT NOT NULL DEFAULT '[]'
            );
            CREATE INDEX IF NOT EXISTS idx_nodes_last_seen
                ON nodes(last_seen);
            CREATE TABLE IF NOT EXISTS node_telemetry_batches (
                batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL,
                session_sha256 TEXT NOT NULL,
                sequence INTEGER NOT NULL CHECK (sequence >= 0),
                schema_version INTEGER NOT NULL CHECK (schema_version >= 1),
                observed_at REAL NOT NULL,
                received_at REAL NOT NULL,
                payload_sha256 TEXT NOT NULL,
                UNIQUE(node_id, session_sha256, sequence),
                FOREIGN KEY(node_id) REFERENCES nodes(node_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_node_telemetry_batches_node_received
                ON node_telemetry_batches(node_id, received_at DESC);
            CREATE TABLE IF NOT EXISTS node_telemetry_samples (
                sample_id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                metric TEXT NOT NULL,
                value REAL,
                unit TEXT NOT NULL,
                quality TEXT NOT NULL CHECK (quality IN ('measured', 'estimated', 'unavailable')),
                CHECK (
                    (quality = 'unavailable' AND value IS NULL)
                    OR (quality IN ('measured', 'estimated') AND value IS NOT NULL)
                ),
                UNIQUE(batch_id, metric),
                FOREIGN KEY(batch_id) REFERENCES node_telemetry_batches(batch_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_node_telemetry_samples_batch
                ON node_telemetry_samples(batch_id, metric);
            CREATE TABLE IF NOT EXISTS maintenance_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                actor TEXT NOT NULL,
                enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
                boot_id TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT 'user'
            );
            CREATE TABLE IF NOT EXISTS ai_provider_connections (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                provider_type TEXT NOT NULL,
                protocol TEXT NOT NULL,
                endpoint_scope TEXT NOT NULL CHECK (endpoint_scope IN ('cloud', 'local')),
                base_url TEXT NOT NULL,
                model_name TEXT NOT NULL,
                responsible TEXT NOT NULL,
                purpose TEXT NOT NULL,
                auth_method TEXT NOT NULL,
                credential_ciphertext TEXT,
                enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
                monthly_budget_usd REAL,
                input_cost_per_million_usd REAL,
                output_cost_per_million_usd REAL,
                pricing_verified_on TEXT,
                max_requests_per_hour INTEGER NOT NULL DEFAULT 30,
                timeout_seconds INTEGER NOT NULL DEFAULT 10,
                allowed_data_classes_json TEXT NOT NULL DEFAULT '["public","synthetic"]',
                last_test_status TEXT NOT NULL DEFAULT 'not_tested',
                last_test_at REAL,
                created_by TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ai_provider_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id TEXT,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                outcome TEXT NOT NULL DEFAULT 'ok',
                created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_ai_provider_audit_created
                ON ai_provider_audit(created_at DESC);
            CREATE TABLE IF NOT EXISTS ai_execution_tasks (
                task_id TEXT PRIMARY KEY,
                actor TEXT NOT NULL,
                budget_micro_usd INTEGER NOT NULL DEFAULT 0 CHECK (budget_micro_usd >= 0),
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ai_execution_requests (
                request_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                actor TEXT NOT NULL,
                model_name TEXT NOT NULL,
                data_class TEXT NOT NULL,
                status TEXT NOT NULL,
                reserved_cost_micro_usd INTEGER NOT NULL DEFAULT 0 CHECK (reserved_cost_micro_usd >= 0),
                settled_cost_micro_usd INTEGER CHECK (settled_cost_micro_usd >= 0),
                input_tokens INTEGER,
                output_tokens INTEGER,
                duration_ms INTEGER,
                failure_code TEXT,
                request_sent INTEGER NOT NULL DEFAULT 0 CHECK (request_sent IN (0, 1)),
                cancel_requested_at REAL,
                created_at REAL NOT NULL,
                completed_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_ai_execution_provider_created
                ON ai_execution_requests(provider_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_ai_execution_task_created
                ON ai_execution_requests(task_id, created_at DESC);
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
                role TEXT NOT NULL,
                must_change_password INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS login_attempts (
                username TEXT PRIMARY KEY,
                failures INTEGER DEFAULT 0,
                locked_until DATETIME
            );
            """
        )

        provider_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(ai_provider_connections)")
        }
        for column, definition in (
            ("input_cost_per_million_usd", "REAL"),
            ("output_cost_per_million_usd", "REAL"),
            ("pricing_verified_on", "TEXT"),
        ):
            if column not in provider_columns:
                conn.execute(
                    f"ALTER TABLE ai_provider_connections ADD COLUMN {column} {definition}"
                )

        actuator_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(actuator_audit)")
        }
        if "source" not in actuator_columns:
            conn.execute(
                "ALTER TABLE actuator_audit ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'"
            )

        # Migrate account records without forcing existing users to rotate passwords.
        user_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(users)")
        }
        if "must_change_password" not in user_columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0"
            )

        # Migrate existing databases without modifying existing alert records.
        alert_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(alerts_history)")
        }
        if "telemetry_id" not in alert_columns:
            conn.execute("ALTER TABLE alerts_history ADD COLUMN telemetry_id INTEGER")
        telemetry_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(telemetry)")
        }
        for column, definition in (
            ("host_battery_percent", "REAL"),
            ("host_battery_power_plugged", "INTEGER"),
            ("host_battery_source", "TEXT"),
            ("temperature_source", "TEXT"),
            ("cpu_hotspot_temperature", "REAL"),
            ("cpu_hotspot_source", "TEXT"),
            ("motherboard_temperature", "REAL"),
            ("motherboard_temperature_source", "TEXT"),
            ("gpu_temperature", "REAL"),
            ("gpu_temperature_source", "TEXT"),
            ("gpu_hotspot_temperature", "REAL"),
            ("gpu_hotspot_source", "TEXT"),
        ):
            if column not in telemetry_columns:
                conn.execute(f"ALTER TABLE telemetry ADD COLUMN {column} {definition}")
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
