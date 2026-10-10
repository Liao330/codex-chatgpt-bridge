import multiprocessing
import os
import tempfile
import unittest
from pathlib import Path

from ccw.cycle import set_protocol_state
from ccw.errors import StateError
from ccw.http_runtime import process_lock
from ccw.state import create_run, load_run


def competing_cycle(run_id, result):
    try:
        set_protocol_state(run_id, state_name="INIT", iteration=0)
        result.put("written")
    except StateError:
        result.put("locked")


class HttpCycleLockTests(unittest.TestCase):
    def test_generic_cycle_mutation_uses_http_run_lock(self):
        previous = os.environ.get("CCW_HOME")
        with tempfile.TemporaryDirectory() as directory:
            os.environ["CCW_HOME"] = directory
            try:
                adapter = {"identity": "http-test", "family": "native-control-style",
                    "kind": "web-http", "capabilities": ["send", "observe", "capture", "stable_identity", "chat_pro"]}
                state = create_run(mode="chat-pro", task_kind="review", workspace=Path(directory),
                    prompt_text="Read-only test question", adapter_manifest=adapter)
                context = multiprocessing.get_context("spawn")
                result = context.Queue()
                with process_lock("run:" + state["run_id"]):
                    child = context.Process(target=competing_cycle, args=(state["run_id"], result))
                    child.start()
                    child.join(10)
                    self.assertFalse(child.is_alive())
                    self.assertEqual(child.exitcode, 0)
                    self.assertEqual(result.get(timeout=2), "locked")
                self.assertIsNone(load_run(state["run_id"])["protocol"]["state"])
                set_protocol_state(state["run_id"], state_name="INIT", iteration=0)
                self.assertEqual(load_run(state["run_id"])["protocol"]["state"], "INIT")
            finally:
                if previous is None:
                    os.environ.pop("CCW_HOME", None)
                else:
                    os.environ["CCW_HOME"] = previous
