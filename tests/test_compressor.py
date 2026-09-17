import json
import tempfile
import unittest
from pathlib import Path

from ccw.compressor import compress_response, validate_compressed


class CompressorTests(unittest.TestCase):
    def test_json_review_is_preserved(self):
        payload = {
            "verdict": "request_changes",
            "summary": ["operator bug"],
            "findings": [
                {
                    "severity": "high",
                    "file": "sample.py",
                    "line": 2,
                    "claim": "subtracts instead of adds",
                    "evidence": "return a-b",
                    "recommendation": "return a+b",
                }
            ],
            "tests": ["assert add(1, 2) == 3"],
            "uncertainties": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.md"
            raw.write_text(json.dumps(payload), encoding="utf-8")
            result = compress_response(raw.read_text(encoding="utf-8"), mode="chat-pro", raw_path=raw)
        self.assertEqual("json", result["parse_mode"])
        self.assertEqual("sample.py", result["findings"][0]["file"])
        self.assertEqual([], validate_compressed(result))

    def test_heuristic_deep_research_keeps_citations(self):
        raw = "Summary: thing works\n- https://example.com/a\nUncertainty: may change\n"
        result = compress_response(raw, mode="deep-research")
        self.assertEqual("heuristic", result["parse_mode"])
        self.assertIn("https://example.com/a", result["citations"])


if __name__ == "__main__":
    unittest.main()
