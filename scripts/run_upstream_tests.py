from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "vendor" / "codex-chatgpt-web-orchestrator"
TESTS = UPSTREAM / "tests"
SCRIPTS = UPSTREAM / "scripts"

sys.path.insert(0, str(SCRIPTS))


def flatten(suite: unittest.TestSuite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def main() -> int:
    discovered = unittest.defaultTestLoader.discover(str(TESTS))
    tests = list(flatten(discovered))
    skipped: list[str] = []
    if os.name == "nt":
        remaining = []
        for test in tests:
            if test.id().endswith("test_dry_demo_is_executable_and_truthfully_labeled"):
                skipped.append(test.id())
            else:
                remaining.append(test)
        tests = remaining
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(tests))
    for test_id in skipped:
        print(f"SKIP (Windows has no upstream bash demo runtime): {test_id}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
