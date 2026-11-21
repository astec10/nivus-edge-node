import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from api.schemas import AITaskControllerSettingsUpdate
from pydantic import SecretStr
from services import ai_providers, ai_task_controller


VALID_TASK_BODY = """### Objective
Update public documentation.

### Acceptance criteria
- The updated documentation is accurate.

### Allowed paths
- `docs/example.md`

### Module
documentation

### Risk
low

### Data classification
synthetic test data only

### Maximum runtime in minutes
5

### External model budget
free-tier model call — public/synthetic content only

### Human owner
@astec10

### Review gate
- [x] I understand that a human must review the PR before merge.
"""


def issue_payload(number=10, labels=None, body=VALID_TASK_BODY):
    return {
        "number": number,
        "title": "Synthetic documentation task",
        "html_url": f"https://github.com/astec10/nivus-edge-node/issues/{number}",
        "created_at": "2026-11-20T12:00:00Z",
        "state": "open",
        "body": body,
        "labels": [{"name": label} for label in (labels or ["ai:queued"])],
    }


PUBLIC_REPOSITORY = {"private": False}


class AITaskControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.db_patch = patch.object(database, "DB_PATH", self.root / "nivus.db")
        self.key_patch = patch.object(ai_providers, "KEY_FILE", self.root / "provider.key")
        self.db_patch.start()
        self.key_patch.start()
        ai_providers.KEY_FILE.write_bytes(b"K" * 32)
        database.init_db()
        ai_task_controller._set_state(
            state="stopped", last_poll_at=None, last_success_at=None,
            last_error_code=None, tasks=[],
        )

    def tearDown(self):
        self.key_patch.stop()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def save_config(self, **overrides):
        values = {
            "repository": "astec10/nivus-edge-node",
            "poll_interval_seconds": 60,
            "github_token": SecretStr("github_pat_synthetic_test"),
        }
        values.update(overrides)
        return ai_task_controller.update_settings(
            AITaskControllerSettingsUpdate(**values), "admin"
        )

    def configure_enabled(self):
        self.save_config()
        with patch.object(
            ai_task_controller,
            "_github_request",
            side_effect=[PUBLIC_REPOSITORY, []],
        ):
            ai_task_controller.test_connection("admin")
        ai_task_controller.set_enabled(True, "admin")

    def test_token_is_encrypted_and_never_returned(self):
        public = self.save_config()
        self.assertTrue(public["credential_configured"])
        self.assertNotIn("github_token", public)
        self.assertNotIn("credential_ciphertext", public)
        self.assertNotIn("github_pat_synthetic_test", repr(public))

        conn = database.get_db_connection()
        try:
            row = conn.execute(
                "SELECT credential_ciphertext FROM ai_task_controller_settings WHERE id=1"
            ).fetchone()
        finally:
            conn.close()
        self.assertNotIn("github_pat_synthetic_test", row["credential_ciphertext"])
        self.assertEqual(ai_task_controller._get_token(), "github_pat_synthetic_test")

    def test_token_change_disables_controller_and_requires_new_connection_test(self):
        self.configure_enabled()
        result = self.save_config(github_token=SecretStr("github_pat_replaced_test"))
        self.assertFalse(result["enabled"])
        self.assertEqual(result["last_test_status"], "not_tested")
        with self.assertRaisesRegex(ai_task_controller.TaskControllerError, "github_connection_not_tested"):
            ai_task_controller.set_enabled(True, "admin")

    def test_repository_change_disables_controller_and_clears_cached_tasks(self):
        self.configure_enabled()
        ai_task_controller._set_state(
            state="online", tasks=[{"number": 10}], last_success_at="2026-11-20T12:00:00+00:00"
        )

        result = self.save_config(repository="astec10/other-public-repository")

        self.assertFalse(result["enabled"])
        self.assertEqual(ai_task_controller.get_status()["state"], "disabled")
        self.assertEqual(ai_task_controller.get_status()["tasks"], [])
        self.assertIsNone(ai_task_controller.get_status()["last_success_at"])

    def test_connection_test_is_read_only_and_enables_after_success(self):
        self.save_config()
        with patch.object(
            ai_task_controller,
            "_github_request",
            side_effect=[PUBLIC_REPOSITORY, []],
        ) as request:
            result = ai_task_controller.test_connection("admin")
        self.assertEqual(result["status"], "success")
        self.assertFalse(result["enabled"])
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args_list[0].args[:3], (
            "GET", "/repos/astec10/nivus-edge-node", None
        ))
        self.assertEqual(request.call_args_list[1].args[0], "GET")
        self.assertIn("labels=ai%3Aqueued", request.call_args_list[1].args[1])
        enabled = ai_task_controller.set_enabled(True, "admin")
        self.assertTrue(enabled["enabled"])

    def test_manual_refresh_polls_github_and_requires_controller_enabled(self):
        with self.assertRaisesRegex(ai_task_controller.TaskControllerError, "controller_disabled"):
            ai_task_controller.refresh_now()

        self.configure_enabled()
        with patch.object(
            ai_task_controller,
            "_github_request",
            side_effect=[PUBLIC_REPOSITORY, [], PUBLIC_REPOSITORY, []],
        ) as request:
            result = ai_task_controller.refresh_now()

        self.assertEqual(result["state"], "online")
        self.assertEqual(request.call_count, 4)
        self.assertTrue(all(call.args[0] == "GET" for call in request.call_args_list))
        self.assertEqual(request.call_args_list[0].args[2], None)
        self.assertEqual(request.call_args_list[2].args[2], None)

    def test_poll_recovers_after_github_failure_without_losing_queue(self):
        self.configure_enabled()
        queued = issue_payload()
        ready = issue_payload(number=11, labels=["ai:queued", "ai:ready"])
        with patch.object(
            ai_task_controller,
            "_github_request",
            side_effect=[
                ai_task_controller.TaskControllerError("github_unreachable", "offline", 503),
                PUBLIC_REPOSITORY, [queued], PUBLIC_REPOSITORY, [ready],
            ],
        ):
            first = ai_task_controller.poll_once()
            second = ai_task_controller.poll_once()
        self.assertEqual(first["state"], "degraded")
        self.assertEqual(first["last_error_code"], "github_unreachable")
        self.assertEqual(second["state"], "online")
        self.assertEqual([task["number"] for task in second["tasks"]], [11, 10])
        self.assertEqual(second["tasks"][0]["queue_state"], "authorized")
        self.assertTrue(second["tasks"][1]["can_authorize"])

    def test_authorization_requires_explicit_confirmation(self):
        self.configure_enabled()
        with patch.object(ai_task_controller, "_github_request") as request:
            with self.assertRaisesRegex(
                ai_task_controller.TaskControllerError, "explicit_authorization_required"
            ):
                ai_task_controller.authorize_issue(10, False, "admin")
        request.assert_not_called()

    def test_disable_waits_for_in_flight_authorization(self):
        self.configure_enabled()
        issue_read_started = threading.Event()
        release_issue_read = threading.Event()
        disable_started = threading.Event()
        disable_finished = threading.Event()
        order = []
        order_lock = threading.Lock()

        def request(method, path, _token, payload=None):
            if method == "GET" and path == "/repos/astec10/nivus-edge-node":
                return PUBLIC_REPOSITORY
            if method == "GET" and path.endswith("/issues/10"):
                issue_read_started.set()
                if not release_issue_read.wait(timeout=3):
                    raise RuntimeError("test timed out waiting to release the issue read")
                return issue_payload()
            if method == "POST":
                with order_lock:
                    order.append("authorized")
                return {"labels": ["ai:queued", "ai:ready"]}
            raise AssertionError(f"Unexpected GitHub method: {method}")

        def disable_controller():
            disable_started.set()
            ai_task_controller.set_enabled(False, "admin")
            with order_lock:
                order.append("disabled")
            disable_finished.set()

        with patch.object(ai_task_controller, "_github_request", side_effect=request):
            authorizer = threading.Thread(
                target=ai_task_controller.authorize_issue,
                args=(10, True, "admin"),
            )
            authorizer.start()
            self.assertTrue(issue_read_started.wait(timeout=2))

            disabler = threading.Thread(target=disable_controller)
            disabler.start()
            self.assertTrue(disable_started.wait(timeout=2))
            try:
                disabled_before_authorization_finished = disable_finished.wait(timeout=0.25)
            finally:
                release_issue_read.set()
                authorizer.join(timeout=3)
                disabler.join(timeout=3)

        self.assertFalse(authorizer.is_alive())
        self.assertFalse(disabler.is_alive())
        self.assertFalse(disabled_before_authorization_finished)
        self.assertEqual(order, ["authorized", "disabled"])
        self.assertFalse(ai_task_controller.get_config()["enabled"])

    def test_disable_waits_for_in_flight_poll(self):
        self.configure_enabled()
        poll_started = threading.Event()
        release_poll = threading.Event()
        disable_started = threading.Event()
        disable_finished = threading.Event()

        def request(method, path, _token, payload=None):
            if method == "GET" and path == "/repos/astec10/nivus-edge-node":
                return PUBLIC_REPOSITORY
            if method == "GET" and "labels=ai%3Aqueued" in path:
                poll_started.set()
                if not release_poll.wait(timeout=3):
                    raise RuntimeError("test timed out waiting to release the queue poll")
                return [issue_payload()]
            if method == "GET" and "labels=ai%3Aready" in path:
                return []
            raise AssertionError(f"Unexpected GitHub request: {method} {path}")

        def disable_controller():
            disable_started.set()
            ai_task_controller.set_enabled(False, "admin")
            disable_finished.set()

        with patch.object(ai_task_controller, "_github_request", side_effect=request):
            poller = threading.Thread(target=ai_task_controller.poll_once)
            poller.start()
            self.assertTrue(poll_started.wait(timeout=2))

            disabler = threading.Thread(target=disable_controller)
            disabler.start()
            self.assertTrue(disable_started.wait(timeout=2))
            try:
                disabled_before_poll_finished = disable_finished.wait(timeout=0.25)
            finally:
                release_poll.set()
                poller.join(timeout=3)
                disabler.join(timeout=3)

        self.assertFalse(poller.is_alive())
        self.assertFalse(disabler.is_alive())
        self.assertFalse(disabled_before_poll_finished)
        status = ai_task_controller.get_status()
        self.assertFalse(status["enabled"])
        self.assertEqual(status["state"], "disabled")
        self.assertEqual(status["tasks"], [])

    def test_repository_change_waits_for_poll_and_discards_old_tasks(self):
        self.configure_enabled()
        poll_started = threading.Event()
        release_poll = threading.Event()
        update_started = threading.Event()
        update_finished = threading.Event()
        updated_config = {}

        def request(method, path, _token, payload=None):
            if method == "GET" and path == "/repos/astec10/nivus-edge-node":
                return PUBLIC_REPOSITORY
            if method == "GET" and "labels=ai%3Aqueued" in path:
                poll_started.set()
                if not release_poll.wait(timeout=3):
                    raise RuntimeError("test timed out waiting to release the queue poll")
                return [issue_payload()]
            if method == "GET" and "labels=ai%3Aready" in path:
                return []
            raise AssertionError(f"Unexpected GitHub request: {method} {path}")

        def update_repository():
            update_started.set()
            updated_config.update(
                self.save_config(repository="astec10/other-public-repository")
            )
            update_finished.set()

        with patch.object(ai_task_controller, "_github_request", side_effect=request):
            poller = threading.Thread(target=ai_task_controller.poll_once)
            poller.start()
            self.assertTrue(poll_started.wait(timeout=2))

            updater = threading.Thread(target=update_repository)
            updater.start()
            self.assertTrue(update_started.wait(timeout=2))
            try:
                update_before_poll_finished = update_finished.wait(timeout=0.25)
            finally:
                release_poll.set()
                poller.join(timeout=3)
                updater.join(timeout=3)

        self.assertFalse(poller.is_alive())
        self.assertFalse(updater.is_alive())
        self.assertFalse(update_before_poll_finished)
        self.assertEqual(updated_config["repository"], "astec10/other-public-repository")
        status = ai_task_controller.get_status()
        self.assertFalse(status["enabled"])
        self.assertEqual(status["state"], "disabled")
        self.assertEqual(status["repository"], "astec10/other-public-repository")
        self.assertEqual(status["tasks"], [])

    def test_authorization_adds_one_label_and_repeat_never_posts_again(self):
        self.configure_enabled()
        queued = issue_payload()
        with patch.object(
            ai_task_controller,
            "_github_request",
            side_effect=[
                PUBLIC_REPOSITORY, queued, PUBLIC_REPOSITORY, None,
            ],
        ) as request:
            result = ai_task_controller.authorize_issue(10, True, "admin")
        self.assertEqual(result["status"], "authorized")
        self.assertEqual(request.call_count, 4)
        method, path, _token, payload = request.call_args_list[3].args
        self.assertEqual(method, "POST")
        self.assertTrue(path.endswith("/issues/10/labels"))
        self.assertEqual(payload, {"labels": ["ai:ready"]})
        self.assertIsNone(request.call_args_list[0].args[2])
        self.assertIsNone(request.call_args_list[2].args[2])

        with patch.object(
            ai_task_controller,
            "_github_request",
            side_effect=[PUBLIC_REPOSITORY, issue_payload(labels=["ai:queued", "ai:ready"])],
        ) as repeated:
            again = ai_task_controller.authorize_issue(10, True, "admin")
        self.assertEqual(again["status"], "already_authorized")
        self.assertEqual(repeated.call_count, 2)
        self.assertEqual(repeated.call_args_list[1].args[0], "GET")

    def test_authorization_blocks_invalid_or_private_task_and_never_posts(self):
        self.configure_enabled()
        invalid = issue_payload(body=VALID_TASK_BODY.replace(
            "synthetic test data only", "home telemetry"
        ))
        with patch.object(
            ai_task_controller,
            "_github_request",
            side_effect=[PUBLIC_REPOSITORY, invalid],
        ) as request:
            with self.assertRaisesRegex(
                ai_task_controller.TaskControllerError, "issue_contract_invalid"
            ):
                ai_task_controller.authorize_issue(10, True, "admin")
        self.assertEqual(request.call_count, 2)
        self.assertEqual([call.args[0] for call in request.call_args_list], ["GET", "GET"])
        self.assertEqual(request.call_args_list[0].args[2], None)

    def test_uncertain_post_result_is_checked_and_not_retried(self):
        self.configure_enabled()
        queued = issue_payload()
        ready = issue_payload(labels=["ai:queued", "ai:ready"])
        with patch.object(
            ai_task_controller,
            "_github_request",
            side_effect=[
                PUBLIC_REPOSITORY, queued, PUBLIC_REPOSITORY,
                ai_task_controller.TaskControllerError("github_unreachable", "offline", 503),
                PUBLIC_REPOSITORY, ready,
            ],
        ) as request:
            result = ai_task_controller.authorize_issue(10, True, "admin")
        self.assertEqual(result["status"], "authorized")
        self.assertEqual(request.call_count, 6)
        self.assertEqual(
            [call.args[0] for call in request.call_args_list],
            ["GET", "GET", "GET", "POST", "GET", "GET"],
        )
        self.assertIsNone(request.call_args_list[0].args[2])
        self.assertIsNone(request.call_args_list[2].args[2])
        self.assertIsNone(request.call_args_list[4].args[2])

    def test_daily_authorization_limit_is_enforced_before_post(self):
        self.save_config(max_authorizations_per_day=1)
        with patch.object(
            ai_task_controller,
            "_github_request",
            side_effect=[PUBLIC_REPOSITORY, []],
        ):
            ai_task_controller.test_connection("admin")
        ai_task_controller.set_enabled(True, "admin")
        with patch.object(
            ai_task_controller,
            "_github_request",
            side_effect=[PUBLIC_REPOSITORY, issue_payload(), PUBLIC_REPOSITORY, None],
        ):
            first = ai_task_controller.authorize_issue(10, True, "admin")
        self.assertEqual(first["status"], "authorized")

        with patch.object(
            ai_task_controller,
            "_github_request",
            side_effect=[PUBLIC_REPOSITORY, issue_payload(number=11)],
        ) as request:
            with self.assertRaisesRegex(
                ai_task_controller.TaskControllerError, "daily_authorization_limit"
            ):
                ai_task_controller.authorize_issue(11, True, "admin")
        self.assertEqual(request.call_count, 2)
        self.assertEqual([call.args[0] for call in request.call_args_list], ["GET", "GET"])
        self.assertEqual(request.call_args_list[0].args[2], None)
        self.assertIn("/issues/11", request.call_args_list[1].args[1])


    def test_connection_rejects_private_repository_before_reading_issues(self):
        self.save_config()
        with patch.object(
            ai_task_controller, "_github_request", return_value={"private": True}
        ) as request:
            with self.assertRaisesRegex(
                ai_task_controller.TaskControllerError, "repository_not_public"
            ):
                ai_task_controller.test_connection("admin")

        request.assert_called_once()
        self.assertEqual(
            request.call_args.args[:3],
            ("GET", "/repos/astec10/nivus-edge-node", None),
        )
        self.assertEqual(ai_task_controller.get_config()["last_test_status"], "repository_not_public")

    def test_anonymous_not_found_repository_is_rejected_as_not_public(self):
        self.save_config()
        with patch.object(
            ai_task_controller,
            "_github_request",
            side_effect=ai_task_controller.TaskControllerError(
                "github_not_found", "not found", 404
            ),
        ) as request:
            with self.assertRaisesRegex(
                ai_task_controller.TaskControllerError, "repository_not_public"
            ):
                ai_task_controller.test_connection("admin")

        request.assert_called_once()
        self.assertEqual(request.call_args.args[2], None)
        self.assertEqual(ai_task_controller.get_config()["last_test_status"], "repository_not_public")


    def test_private_repository_does_not_expose_issue_data_or_authorize(self):
        self.configure_enabled()
        with patch.object(
            ai_task_controller, "_github_request", return_value={"private": True}
        ) as request:
            with self.assertRaisesRegex(
                ai_task_controller.TaskControllerError, "repository_not_public"
            ):
                ai_task_controller.authorize_issue(10, True, "admin")

        request.assert_called_once()
        self.assertEqual(
            request.call_args.args[:3],
            ("GET", "/repos/astec10/nivus-edge-node", None),
        )

    def test_poll_fails_closed_when_repository_is_private(self):
        self.configure_enabled()
        with patch.object(
            ai_task_controller, "_github_request", return_value={"private": True}
        ) as request:
            status = ai_task_controller.poll_once()

        self.assertEqual(status["state"], "degraded")
        self.assertEqual(status["last_error_code"], "repository_not_public")
        request.assert_called_once()
        self.assertEqual(
            request.call_args.args[:3],
            ("GET", "/repos/astec10/nivus-edge-node", None),
        )


if __name__ == "__main__":
    unittest.main()
