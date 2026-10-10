import unittest

from ccw.errors import ValidationError, WorkForbiddenError
from ccw.policy import choose_route, default_adapter_manifest, detect_presence, normalize_mode, required_capabilities, validate_adapter_manifest


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

    def test_default_adapter_is_http(self):
        manifest = default_adapter_manifest(mode="chat-pro")
        self.assertEqual("web-http", manifest["kind"])
        self.assertIn("chat_pro", manifest["capabilities"])

    def test_deep_research_requires_explicit_adapter(self):
        with self.assertRaises(ValidationError):
            default_adapter_manifest(mode="deep-research")

    def test_backend_selection_does_not_implicitly_choose_native(self):
        from ccw.policy import select_adapter

        capabilities = {
            "web-http": ["send", "observe", "capture", "stable_identity", "chat_pro"],
            "native": ["send", "observe", "capture", "stable_identity", "chat_pro"],
        }
        self.assertEqual("web-http", select_adapter(mode="chat-pro", available=capabilities))
        self.assertEqual("native", select_adapter(mode="chat-pro", available=capabilities, requested_backend="native"))


if __name__ == "__main__":
    unittest.main()
