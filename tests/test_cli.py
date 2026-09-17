import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_route_plan_rejects_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            capabilities = Path(tmp) / "caps.json"
            capabilities.write_text(
                json.dumps({"backends": {"native": ["send", "observe", "capture", "stable_identity", "chat_pro"]}}),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ccw",
                    "route",
                    "plan",
                    "--task-kind",
                    "artifact",
                    "--capabilities",
                    str(capabilities),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(3, result.returncode)
            self.assertIn("Work", result.stderr)


if __name__ == "__main__":
    unittest.main()
