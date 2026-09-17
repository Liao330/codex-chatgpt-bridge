import unittest

from ccw.errors import ValidationError, WorkForbiddenError
from ccw.policy import choose_route, detect_presence, normalize_mode, required_capabilities, validate_adapter_manifest


class PolicyTests(unittest.TestCase):
    def test_work_is_forbidden(self):
        with self.assertRaises(WorkForbiddenError):
            normalize_mode("work")
        with self.assertRaises(WorkForbiddenError):
            choose_route(task_kind="artifact")
        with self.assertRaises(WorkForbiddenError):
            choose_route(task_kind="browser-action")
        with self.assertRaises(WorkForbiddenError):
            choose_route(task_kind="multi-step")
        with self.assertRaises(WorkForbiddenError):
            choose_route(task_kind="artifact", requested_mode="chat-pro")

    def test_routes(self):
        self.assertEqual("chat-pro", choose_route(task_kind="critique"))
        self.assertEqual("chat-pro", choose_route(task_kind="architecture-review"))
        self.assertEqual("deep-research", choose_route(task_kind="source-research"))
        self.assertEqual("deep-research", choose_route(task_kind="research-report"))

    def test_unknown_task_fails(self):
        with self.assertRaises(ValidationError):
            choose_route(task_kind="unknown")

    def test_read_only_presence_detection(self):
        present = detect_presence(
            {
                "exposed_tools": ["browser_get_state", "read_thread", "send_message_to_thread"],
                "exposed_skills": [],
                "executables": [],
            }
        )
        self.assertIn("native", present)

    def test_adapter_capabilities(self):
        manifest = {
            "family": "native-control-style",
            "kind": "browser-thread-bridge",
            "capabilities": [
                "send",
                "observe",
                "capture",
                "stable_identity",
                "chat_pro",
                "deep_research",
            ],
        }
        self.assertEqual([], validate_adapter_manifest(manifest, mode="chat-pro"))
        self.assertEqual([], validate_adapter_manifest(manifest, mode="deep-research"))
        self.assertIn("chat_pro", required_capabilities("chat-pro"))
        self.assertIn("deep_research", required_capabilities("deep-research"))

    def test_adapter_work_capability_is_rejected(self):
        manifest = {
            "family": "native-control-style",
            "kind": "browser-thread-bridge",
            "capabilities": ["send", "observe", "capture", "stable_identity", "chat_pro", "work"],
        }
        self.assertIn("work-capability-forbidden", validate_adapter_manifest(manifest, mode="chat-pro"))


if __name__ == "__main__":
    unittest.main()
