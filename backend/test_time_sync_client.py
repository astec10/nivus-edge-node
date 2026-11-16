import json
import socket
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from services import time_sync


class HostTimeSyncClientTests(unittest.TestCase):
    def test_unavailable_socket_is_reported_without_failing_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(time_sync, "SOCKET_PATH", Path(temp) / "missing.sock"):
                status = time_sync.get_host_time_sync_status()
        self.assertEqual(status["state"], "unavailable")
        self.assertFalse(status["can_configure"])
        self.assertEqual(len(status["suggested_servers"]), 3)

    def test_status_uses_the_local_json_socket_protocol(self):
        with tempfile.TemporaryDirectory() as temp:
            path = str(Path(temp) / "control.sock")
            received = []
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(path)
            server.listen(1)

            def serve_once():
                with server:
                    connection, _ = server.accept()
                    with connection:
                        with connection.makefile("rb") as reader:
                            received.append(json.loads(reader.readline()))
                        connection.sendall(
                            b'{"ok":true,"state":"synchronized","can_configure":true,'
                            b'"configured_servers":["a.ntp.br","b.ntp.br","c.ntp.br"],'
                            b'"suggested_servers":["a.ntp.br","b.ntp.br","c.ntp.br"],'
                            b'"has_rollback":false}\n'
                        )

            thread = threading.Thread(target=serve_once)
            thread.start()
            with patch.object(time_sync, "SOCKET_PATH", Path(path)):
                result = time_sync.get_host_time_sync_status()
            thread.join(timeout=3)

        self.assertFalse(thread.is_alive())
        self.assertEqual(received, [{"action": "status"}])
        self.assertEqual(result["state"], "synchronized")
        self.assertTrue(result["can_configure"])


if __name__ == "__main__":
    unittest.main()
