import datetime as dt
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4, uuid5

import database
from api.schemas import AIExecutorParallelRequest, AIExecutorRequest, AIProviderCreate
from pydantic import SecretStr
from services import ai_executor, ai_providers


class AIExecutorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.db_patch = patch.object(database, "DB_PATH", self.root / "nivus.db")
        self.key_patch = patch.object(ai_providers, "KEY_FILE", self.root / "provider.key")
        self.db_patch.start()
        self.key_patch.start()
        ai_providers.KEY_FILE.write_bytes(b"K" * 32)
        database.init_db()

    def tearDown(self):
        self.key_patch.stop()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_llama_cpp_preset_uses_internal_compose_dns(self):
        preset = next(
            item for item in ai_providers.provider_catalog()
            if item["id"] == "llama_cpp"
        )
        self.assertEqual(preset["base_url"], "http://llama-cpp:9931/v1")
        self.assertEqual(
            ai_providers.normalize_base_url(
                preset["base_url"], "local", preset["protocol"]
            ),
            "http://llama-cpp:9931/v1",
        )

    def test_llama_cpp_request_disables_reasoning(self):
        body = ai_executor._request_body(
            "openai-compatible",
            "nivus-local-qwen3.5-0.8b",
            "synthetic prompt",
            64,
            "llama_cpp",
        )
        self.assertEqual(body["reasoning_effort"], "none")
        self.assertEqual(body["max_completion_tokens"], 64)

    def create_provider(self, *, enabled=True, monthly_budget=5.0, max_requests_per_hour=30):
        today = dt.datetime.now(dt.timezone.utc).date()
        payload = AIProviderCreate(
            provider_type="openai",
            name="Synthetic test provider",
            protocol="openai-compatible",
            endpoint_scope="cloud",
            base_url="https://api.openai.com/v1",
            model_name="synthetic-model",
            responsible="unit tests",
            purpose="synthetic fixtures only",
            auth_method="bearer",
            api_key=SecretStr("synthetic-test-key"),
            monthly_budget_usd=monthly_budget,
            max_requests_per_hour=max_requests_per_hour,
            input_cost_per_million_usd=1.0,
            output_cost_per_million_usd=2.0,
            pricing_verified_on=today,
            allowed_data_classes=["public", "synthetic"],
        )
        provider = ai_providers.create_connection(payload, "admin")
        conn = database.get_db_connection()
        try:
            conn.execute(
                "UPDATE ai_provider_connections SET last_test_status='success', last_test_at=? WHERE id=?",
                (time.time(), provider["id"]),
            )
            conn.commit()
        finally:
            conn.close()
        if enabled:
            ai_providers.set_enabled(provider["id"], True, "admin")
        return provider

    def request(self, provider_id, **overrides):
        values = {
            "request_id": uuid4(),
            "task_id": "synthetic-task-001",
            "provider_id": provider_id,
            "prompt": "Return only the word synthetic.",
            "data_class": "synthetic",
            "task_budget_usd": 1.0,
            "max_output_tokens": 16,
        }
        values.update(overrides)
        return AIExecutorRequest(**values)

    def fake_target(self, _connection):
        return {
            "scheme": "https",
            "hostname": "api.openai.com",
            "port": 443,
            "path": "/v1/chat/completions",
            "pinned_address": "203.0.113.10",
        }

    def fake_completion(self, *_args, **_kwargs):
        return {
            "output": "synthetic",
            "input_tokens": 7,
            "output_tokens": 2,
            "http_status": 200,
        }

    def execution_rows(self):
        conn = database.get_db_connection()
        try:
            rows = conn.execute("SELECT * FROM ai_execution_requests").fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def test_disabled_provider_is_blocked_without_outbound_call(self):
        provider = self.create_provider(enabled=False)
        with patch.object(ai_executor, "_target", side_effect=self.fake_target), patch.object(
            ai_executor, "_perform_provider_request"
        ) as perform:
            with self.assertRaises(ai_executor.InferenceRequestError) as caught:
                ai_executor.execute(self.request(provider["id"]), "admin")
        self.assertEqual(caught.exception.code, "provider_disabled")
        perform.assert_not_called()
        self.assertEqual(self.execution_rows()[0]["status"], "blocked")

    def test_cloud_private_data_is_blocked_without_outbound_call(self):
        provider = self.create_provider()
        with patch.object(ai_executor, "_target", side_effect=self.fake_target), patch.object(
            ai_executor, "_perform_provider_request"
        ) as perform:
            with self.assertRaises(ai_executor.InferenceRequestError) as caught:
                ai_executor.execute(
                    self.request(provider["id"], data_class="home"), "admin"
                )
        self.assertEqual(caught.exception.code, "data_class_blocked")
        perform.assert_not_called()

    def test_credential_decryption_failure_fails_closed(self):
        provider = self.create_provider()
        with patch.object(ai_executor, "_target", side_effect=self.fake_target), patch.object(
            ai_executor, "_perform_provider_request"
        ) as perform, patch.object(
            ai_providers,
            "decrypt_credential",
            side_effect=ai_providers.ProviderSecretError("synthetic failure"),
        ):
            with self.assertRaises(ai_executor.InferenceRequestError) as caught:
                ai_executor.execute(self.request(provider["id"]), "admin")
        self.assertEqual(caught.exception.code, "credential_unavailable")
        perform.assert_not_called()
        self.assertEqual(self.execution_rows()[0]["failure_code"], "credential_unavailable")

    def test_budget_is_reserved_before_provider_call(self):
        provider = self.create_provider(monthly_budget=0.000001)
        with patch.object(ai_executor, "_target", side_effect=self.fake_target), patch.object(
            ai_executor, "_perform_provider_request"
        ) as perform:
            with self.assertRaises(ai_executor.InferenceRequestError) as caught:
                ai_executor.execute(self.request(provider["id"]), "admin")
        self.assertEqual(caught.exception.code, "monthly_budget_exceeded")
        perform.assert_not_called()
        self.assertEqual(self.execution_rows()[0]["status"], "blocked")


    def test_missing_credential_blocks_without_provider_call(self):
        provider = self.create_provider()
        conn = database.get_db_connection()
        try:
            conn.execute(
                "UPDATE ai_provider_connections SET credential_ciphertext=NULL WHERE id=?",
                (provider["id"],),
            )
            conn.commit()
        finally:
            conn.close()
        with patch.object(ai_executor, "_target", side_effect=self.fake_target), patch.object(
            ai_executor, "_perform_provider_request"
        ) as perform:
            with self.assertRaises(ai_executor.InferenceRequestError) as caught:
                ai_executor.execute(self.request(provider["id"]), "admin")
        self.assertEqual(caught.exception.code, "credential_missing")
        perform.assert_not_called()

    def test_hourly_limit_blocks_before_second_provider_call(self):
        provider = self.create_provider(max_requests_per_hour=1)
        with patch.object(ai_executor, "_target", side_effect=self.fake_target), patch.object(
            ai_executor, "_perform_provider_request", side_effect=self.fake_completion
        ) as perform:
            ai_executor.execute(self.request(provider["id"]), "admin")
            with self.assertRaises(ai_executor.InferenceRequestError) as caught:
                ai_executor.execute(
                    self.request(provider["id"], request_id=uuid4()), "admin"
                )
        self.assertEqual(caught.exception.code, "hourly_limit")
        self.assertEqual(perform.call_count, 1)

    def test_provider_error_does_not_trigger_fallback_or_retry(self):
        provider = self.create_provider()
        second = self.create_provider()
        error = ai_executor.InferenceRequestError(
            "provider_error", 502, "synthetic provider failure"
        )
        with patch.object(ai_executor, "_target", side_effect=self.fake_target), patch.object(
            ai_executor, "_perform_provider_request", side_effect=error
        ) as perform:
            with self.assertRaises(ai_executor.InferenceRequestError) as caught:
                ai_executor.execute(self.request(provider["id"]), "admin")
        self.assertEqual(caught.exception.code, "provider_error")
        self.assertEqual(perform.call_count, 1)
        self.assertNotEqual(provider["id"], second["id"])

    def test_timeout_keeps_reservation_and_does_not_store_prompt_or_secret(self):
        provider = self.create_provider()
        prompt = "private synthetic prompt that must not be stored"
        with patch.object(ai_executor, "_target", side_effect=self.fake_target), patch.object(
            ai_executor, "_perform_provider_request", side_effect=TimeoutError()
        ) as perform:
            with self.assertRaises(ai_executor.InferenceRequestError) as caught:
                ai_executor.execute(
                    self.request(provider["id"], prompt=prompt), "admin"
                )
        self.assertEqual(caught.exception.code, "timeout")
        perform.assert_called_once()
        row = self.execution_rows()[0]
        self.assertEqual(row["status"], "timeout")
        self.assertGreater(row["reserved_cost_micro_usd"], 0)
        self.assertNotIn(prompt, repr(row))
        self.assertNotIn("synthetic-test-key", repr(row))

    def test_cancellation_marks_sent_call_and_retains_uncertain_cost(self):
        provider = self.create_provider()
        call_started = threading.Event()
        finished = threading.Event()
        errors = []

        def wait_for_cancel(_connection, _secret, _target, _prompt, _limit, context, _request_id):
            context.request_sent = True
            call_started.set()
            if not context.cancelled.wait(3):
                raise AssertionError("cancel not observed")
            raise ai_executor._CancelledDuringCall()

        payload = self.request(provider["id"])

        def run():
            try:
                with patch.object(ai_executor, "_target", side_effect=self.fake_target), patch.object(
                    ai_executor, "_perform_provider_request", side_effect=wait_for_cancel
                ):
                    ai_executor.execute(payload, "admin")
            except Exception as error:
                errors.append(error)
            finally:
                finished.set()

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        self.assertTrue(call_started.wait(2))
        self.assertTrue(ai_executor.cancel_request(str(payload.request_id), "admin"))
        self.assertTrue(finished.wait(2))
        thread.join(timeout=1)
        self.assertTrue(errors)
        self.assertIsInstance(errors[0], ai_executor.InferenceRequestError)
        self.assertEqual(errors[0].code, "cancelled")
        row = self.execution_rows()[0]
        self.assertEqual(row["status"], "cancelled")
        self.assertGreater(row["settled_cost_micro_usd"], 0)



    def test_provider_output_redacts_exact_credential(self):
        raw = json.dumps({
            "choices": [{"message": {"content": "result synthetic-test-key"}}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 3},
        }).encode("utf-8")

        class FakeResponse:
            status = 200

            def getheader(self, name):
                return str(len(raw)) if name == "Content-Length" else None

            def read(self, _maximum):
                return raw

        class FakeConnection:
            sock = None

            def request(self, *_args, **_kwargs):
                return None

            def getresponse(self):
                return FakeResponse()

            def close(self):
                return None

        connection = FakeConnection()
        provider = {
            "protocol": "openai-compatible",
            "model_name": "synthetic-model",
            "timeout_seconds": 5,
            "auth_method": "bearer",
        }
        target = {
            "hostname": "api.openai.com",
            "pinned_address": "203.0.113.10",
            "port": 443,
            "scheme": "https",
            "path": "/v1/chat/completions",
        }
        with patch.object(ai_executor, "_CancellableHTTPS", return_value=connection):
            result = ai_executor._perform_provider_request(
                provider,
                "synthetic-test-key",
                target,
                "synthetic prompt",
                16,
                ai_executor._RequestContext(actor="admin"),
                str(uuid4()),
            )
        self.assertEqual(result["output"], "result [SEGREDO REMOVIDO]")
        self.assertNotIn("synthetic-test-key", repr(result))


    def test_gemini_uses_stateless_interactions_and_parses_completed_text(self):
        connection = {
            "protocol": "gemini",
            "model_name": "gemini-example",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "endpoint_scope": "cloud",
        }
        with patch.object(
            ai_providers, "_resolve_pinned_address", return_value="203.0.113.10"
        ):
            target = ai_executor._target(connection)
        self.assertEqual(target["path"], "/v1beta/interactions")

        request_body = ai_executor._request_body(
            "gemini", "gemini-example", "synthetic prompt", 32
        )
        self.assertEqual(request_body["model"], "gemini-example")
        self.assertEqual(request_body["input"], "synthetic prompt")
        self.assertIs(request_body["store"], False)
        self.assertEqual(
            request_body["generation_config"], {"max_output_tokens": 32}
        )

        output, input_tokens, output_tokens = ai_executor._provider_output(
            "gemini",
            {
                "status": "completed",
                "steps": [
                    {"type": "thought", "content": [{"type": "text", "text": "private reasoning"}]},
                    {"type": "model_output", "content": [{"type": "text", "text": "synthetic"}]},
                ],
                "usage": {
                    "total_input_tokens": 9,
                    "total_output_tokens": 3,
                    "total_thought_tokens": 2,
                },
            },
        )
        self.assertEqual(output, "synthetic")
        self.assertEqual(input_tokens, 9)
        self.assertEqual(output_tokens, 5)

    def test_gemini_incomplete_interaction_is_rejected(self):
        with self.assertRaises(ValueError):
            ai_executor._provider_output(
                "gemini",
                {
                    "status": "incomplete",
                    "steps": [{"type": "model_output", "content": [{"type": "text", "text": "partial"}]}],
                },
            )

    def test_admin_route_logs_no_prompt_or_credential(self):
        from api.routers import ai_executor as executor_router

        provider = self.create_provider()
        payload = self.request(
            provider["id"],
            prompt="synthetic prompt must not appear in logs",
        )
        with self.assertLogs("nivus.api.ai_executor", level="INFO") as captured:
            with patch.object(
                ai_executor, "execute", return_value={"status": "succeeded"}
            ):
                executor_router.complete(payload, admin="admin")
        joined = "\\n".join(captured.output)
        self.assertNotIn("synthetic prompt must not appear in logs", joined)
        self.assertNotIn("synthetic-test-key", joined)


    def test_openrouter_free_body_disables_fallback_and_data_collection(self):
        body = ai_executor._request_body(
            "openai-compatible", "openrouter/free", "synthetic prompt", 64, "openrouter"
        )
        self.assertEqual(body["model"], "openrouter/free")
        self.assertEqual(body["provider"], {
            "data_collection": "deny",
            "allow_fallbacks": False,
        })
        with self.assertRaises(ValueError):
            ai_executor._request_body(
                "openai-compatible", "paid-model", "synthetic prompt", 64, "openrouter"
            )

    def test_openrouter_target_rejects_non_free_model(self):
        connection = {
            "provider_type": "openrouter",
            "protocol": "openai-compatible",
            "model_name": "paid-model",
            "base_url": "https://openrouter.ai/api/v1",
            "endpoint_scope": "cloud",
        }
        with self.assertRaises(ValueError):
            ai_executor._target(connection)

    def test_parallel_calls_share_budget_and_run_concurrently(self):
        providers = [self.create_provider(), self.create_provider()]
        payload = AIExecutorParallelRequest(
            request_id=uuid4(),
            task_id="synthetic-parallel-001",
            provider_ids=[item["id"] for item in providers],
            prompt="Return a synthetic status.",
            data_class="synthetic",
            task_budget_usd=1.0,
            max_output_tokens=16,
        )
        barrier = threading.Barrier(2)
        observed = []
        lock = threading.Lock()

        def fake_execute(child, actor):
            barrier.wait(timeout=2)
            with lock:
                observed.append((child, actor))
            return {
                "request_id": str(child.request_id),
                "status": "succeeded",
                "output": "synthetic result",
            }

        with patch.object(ai_executor, "execute", side_effect=fake_execute):
            result = ai_executor.execute_parallel(payload, "admin")
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["success_count"], 2)
        self.assertEqual(len({str(item[0].request_id) for item in observed}), 2)
        self.assertTrue(all(item[0].task_id == payload.task_id for item in observed))
        self.assertTrue(all(item[0].task_budget_usd == payload.task_budget_usd for item in observed))
        self.assertTrue(all(actor == "admin" for _, actor in observed))

    def test_parallel_calls_fail_fast_when_global_capacity_is_full(self):
        providers = [self.create_provider(), self.create_provider()]
        payload = AIExecutorParallelRequest(
            request_id=uuid4(),
            task_id="synthetic-parallel-003",
            provider_ids=[item["id"] for item in providers],
            prompt="Synthetic status only.",
            data_class="synthetic",
            task_budget_usd=1.0,
            max_output_tokens=16,
        )
        with patch.object(ai_executor, "_ACTIVE_PARALLEL_CALLS", 3), patch.object(
            ai_executor, "execute"
        ) as execute:
            with self.assertRaises(ai_executor.InferenceRequestError) as caught:
                ai_executor.execute_parallel(payload, "admin")
        self.assertEqual(caught.exception.code, "parallel_capacity")
        execute.assert_not_called()

    def test_parallel_calls_reject_two_local_profiles(self):
        providers = [self.create_provider(), self.create_provider()]
        conn = database.get_db_connection()
        try:
            conn.executemany(
                "UPDATE ai_provider_connections SET endpoint_scope='local' WHERE id=?",
                [(item["id"],) for item in providers],
            )
            conn.commit()
        finally:
            conn.close()
        payload = AIExecutorParallelRequest(
            request_id=uuid4(),
            task_id="synthetic-parallel-002",
            provider_ids=[item["id"] for item in providers],
            prompt="Synthetic status only.",
            data_class="synthetic",
            task_budget_usd=1.0,
            max_output_tokens=16,
        )
        with patch.object(ai_executor, "execute") as execute:
            with self.assertRaises(ai_executor.InferenceRequestError) as caught:
                ai_executor.execute_parallel(payload, "admin")
        self.assertEqual(caught.exception.code, "parallel_local_limit")
        execute.assert_not_called()


    def parallel_request(self, providers, *, request_id=None, task_id="synthetic-parallel-task", budget=1.0):
        return AIExecutorParallelRequest(
            request_id=request_id or uuid4(),
            task_id=task_id,
            provider_ids=[item["id"] for item in providers],
            prompt="Return a synthetic status.",
            data_class="synthetic",
            task_budget_usd=budget,
            max_output_tokens=16,
        )

    def test_parallel_child_ids_are_deterministic_and_replay_does_not_call_providers(self):
        providers = [self.create_provider(), self.create_provider()]
        payload = self.parallel_request(providers, task_id="synthetic-parallel-replay")
        calls = []

        def complete(_connection, _secret, _target, _prompt, _limit, _context, request_id):
            calls.append(request_id)
            return self.fake_completion()

        with patch.object(ai_executor, "_target", side_effect=self.fake_target), patch.object(
            ai_executor, "_perform_provider_request", side_effect=complete
        ) as perform:
            first = ai_executor.execute_parallel(payload, "admin")
            replay = ai_executor.execute_parallel(payload, "admin")

        expected = [
            str(uuid5(payload.request_id, "nivus-provider:" + provider["id"]))
            for provider in providers
        ]
        self.assertEqual([item["request_id"] for item in first["results"]], expected)
        self.assertEqual([item["request_id"] for item in replay["results"]], expected)
        self.assertEqual(first["success_count"], 2)
        self.assertEqual(replay["failure_count"], 2)
        self.assertTrue(all(item["error"]["code"] == "duplicate_request" for item in replay["results"]))
        self.assertEqual(perform.call_count, 2)
        self.assertEqual(set(calls), set(expected))

    def test_parallel_isolates_one_provider_failure(self):
        providers = [self.create_provider(), self.create_provider()]
        failed_id = providers[0]["id"]
        payload = self.parallel_request(providers, task_id="synthetic-parallel-partial")

        def execute_one(child, _actor):
            if child.provider_id == failed_id:
                raise ai_executor.InferenceRequestError(
                    "provider_rate_limited", 429, "Synthetic rate limit."
                )
            return {
                "request_id": str(child.request_id),
                "provider_id": child.provider_id,
                "status": "succeeded",
                "output": "synthetic result",
            }

        with patch.object(ai_executor, "execute", side_effect=execute_one):
            result = ai_executor.execute_parallel(payload, "admin")

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 1)
        self.assertEqual(result["results"][0]["error"]["code"], "provider_rate_limited")
        self.assertEqual(result["results"][1]["status"], "succeeded")

    def test_parallel_reserves_shared_budget_before_concurrent_provider_calls(self):
        providers = [
            self.create_provider(monthly_budget=5.0),
            self.create_provider(monthly_budget=5.0),
        ]
        payload = self.parallel_request(
            providers, task_id="synthetic-parallel-budget", budget=0.003
        )
        with patch.object(ai_executor, "_target", side_effect=self.fake_target), patch.object(
            ai_executor, "_perform_provider_request", side_effect=self.fake_completion
        ) as perform:
            result = ai_executor.execute_parallel(payload, "admin")

        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 1)
        self.assertEqual(perform.call_count, 1)
        self.assertEqual(result["results"][1]["error"]["code"], "task_budget_exceeded")
        rows = [row for row in self.execution_rows() if row["task_id"] == payload.task_id]
        reserved = sum(
            row["settled_cost_micro_usd"] or row["reserved_cost_micro_usd"]
            for row in rows if row["status"] != "blocked"
        )
        self.assertLessEqual(reserved, 3000)

    def test_parallel_enforces_each_provider_hourly_quota(self):
        providers = [
            self.create_provider(max_requests_per_hour=1),
            self.create_provider(max_requests_per_hour=1),
        ]
        first_payload = self.parallel_request(
            providers, task_id="synthetic-parallel-quota-first"
        )
        second_payload = self.parallel_request(
            providers, task_id="synthetic-parallel-quota-second"
        )
        with patch.object(ai_executor, "_target", side_effect=self.fake_target), patch.object(
            ai_executor, "_perform_provider_request", side_effect=self.fake_completion
        ) as perform:
            first = ai_executor.execute_parallel(first_payload, "admin")
            second = ai_executor.execute_parallel(second_payload, "admin")

        self.assertEqual(first["success_count"], 2)
        self.assertEqual(second["failure_count"], 2)
        self.assertTrue(all(item["error"]["code"] == "hourly_limit" for item in second["results"]))
        self.assertEqual(perform.call_count, 2)

    def test_parallel_cancellation_targets_only_one_child_request(self):
        providers = [self.create_provider(), self.create_provider()]
        payload = self.parallel_request(providers, task_id="synthetic-parallel-cancel")
        cancelled_id = str(uuid5(payload.request_id, "nivus-provider:" + providers[0]["id"]))
        started = threading.Event()
        finished = threading.Event()
        result_box = []
        errors = []

        def provider_call(_connection, _secret, _target, _prompt, _limit, context, request_id):
            if request_id == cancelled_id:
                context.request_sent = True
                started.set()
                if not context.cancelled.wait(3):
                    raise AssertionError("child cancellation was not observed")
                raise ai_executor._CancelledDuringCall()
            return self.fake_completion()

        def run_batch():
            try:
                result_box.append(ai_executor.execute_parallel(payload, "admin"))
            except Exception as error:
                errors.append(error)
            finally:
                finished.set()

        with patch.object(ai_executor, "_target", side_effect=self.fake_target), patch.object(
            ai_executor, "_perform_provider_request", side_effect=provider_call
        ):
            thread = threading.Thread(target=run_batch, daemon=True)
            thread.start()
            self.assertTrue(started.wait(2))
            self.assertTrue(ai_executor.cancel_request(cancelled_id, "admin"))
            self.assertTrue(finished.wait(3))
            thread.join(timeout=1)

        self.assertFalse(errors)
        self.assertEqual(len(result_box), 1)
        result = result_box[0]
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 1)
        self.assertEqual(result["results"][0]["error"]["code"], "cancelled")
        self.assertEqual(result["results"][1]["status"], "succeeded")
        rows = {row["request_id"]: row for row in self.execution_rows()}
        self.assertEqual(rows[cancelled_id]["status"], "cancelled")

if __name__ == "__main__":
    unittest.main()
