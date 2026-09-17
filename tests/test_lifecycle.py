import os
import tempfile
import unittest
from pathlib import Path

from ccw.compressor import compress_response
from ccw.errors import StateError
from ccw.state import (
    authorize_run,
    begin_submit,
    capture_raw,
    confirm_submit,
    create_run,
    finalize_run,
    load_run,
    record_preflight,
    set_compression,
    set_verification,
)
from ccw.storage import run_dir, write_json
from ccw.verifier import verify_compressed


ADAPTER = {
    "identity": "native-codex-browser",
    "family": "native-control-style",
    "kind": "browser-thread-bridge",
    "capabilities": ["send", "observe", "capture", "stable_identity", "chat_pro", "deep_research"],
}


PREFLIGHT = {
    "bridge_connected": True,
    "tab_bound": True,
    "identity_stable": True,
    "identity_reopenable": True,
    "expected_surface": "chat",
    "observed_surface": "chat",
    "observed_mode": "chat-pro",
    "model_label": "Pro",
    "mode_verified": True,
    "model_verified": True,
    "composer_interactive": True,
    "stable_read_count": 2,
    "prompt_filled": False,
    "submission_count": 0,
}


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_home = os.environ.get("CCW_HOME")
        os.environ["CCW_HOME"] = str(Path(self.tmp.name) / "ccw-home")
        self.workspace = Path(self.tmp.name) / "repo"
        self.workspace.mkdir()
        (self.workspace / "sample.py").write_text("a = 1\nb = 2\n", encoding="utf-8")

    def tearDown(self):
        if self.old_home is None:
            os.environ.pop("CCW_HOME", None)
        else:
            os.environ["CCW_HOME"] = self.old_home
        self.tmp.cleanup()

    def test_complete_review_lifecycle(self):
        state = create_run(
            mode="chat-pro",
            task_kind="review",
            workspace=self.workspace,
            prompt_text="Review sample.py",
            adapter_manifest=ADAPTER,
        )
        run_id = state["run_id"]
        authorize_run(run_id)
        record_preflight(run_id, PREFLIGHT)
        begin_submit(run_id)
        confirm_submit(run_id, acknowledged=True, conversation_identity="conversation-test")
        raw = '{"verdict":"request_changes","summary":["line bug"],"findings":[{"severity":"high","file":"sample.py","line":2,"claim":"bad","evidence":"b = 2","recommendation":"fix it"}],"tests":[],"uncertainties":[]}'
        capture_raw(run_id, raw, terminal_signal=True)
        compressed = compress_response(raw, mode="chat-pro", raw_path=run_dir(run_id) / "response.raw.md")
        compressed_path = run_dir(run_id) / "compressed.json"
        write_json(compressed_path, compressed)
        set_compression(run_id, compressed, compressed_path)
        verification = verify_compressed(
            compressed,
            workspace=self.workspace,
            raw_sha256=load_run(run_id)["outcome"]["raw_sha256"],
        )
        verification_path = run_dir(run_id) / "verification.json"
        write_json(verification_path, verification)
        set_verification(run_id, verification, verification_path)
        result = finalize_run(run_id)
        self.assertEqual("complete", result["state"]["status"])
        self.assertEqual(1, result["state"]["submission"]["count"])
        self.assertEqual("accept", result["receipt"]["acceptance"]["verdict"])

    def test_deep_research_lifecycle_preserves_citations(self):
        state = create_run(
            mode="deep-research",
            task_kind="source-research",
            workspace=self.workspace,
            prompt_text="Research a public standard",
            adapter_manifest=ADAPTER,
        )
        run_id = state["run_id"]
        authorize_run(run_id)
        observation = dict(PREFLIGHT)
        observation.update(
            {
                "observed_mode": "deep-research",
                "model_label": "Deep Research",
            }
        )
        record_preflight(run_id, observation)
        begin_submit(run_id)
        confirm_submit(run_id, acknowledged=True, conversation_identity="conversation-deep")
        raw = '{"summary":["result"],"key_points":["point"],"citations":["https://example.com/source"],"uncertainties":["needs source check"]}'
        capture_raw(run_id, raw, terminal_signal=True)
        compressed = compress_response(raw, mode="deep-research", raw_path=run_dir(run_id) / "response.raw.md")
        compressed_path = run_dir(run_id) / "compressed.json"
        write_json(compressed_path, compressed)
        set_compression(run_id, compressed, compressed_path)
        verification = verify_compressed(
            compressed,
            workspace=self.workspace,
            raw_sha256=load_run(run_id)["outcome"]["raw_sha256"],
        )
        verification_path = run_dir(run_id) / "verification.json"
        write_json(verification_path, verification)
        set_verification(run_id, verification, verification_path)
        result = finalize_run(run_id)
        self.assertEqual("deep-research", result["receipt"]["route_evidence"]["mode"])
        self.assertEqual(["https://example.com/source"], result["receipt"]["outcome"]["citations"])

    def test_duplicate_submission_is_blocked(self):
        state = create_run(
            mode="chat-pro",
            task_kind="review",
            workspace=self.workspace,
            prompt_text="Review sample.py",
            adapter_manifest=ADAPTER,
        )
        run_id = state["run_id"]
        authorize_run(run_id)
        record_preflight(run_id, PREFLIGHT)
        begin_submit(run_id)
        confirm_submit(run_id, acknowledged=True)
        with self.assertRaises(StateError):
            begin_submit(run_id)


if __name__ == "__main__":
    unittest.main()
