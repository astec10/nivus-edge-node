import json
import os
import stat
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from unittest.mock import patch

import database
from api.routers import nodes as node_routes
from fastapi import HTTPException
from node_agent.agent import (
    AgentError,
    AuthenticationRejected,
    NivusApiClient,
    NivusNodeAgent,
    load_credentials,
    pair_node,
)
from services import nodes


class FakeResponse:
    def __init__(self, status, value):
        self.status = status
        self.body = json.dumps(value).encode("utf-8")

    def read(self, limit=-1):
        return self.body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class TemporaryNodesApi:
    """In-process HTTPS-shaped transport backed by the real node API handlers and SQLite."""

    def __init__(self):
        self.fail_before = Counter()
        self.drop_after = Counter()
        self.session_ids = []
        self.request_paths = []

    @staticmethod
    def _headers(request):
        return {key.lower(): value for key, value in request.header_items()}

    def open(self, request, timeout):
        parsed = urlsplit(request.full_url)
        if parsed.scheme != "https":
            raise AssertionError("test agent attempted non-HTTPS transport")
        path = parsed.path
        self.request_paths.append(path)
        if self.fail_before[path]:
            self.fail_before[path] -= 1
            raise URLError("simulated network outage")

        headers = self._headers(request)
        payload = json.loads(request.data.decode("utf-8"))
        status = 200
        try:
            if path == "/api/nodes/enroll":
                result = node_routes.enroll(
                    node_routes.NodeEnrollment.model_validate(payload),
                    enrollment_code=headers["x-nivus-enrollment-code"],
                )
                status = 201
            elif path == "/api/nodes/session":
                result = node_routes.renew_session(
                    node_token=headers["x-nivus-node-token"]
                )
                self.session_ids.append(result["session_id"])
            elif path == "/api/nodes/heartbeat":
                result = node_routes.heartbeat(
                    node_routes.NodeHeartbeat.model_validate(payload),
                    node_token=headers["x-nivus-node-token"],
                )
                status = 202
            else:
                status, result = 404, {"detail": "not found"}
        except HTTPException as error:
            status, result = error.status_code, {"detail": error.detail}

        if status < 400 and self.drop_after[path]:
            self.drop_after[path] -= 1
            raise URLError("simulated response loss")
        return FakeResponse(status, result)


class NodeAgentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.db_patch = patch.object(database, "DB_PATH", self.root / "registry.db")
        self.db_patch.start()
        database.init_db()
        self.transport = TemporaryNodesApi()

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def pair(self, name):
        enrollment = nodes.create_node_enrollment()
        credential_path = self.root / name.replace(" ", "-") / "credentials.json"
        returned_id = pair_node(
            "https://master.example",
            name,
            credential_path,
            code_reader=lambda prompt: enrollment["code"],
            opener=self.transport,
        )
        credentials = load_credentials(credential_path)
        return enrollment, credential_path, returned_id, credentials

    def make_agent(self, credential_path, sleeps=None):
        credentials = load_credentials(credential_path)
        client = NivusApiClient(credentials.master_url, opener=self.transport)
        return NivusNodeAgent(
            credentials,
            client=client,
            sleep_fn=(sleeps.append if sleeps is not None else lambda _: None),
        )

    def test_two_clients_pair_with_distinct_server_ids_and_presence(self):
        _, first_path, first_id, first = self.pair("Edge A")
        _, second_path, second_id, second = self.pair("Edge B")
        self.assertNotEqual(first_id, second_id)
        self.assertNotEqual(first.token, second.token)

        self.make_agent(first_path).run(max_heartbeats=1)
        first_session = self.transport.session_ids[-1]
        self.make_agent(second_path).run(max_heartbeats=1)
        second_session = self.transport.session_ids[-1]
        self.assertNotEqual(first_session, second_session)

        listed = nodes.list_nodes()
        by_id = {entry["node_id"]: entry for entry in listed}
        self.assertEqual(by_id[first_id]["status"], "online")
        self.assertEqual(by_id[second_id]["status"], "online")
        self.assertEqual(by_id[first_id]["capabilities"], [])
        self.assertEqual(by_id[second_id]["capabilities"], [])
        self.assertNotIn("token", by_id[first_id])
        self.assertNotIn("token_sha256", by_id[first_id])

    def test_network_loss_and_lost_response_recover_without_losing_identity(self):
        enrollment, path, node_id, credentials = self.pair("Edge Rede")
        credential_text = path.read_text(encoding="utf-8")
        self.assertNotIn(enrollment["code"], credential_text)
        self.assertNotIn("session_id", credential_text)
        self.assertIn(credentials.token, credential_text)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)

        self.transport.fail_before["/api/nodes/heartbeat"] = 1
        sleeps = []
        self.make_agent(path, sleeps).run(max_heartbeats=1)
        self.assertEqual(sleeps, [1])
        self.assertEqual(nodes.list_nodes()[0]["status"], "online")

        old_session_count = len(self.transport.session_ids)
        self.transport.drop_after["/api/nodes/heartbeat"] = 1
        self.make_agent(path, []).run(max_heartbeats=1)
        self.assertGreaterEqual(len(self.transport.session_ids), old_session_count + 2)
        self.assertEqual(nodes.list_nodes()[0]["node_id"], node_id)
        self.assertEqual(nodes.list_nodes()[0]["status"], "online")

    def test_each_process_start_renews_session_and_revocation_stops_connection(self):
        _, path, node_id, _ = self.pair("Edge Revogável")
        self.make_agent(path).run(max_heartbeats=1)
        first_session = self.transport.session_ids[-1]
        self.make_agent(path).run(max_heartbeats=1)
        second_session = self.transport.session_ids[-1]
        self.assertNotEqual(first_session, second_session)

        self.assertTrue(nodes.revoke_node(node_id))
        with self.assertRaises(AuthenticationRejected):
            self.make_agent(path).run(max_heartbeats=1)

    def test_http_is_rejected_and_saved_secret_file_must_be_private(self):
        with self.assertRaises(AgentError):
            NivusApiClient("http://master.example", opener=self.transport)

        _, path, _, credentials = self.pair("Edge Permissão")
        self.assertNotIn(credentials.token, repr(credentials))
        path.chmod(0o644)
        with self.assertRaises(AgentError):
            load_credentials(path)

    def test_existing_credentials_are_never_overwritten_or_code_consumed(self):
        enrollment = nodes.create_node_enrollment()
        credential_path = self.root / "existing" / "credentials.json"
        credential_path.parent.mkdir(mode=0o700)
        credential_path.write_text("preserve", encoding="utf-8")
        credential_path.chmod(0o600)
        original_requests = len(self.transport.request_paths)
        prompted = []

        with self.assertRaises(AgentError):
            pair_node(
                "https://master.example",
                "Edge Existente",
                credential_path,
                code_reader=lambda prompt: prompted.append(prompt),
                opener=self.transport,
            )

        self.assertEqual(prompted, [])
        self.assertEqual(len(self.transport.request_paths), original_requests)
        self.assertEqual(credential_path.read_text(encoding="utf-8"), "preserve")
        self.assertEqual(
            nodes.enroll_node(enrollment["code"], "Código preservado")["name"],
            "Código preservado",
        )


if __name__ == "__main__":
    unittest.main()
