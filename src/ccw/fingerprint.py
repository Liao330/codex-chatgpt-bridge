from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def prompt_fingerprint(prompt: str) -> str:
    normalized = "\n".join(line.rstrip() for line in prompt.strip().splitlines())
    return sha256_text(normalized)


def scope_fingerprint(workspace: str | Path, allowed_paths: list[str] | None = None) -> str:
    scope = {
        "workspace": str(Path(workspace).resolve()),
        "allowed_paths": sorted(allowed_paths or ["."]),
    }
    return canonical_sha256(scope)
