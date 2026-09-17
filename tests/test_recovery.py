import os
import tempfile
import unittest
from pathlib import Path

from ccw.state import create_run, record_recovery


ADAPTER = {
    "identity": "native-codex-browser",
    "family": "native-control-style",
    "kind": "browser-thread-bridge",
    "capabilities": ["send", "observe", "capture", "stable_identity", "chat_pro", "deep_research"],
}


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_home = os.environ.get("CCW_HOME")
        os.environ["CCW_HOME"] = str(Path(self.tmp.name) / "ccw-home")
        self.workspace = Path(self.tmp.name) / "repo"
        self.workspace.mkdir()

    def tearDown(self):
        if self.old_home is None:
            os.environ.pop("CCW_HOME", None)
        else:
            os.environ["CCW_HOME"] = self.old_home
        self.tmp.cleanup()

    def test_generation_reconnects_to_same_run(self):
        state = create_run(
            mode="chat-pro",
            task_kind="review",
            workspace=self.workspace,
            prompt_text="Review",
            adapter_manifest=ADAPTER,
        )
        result = record_recovery(
            state["run_id"],
            {
                "identity_reopenable": True,
                "original_turn_present": True,
                "generation_active": True,
                "final_output_accessible": False,
                "partial_output_accessible": False,
                "saved_capture_available": False,
            },
        )
        self.assertEqual("wait_same_run", result["last_recovery"]["action"])
        self.assertFalse(result["last_recovery"]["resubmit"])

    def test_lost_identity_marks_unknown(self):
        state = create_run(
            mode="deep-research",
            task_kind="source-research",
            workspace=self.workspace,
            prompt_text="Research",
            adapter_manifest=ADAPTER,
        )
        result = record_recovery(
            state["run_id"],
            {
                "identity_reopenable": False,
                "original_turn_present": None,
                "generation_active": None,
                "final_output_accessible": False,
                "partial_output_accessible": False,
                "saved_capture_available": False,
            },
        )
        self.assertEqual("mark_unknown_no_resend", result["last_recovery"]["action"])
        self.assertEqual("unknown", result["status"])


if __name__ == "__main__":
    unittest.main()
