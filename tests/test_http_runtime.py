import json
import argparse
import contextlib
import io
import multiprocessing
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ccw.errors import StateError, ValidationError
from ccw.http_runtime import execute_http, preflight_http, recover_http, public_status, process_lock
from ccw.state import create_run, authorize_run, load_run, save_run, capture_raw, set_compression, set_verification, finalize_run
from ccw.storage import write_json, read_json
from ccw.cli import command_run_compress, command_run_verify


CONFIG = dict(model="chat-pro", account_hash="a" * 64, token="private-token",
              expected_connector="connector", expected_tool="git_status")
ADAPTER = dict(family="oracle-style", kind="web-http", identity="http-executor",
               capabilities=["send", "observe", "capture", "stable_identity", "chat_pro"])


class Client:
    def __init__(self, marker=None, crash=False, disconnect=False, verified=True):
        self.marker, self.crash, self.disconnect, self.verified = marker, crash, disconnect, verified
        self.posts = 0

    def probe(self):
        return dict(state="ready", account_hash=CONFIG["account_hash"])

    def submit(self, intent):
        self.posts += 1
        if self.marker:
            with open(self.marker, "a") as handle:
                handle.write("post\n")
        if self.crash:
            os._exit(8)
        if self.disconnect:
            raise ConnectionError("private-token raw body must never escape")
        return self.recover(intent)

    def recover(self, locator):
        return dict(state="complete", complete=True, acknowledged=True,
                    identity_verified=True, account_hash=CONFIG["account_hash"],
                    text="Review complete", actual_model="chat-pro",
                    locator={**locator, "conversation_id": "private-conversation"},
                    route_evidence=dict(actual_model="chat-pro", provenance="conversation_mapping_metadata") if self.verified else {},
                    terminal_evidence=dict(message_id="private-assistant", status="finished_successfully", end_turn=True),
                    tool_evidence=[dict(source="http-server", connector="connector", tool="git_status",
                        read_only=True, message_id="private-tool", provenance="conversation_mapping_tool_metadata")] if self.verified else [])


def contender(run_id, marker, crash=False):
    try:
        execute_http(run_id, CONFIG, client=Client(marker=marker, crash=crash))
    except StateError:
        pass


class WaitingClient(Client):
    def __init__(self, marker, entered, release):
        super().__init__(marker=marker)
        self.entered, self.release = entered, release

    def submit(self, intent):
        self.entered.set()
        if not self.release.wait(10):
            raise RuntimeError("test deadline")
        return super().submit(intent)


def waiting_execute(run_id, marker, entered, release):
    execute_http(run_id, CONFIG, client=WaitingClient(marker, entered, release))


def competing_authorize(run_id, result):
    try:
        authorize_run(run_id)
        result.put("authorized")
    except StateError:
        result.put("rejected")


class RegeneratedClient(Client):
    def recover(self, locator):
        result = super().recover(locator)
        result["text"] = "Regenerated review B"
        result["terminal_evidence"]["message_id"] = "private-assistant-B"
        return result


