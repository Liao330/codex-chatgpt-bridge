import os
import tempfile
import unittest
from pathlib import Path

from ccw.cycle import record_execution, sanitize_output, set_protocol_state
from ccw.state import create_run, load_run


ADAPTER = {
    "identity": "native-codex-browser",
    "family": "native-control-style",
    "kind": "browser-thread-bridge",
    "capabilities": ["send", "observe", "capture", "stable_identity", "chat_pro", "deep_research"],
}


class CycleTests(unittest.TestCase):
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

    def test_protocol_and_execution_records(self):
        state = create_run(mode="chat-pro", task_kind="review", workspace=self.workspace, prompt_text="review", adapter_manifest=ADAPTER)
        run_id = state["run_id"]
        set_protocol_state(run_id, state_name="INIT", iteration=0, task_id="c2c_test")
        set_protocol_state(run_id, state_name="PLAN", iteration=1)
        set_protocol_state(run_id, state_name="EXECUTING", iteration=1)
        output = Path(self.tmp.name) / "test.log"
        output.write_text("token=abcdefghijk1234\n", encoding="utf-8")
        record = record_execution(run_id, iteration=1, changed_files=["sample.py"], tests="1 passed", exit_status="ok", command="python -m unittest", output_file=str(output))
        self.assertEqual("EXECUTED", load_run(run_id)["protocol"]["state"])
        self.assertEqual("1 passed", record["tests"])
        sanitized = (Path(os.environ["CCW_HOME"]) / "runs" / run_id / "executions" / "iteration-1.log").read_text(encoding="utf-8")
        self.assertNotIn("abcdefghijk1234", sanitized)
        self.assertIn("[REDACTED]", sanitized)

    def test_secret_sanitizer(self):
        clean, warnings = sanitize_output("Authorization: Bearer abcdefghijklmnopqrstuvwxyz\n")
        self.assertIn("[REDACTED]", clean)
        self.assertIn("secret-redacted", warnings)


if __name__ == "__main__":
    unittest.main()
