import tempfile
import unittest
from pathlib import Path

from ccw.verifier import verify_compressed


class VerifierTests(unittest.TestCase):
    def test_review_file_and_line_are_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sample.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
            good = {
                "mode": "chat-pro",
                "findings": [{"file": "sample.py", "line": 2}],
            }
            result = verify_compressed(good, workspace=root)
            self.assertTrue(result["passed"])
            bad = {
                "mode": "chat-pro",
                "findings": [{"file": "sample.py", "line": 99}],
            }
            result = verify_compressed(bad, workspace=root)
            self.assertFalse(result["passed"])

    def test_work_is_rejected_by_verifier(self):
        result = verify_compressed({"mode": "work", "findings": []}, workspace=".")
        self.assertFalse(result["passed"])
        self.assertIn("work-mode-forbidden", result["failures"])


if __name__ == "__main__":
    unittest.main()