def waiting_artifact(run_id, stage, entered, release):
    import ccw.cli as cli
    function = cli.compress_response if stage == "compress" else cli.verify_compressed
    def waiting(*args, **kwargs):
        entered.set()
        if not release.wait(10):
            raise RuntimeError("artifact test deadline")
        return function(*args, **kwargs)
    name = "compress_response" if stage == "compress" else "verify_compressed"
    command = cli.command_run_compress if stage == "compress" else cli.command_run_verify
    with patch.object(cli, name, waiting), contextlib.redirect_stdout(io.StringIO()):
        command(argparse.Namespace(run_id=run_id))


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_home = os.environ.get("CCW_HOME")
        os.environ["CCW_HOME"] = self.temp.name
        self.run = create_run(mode="chat-pro", task_kind="review", workspace=self.temp.name,
                              prompt_text="Review repository through readonly MCP", adapter_manifest=ADAPTER)
        self.run_id = self.run["run_id"]
        authorize_run(self.run_id)

    def tearDown(self):
        if self.old_home is None:
            os.environ.pop("CCW_HOME", None)
        else:
            os.environ["CCW_HOME"] = self.old_home
        self.temp.cleanup()

    def prepared(self):
        return preflight_http(self.run_id, CONFIG, client=Client())

    def artifacts(self):
        with contextlib.redirect_stdout(io.StringIO()):
            command_run_compress(argparse.Namespace(run_id=self.run_id))
            command_run_verify(argparse.Namespace(run_id=self.run_id))

    def test_complete_and_public_status_no_private_ids(self):
        self.prepared()
        result = execute_http(self.run_id, CONFIG, client=Client())
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["review_complete"])
        public = json.dumps(result) + json.dumps(load_run(self.run_id)["route_evidence"])
        for secret in ("private-conversation", "private-token", "private-assistant", "private-tool", CONFIG["account_hash"]):
            self.assertNotIn(secret, public)

    def test_public_receipt_real_validator_and_identity_filter(self):
        self.prepared()
        execute_http(self.run_id, CONFIG, client=Client())
        directory = Path(self.temp.name) / "runs" / self.run_id
        self.artifacts()
        receipt = finalize_run(self.run_id)["receipt"]
        self.assertEqual(receipt["adapter"]["kind"], "web-http")
        self.assertTrue(receipt["route_evidence"]["mcp_verified"])
        public = json.dumps(receipt)
        for secret in ("private-conversation", "private-token", "private-assistant", "private-tool", CONFIG["account_hash"]):
            self.assertNotIn(secret, public)

    def test_tampered_prompt_prevents_post(self):
        self.prepared()
        path = Path(self.temp.name) / "runs" / self.run_id / "prompt.md"
        path.write_text("tampered", encoding="utf-8")
        client = Client()
        with self.assertRaises(StateError):
            execute_http(self.run_id, CONFIG, client=client)
        self.assertEqual(client.posts, 0)

    def test_binding_change_and_cross_project_rejected(self):
        self.prepared()
        with self.assertRaises(StateError):
            execute_http(self.run_id, {**CONFIG, "account_hash": "b" * 64}, client=Client())
        with self.assertRaises(ValidationError):
            execute_http(self.run_id, {**CONFIG, "project_id": "other-project"}, client=Client())

    def test_disconnect_recovery_without_second_post(self):
        self.prepared()
        client = Client(disconnect=True)
        self.assertEqual(execute_http(self.run_id, CONFIG, client=client)["status"], "unknown")
        with self.assertRaises(StateError):
            execute_http(self.run_id, CONFIG, client=client)
        self.assertEqual(recover_http(self.run_id, CONFIG, client=client)["status"], "complete")
        self.assertEqual(client.posts, 1)

    def test_locator_persisted_before_stream_process_exit(self):
        self.prepared()
        class StreamingClient(Client):
            def set_locator_callback(self, callback):
                self.callback = callback
            def submit(self, intent):
                self.posts += 1
                self.callback({key: value for key, value in intent.items()
                               if key not in ("text", "model", "project_id", "context")} |
                              {"conversation_id": "private-conversation"})
                raise SystemExit(8)
        client = StreamingClient()
        with self.assertRaises(SystemExit):
            execute_http(self.run_id, CONFIG, client=client)
        directory = Path(self.temp.name) / "runs" / self.run_id
        self.assertEqual(read_json(directory / "private.json")["http_locator"]["conversation_id"],
                         "private-conversation")
        with self.assertRaises(StateError):
            execute_http(self.run_id, CONFIG, client=client)
        recovered = Client()
        self.assertEqual(recover_http(self.run_id, CONFIG, client=recovered)["status"], "complete")
        self.assertEqual(recovered.posts, 0)

    def test_unknown_error_text_is_never_persisted_or_published(self):
        self.prepared()
        class ErrorClient(Client):
            def submit(self, intent):
                return {"state": "unknown", "error_code": "private-token response body"}
        result = execute_http(self.run_id, CONFIG, client=ErrorClient())
        self.assertEqual(result["error_code"], "unclassified_error")
        self.assertNotIn("private-token", json.dumps(load_run(self.run_id)))

    def test_missing_model_and_mcp_proof_blocks_completion(self):
        self.prepared()
        result = execute_http(self.run_id, CONFIG, client=Client(verified=False))
        self.assertFalse(result["review_complete"])
        self.assertEqual(result["status"], "partial")
        with self.assertRaises(StateError):
            capture_raw(self.run_id, "forged", terminal_signal=True)

    def test_multiprocess_single_post(self):
        self.prepared()
        marker = str(Path(self.temp.name) / "posts.txt")
        children = [multiprocessing.Process(target=contender, args=(self.run_id, marker)) for _ in range(2)]
        for child in children:
            child.start()
        for child in children:
            child.join(15)
            self.assertFalse(child.is_alive())
            self.assertEqual(child.exitcode, 0)
        self.assertEqual(Path(marker).read_text().splitlines(), ["post"])

    def test_crash_committing_cannot_post_again(self):
        self.prepared()
        marker = str(Path(self.temp.name) / "posts.txt")
        child = multiprocessing.Process(target=contender, args=(self.run_id, marker, True))
        child.start()
        child.join(15)
        self.assertEqual(child.exitcode, 8)
        self.assertEqual(load_run(self.run_id)["status"], "committing")
        with self.assertRaises(StateError):
            execute_http(self.run_id, CONFIG, client=Client(marker=marker))
        self.assertEqual(Path(marker).read_text().splitlines(), ["post"])
        self.assertEqual(recover_http(self.run_id, CONFIG, client=Client())["status"], "complete")

    def test_generic_authorize_competes_with_executor_process(self):
        self.prepared()
        marker = str(Path(self.temp.name) / "posts.txt")
        entered, release, result = multiprocessing.Event(), multiprocessing.Event(), multiprocessing.Queue()
        executor = multiprocessing.Process(target=waiting_execute, args=(self.run_id, marker, entered, release))
        executor.start()
        self.assertTrue(entered.wait(10))
        authorizer = multiprocessing.Process(target=competing_authorize, args=(self.run_id, result))
        authorizer.start()
        authorizer.join(10)
        self.assertEqual(authorizer.exitcode, 0)
        self.assertEqual(result.get(timeout=2), "rejected")
        release.set()
        executor.join(10)
        self.assertEqual(executor.exitcode, 0)
        self.assertEqual(load_run(self.run_id)["submission"]["count"], 1)
        with self.assertRaises(StateError):
            authorize_run(self.run_id)
        with self.assertRaises(StateError):
            preflight_http(self.run_id, CONFIG, client=Client())
        self.assertEqual(Path(marker).read_text().splitlines(), ["post"])

    def test_durable_intent_with_zero_count_never_resends(self):
        self.prepared()
        path = Path(self.temp.name) / "runs" / self.run_id / "private.json"
        private = read_json(path)
        locator = dict(conversation_id=None, user_message_id="private-user", parent_message_id="private-parent",
                       requested_model=CONFIG["model"], account_hash=CONFIG["account_hash"],
                       expected_connector=CONFIG["expected_connector"], expected_tool=CONFIG["expected_tool"])
        private.update(http_locator=locator, http_intent={**locator, "prompt_sha256": self.run["prompt"]["sha256"]})
        write_json(path, private, private=True)
        client = Client()
        for operation in (execute_http, preflight_http):
            with self.assertRaises(StateError):
                operation(self.run_id, CONFIG, client=client)
        with self.assertRaises(StateError):
            authorize_run(self.run_id)
        self.assertEqual(client.posts, 0)
        self.assertEqual(recover_http(self.run_id, CONFIG, client=client)["status"], "complete")
        self.assertEqual(client.posts, 0)
        self.assertEqual(load_run(self.run_id)["submission"]["count"], 1)

    def test_stale_generic_state_cannot_overwrite_committed_count(self):
        self.prepared()
        stale = load_run(self.run_id)
        execute_http(self.run_id, CONFIG, client=Client())
        with self.assertRaises(StateError):
            save_run(stale)
        current = load_run(self.run_id)
        current["submission"]["count"] = 0
        with self.assertRaises(StateError):
            save_run(current)
        self.assertEqual(load_run(self.run_id)["submission"]["count"], 1)

    def test_regenerated_output_invalidates_accepted_proof(self):
        self.prepared()
        execute_http(self.run_id, CONFIG, client=Client())
        self.artifacts()
        finalize_run(self.run_id)
        directory = Path(self.temp.name) / "runs" / self.run_id
        stale_compressed = read_json(directory / "compressed.json")
        stale_verified = read_json(directory / "verification.json")
        recover_http(self.run_id, CONFIG, client=RegeneratedClient())
        state = load_run(self.run_id)
        self.assertFalse(state["finalized"])
        self.assertEqual(state["compression"]["status"], "pending")
        self.assertEqual(state["verification"]["status"], "pending")
        self.assertFalse((directory / "receipt.public.json").exists())
        with self.assertRaises(StateError):
            finalize_run(self.run_id)
        with self.assertRaises(StateError):
            set_compression(self.run_id, stale_compressed, directory / "compressed.json")
        self.artifacts()
        with self.assertRaises(StateError):
            set_verification(self.run_id, stale_verified, directory / "verification.json")
        self.assertEqual(finalize_run(self.run_id)["receipt"]["acceptance"]["verdict"], "accept")

    def test_compress_and_verify_hold_lock_through_file_write(self):
        self.prepared()
        execute_http(self.run_id, CONFIG, client=Client())
        for stage in ("compress", "verify"):
            entered, release = multiprocessing.Event(), multiprocessing.Event()
            worker = multiprocessing.Process(target=waiting_artifact, args=(self.run_id, stage, entered, release))
            worker.start()
            self.assertTrue(entered.wait(10))
            try:
                with self.assertRaises(StateError):
                    recover_http(self.run_id, CONFIG, client=RegeneratedClient())
            finally:
                release.set()
                worker.join(10)
            self.assertEqual(worker.exitcode, 0)
        self.assertEqual(finalize_run(self.run_id)["receipt"]["acceptance"]["verdict"], "accept")
        recover_http(self.run_id, CONFIG, client=RegeneratedClient())
        with self.assertRaises(StateError):
            finalize_run(self.run_id)

    def test_finalization_detects_actual_artifact_tampering(self):
        self.prepared()
        execute_http(self.run_id, CONFIG, client=Client())
        self.artifacts()
        directory = Path(self.temp.name) / "runs" / self.run_id
        for name in ("response.raw.md", "compressed.json", "verification.json"):
            path = directory / name
            original = path.read_text(encoding="utf-8")
            path.write_text(original + " ", encoding="utf-8")
            with self.assertRaises(StateError):
                finalize_run(self.run_id)
            path.write_text(original, encoding="utf-8")

    def test_terminal_identity_change_invalidates_same_text(self):
        self.prepared()
        execute_http(self.run_id, CONFIG, client=Client())
        self.artifacts()
        finalize_run(self.run_id)
        class NewTerminal(Client):
            def recover(self, locator):
                value = super().recover(locator)
                value["terminal_evidence"]["message_id"] = "different-terminal-id"
                return value
        recover_http(self.run_id, CONFIG, client=NewTerminal())
        self.assertFalse(load_run(self.run_id)["finalized"])
        with self.assertRaises(StateError):
            finalize_run(self.run_id)

    def test_evidence_downgrade_invalidates_same_text_and_terminal(self):
        self.prepared()
        directory = Path(self.temp.name) / "runs" / self.run_id
        for missing in ("model", "mcp", "terminal", "identity"):
            with self.subTest(missing=missing):
                if load_run(self.run_id)["submission"]["count"] == 0:
                    execute_http(self.run_id, CONFIG, client=Client())
                else:
                    recover_http(self.run_id, CONFIG, client=Client())
                self.artifacts()
                finalize_run(self.run_id)
                class DowngradedClient(Client):
                    def recover(self, locator):
                        result = super().recover(locator)
                        if missing == "model":
                            result["route_evidence"] = {}
                        elif missing == "mcp":
                            result["tool_evidence"] = []
                        elif missing == "terminal":
                            result["terminal_evidence"]["end_turn"] = False
                        else:
                            result["identity_verified"] = False
                        return result
                recover_http(self.run_id, CONFIG, client=DowngradedClient())
                state = load_run(self.run_id)
                self.assertFalse(state["finalized"])
                self.assertEqual(state["acceptance"]["verdict"], "hold")
                self.assertEqual(state["compression"]["status"], "pending")
                self.assertEqual(state["verification"]["status"], "pending")
                self.assertFalse(state["outcome"]["final_output_captured"])
                self.assertFalse((directory / "receipt.public.json").exists())
                self.assertFalse((directory / "receipt.private.json").exists())
                with self.assertRaises(StateError):
                    finalize_run(self.run_id)

    def test_probe_only_returns_sanitized_model_slugs(self):
        from ccw.http_runtime import probe_http
        client = Client()
        client.probe = lambda: {"state": "ready", "models": ["real-model", None, 4, "secret\nbody", "a" * 101]}
        with patch("ccw.http_runtime._client", return_value=client):
            self.assertEqual(probe_http(CONFIG)["models"], ["real-model"])


if __name__ == "__main__":
    unittest.main()
