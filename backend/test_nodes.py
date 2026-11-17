import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from api.routers.nodes import NodeHeartbeat, NodeEnrollment
from pydantic import ValidationError
from services import nodes


class NodeRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(
            database, "DB_PATH", Path(self.temp_dir.name) / "nivus.db"
        )
        self.db_patch.start()
        database.init_db()
        self.now = 1_800_000_000.0

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def create_and_enroll(self, name, now=None):
        enrollment = nodes.create_node_enrollment(now=self.now if now is None else now)
        registered = nodes.enroll_node(
            enrollment["code"], name, now=self.now if now is None else now
        )
        return enrollment, registered

    def heartbeat(self, node, sequence, now=None, **overrides):
        values = {
            "node_token": node["token"],
            "session_id": node["session_id"],
            "sequence": sequence,
            "agent_version": "1.2.3",
            "schema_version": 1,
            "capabilities": ["telemetry.cpu", "telemetry.memory"],
            "now": self.now if now is None else now,
        }
        values.update(overrides)
        return nodes.process_node_heartbeat(**values)

    def test_enrollment_is_single_use_and_only_hash_is_stored(self):
        enrollment, registered = self.create_and_enroll("Edge Sala")
        self.assertNotEqual(registered["token"], enrollment["code"])
        self.assertEqual(len(registered["node_id"]), 32)
        conn = database.get_db_connection()
        try:
            enrollment_hash = conn.execute(
                "SELECT token_sha256 FROM node_enrollments WHERE enrollment_id = ?",
                (enrollment["enrollment_id"],),
            ).fetchone()["token_sha256"]
            node_hash = conn.execute(
                "SELECT token_sha256 FROM nodes WHERE node_id = ?",
                (registered["node_id"],),
            ).fetchone()["token_sha256"]
        finally:
            conn.close()
        self.assertEqual(enrollment_hash, hashlib.sha256(enrollment["code"].encode()).hexdigest())
        self.assertEqual(node_hash, hashlib.sha256(registered["token"].encode()).hexdigest())
        self.assertNotEqual(enrollment_hash, enrollment["code"])
        self.assertNotEqual(node_hash, registered["token"])
        with self.assertRaises(nodes.EnrollmentAuthenticationError):
            nodes.enroll_node(enrollment["code"], "Outro nó", now=self.now + 1)
        listed = nodes.list_nodes(now=self.now)
        self.assertNotIn("token", listed[0])
        self.assertNotIn("token_sha256", listed[0])
        self.assertNotIn("session_id", listed[0])
        self.assertNotIn("session_sha256", listed[0])

    def test_expired_enrollment_is_rejected(self):
        old = nodes.create_node_enrollment(now=self.now - nodes.ENROLLMENT_TTL_SECONDS - 1)
        with self.assertRaises(nodes.EnrollmentAuthenticationError):
            nodes.enroll_node(old["code"], "Edge Expirado", now=self.now)

    def test_two_nodes_get_distinct_ids_and_tokens(self):
        _, first = self.create_and_enroll("Edge A")
        _, second = self.create_and_enroll("Edge B")
        self.assertNotEqual(first["node_id"], second["node_id"])
        self.assertNotEqual(first["token"], second["token"])
        self.assertEqual(len(nodes.list_nodes(now=self.now)), 2)

    def test_heartbeat_uses_server_time_and_derives_online_state(self):
        _, node = self.create_and_enroll("Edge A")
        result = self.heartbeat(node, 0, now=self.now + 10)
        self.assertEqual(result["received_at"], nodes._iso(self.now + 10))
        self.assertEqual(nodes.list_nodes(now=self.now + 99)[0]["status"], "online")
        self.assertEqual(nodes.list_nodes(now=self.now + 101)[0]["status"], "offline")
        self.assertEqual(nodes.list_nodes(now=self.now + 101)[0]["last_seen"], nodes._iso(self.now + 10))

    def test_duplicate_or_out_of_order_sequence_is_rejected_without_refreshing_last_seen(self):
        _, node = self.create_and_enroll("Edge A")
        self.heartbeat(node, 4, now=self.now + 5)
        with self.assertRaises(nodes.HeartbeatReplayError):
            self.heartbeat(node, 4, now=self.now + 25)
        with self.assertRaises(nodes.HeartbeatReplayError):
            self.heartbeat(node, 3, now=self.now + 30)
        self.assertEqual(nodes.list_nodes(now=self.now + 30)[0]["last_seen"], nodes._iso(self.now + 5))

    def test_new_session_invalidates_old_session_and_resets_sequence(self):
        _, node = self.create_and_enroll("Edge A")
        self.heartbeat(node, 8)
        session = nodes.create_node_session(node["token"])
        self.assertNotEqual(session["session_id"], node["session_id"])
        with self.assertRaises(nodes.NodeAuthenticationError):
            self.heartbeat(node, 9)
        replacement = dict(node, session_id=session["session_id"])
        self.assertEqual(self.heartbeat(replacement, 0)["status"], "ok")

    def test_revocation_blocks_new_sessions_and_heartbeats(self):
        _, node = self.create_and_enroll("Edge A")
        self.assertTrue(nodes.revoke_node(node["node_id"], now=self.now + 1))
        self.assertFalse(nodes.revoke_node(node["node_id"], now=self.now + 2))
        with self.assertRaises(nodes.NodeAuthenticationError):
            nodes.create_node_session(node["token"])
        with self.assertRaises(nodes.NodeAuthenticationError):
            self.heartbeat(node, 0)
        self.assertEqual(nodes.list_nodes(now=self.now + 3)[0]["status"], "revoked")

    def test_request_schema_rejects_client_identity_clock_and_unknown_capability(self):
        with self.assertRaises(ValidationError):
            NodeHeartbeat.model_validate({
                "session_id": "s" * 43,
                "sequence": 0,
                "agent_version": "1.0.0",
                "schema_version": 1,
                "capabilities": ["telemetry.cpu"],
                "node_id": "client-chosen",
            })
        with self.assertRaises(ValidationError):
            NodeHeartbeat.model_validate({
                "session_id": "s" * 43,
                "sequence": 0,
                "agent_version": "1.0.0",
                "schema_version": 1,
                "capabilities": ["remote.shell"],
            })
        with self.assertRaises(ValidationError):
            NodeHeartbeat.model_validate({
                "session_id": "s" * 43,
                "sequence": True,
                "agent_version": "1.0.0",
                "schema_version": 1,
            })
        self.assertEqual(NodeEnrollment.model_validate({"name": "  Edge   A "}).name, "Edge A")


if __name__ == "__main__":
    unittest.main()
