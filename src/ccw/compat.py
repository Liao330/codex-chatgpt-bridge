from __future__ import annotations

from pathlib import Path
import sys
from types import ModuleType


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_ROOT = PLUGIN_ROOT / "vendor" / "codex-chatgpt-web-orchestrator"
UPSTREAM_SCRIPTS = UPSTREAM_ROOT / "scripts"
UPSTREAM_SCHEMAS = UPSTREAM_ROOT / "schemas"

if str(UPSTREAM_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(UPSTREAM_SCRIPTS))


def upstream_policy() -> ModuleType:
    import orchestrator_policy  # type: ignore

    return orchestrator_policy


def upstream_receipt() -> ModuleType:
    import delegation_receipt  # type: ignore

    return delegation_receipt
