from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import re

from .errors import StateError, ValidationError
from .fingerprint import sha256_text
from .state import load_run, save_run
from .storage import append_event, atomic_write_text, ensure_run_dir, utc_now, write_json


PROTOCOL_STATES = (
    "INIT",
    "PLAN",
    "EXECUTING",
    "EXECUTED",
    "REVIEW",
    "DONE",
    "BLOCKED",
    "ERROR",
    "HANDOFF",
)
ALLOWED_TRANSITIONS = {
    None: {"INIT"},
    "INIT": {"PLAN", "BLOCKED", "ERROR"},
    "PLAN": {"EXECUTING", "PLAN", "BLOCKED", "ERROR"},
    "EXECUTING": {"EXECUTED", "BLOCKED", "ERROR"},
    "EXECUTED": {"REVIEW", "PLAN", "DONE", "BLOCKED", "ERROR"},
    "REVIEW": {"PLAN", "DONE", "BLOCKED", "ERROR"},
    "HANDOFF": {"PLAN", "EXECUTING", "REVIEW", "BLOCKED", "ERROR"},
    "DONE": set(),
    "BLOCKED": set(),
    "ERROR": {"PLAN", "BLOCKED"},
}
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL)
SECRET_RES = (
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]{12,}=*"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"(?i)((?:api[_-]?key|access[_-]?token|refresh[_-]?token|token|password)\s*[:=]\s*)[^\s]{8,}"),
)
HOME_RE = re.compile(r"(?i)(?:[A-Z]:\\Users\\[^\\\s]+|/(?:Users|home)/[^/\s]+)")
MAX_OUTPUT_BYTES = 256 * 1024


def _protocol(state: dict[str, Any]) -> dict[str, Any]:
    return state.setdefault("protocol", {"state": None, "iteration": 0, "task_id": None, "checkpoint": None, "updated_at": None})


def set_protocol_state(
    run_id: str,
    *,
    state_name: str,
    iteration: int,
    task_id: str | None = None,
    checkpoint: str | None = None,
) -> dict[str, Any]:
    state_name = state_name.upper()
    if state_name not in PROTOCOL_STATES:
        raise ValidationError(f"unsupported protocol state: {state_name}")
    if iteration < 0:
        raise ValidationError("iteration must be non-negative")
    state = load_run(run_id)
    protocol = _protocol(state)
    previous = protocol.get("state")
    if state_name not in ALLOWED_TRANSITIONS.get(previous, set()):
        raise StateError(f"invalid protocol transition: {previous or 'NONE'} -> {state_name}")
    protocol.update(
        {
            "state": state_name,
            "iteration": iteration,
            "task_id": task_id or protocol.get("task_id"),
            "checkpoint": checkpoint,
            "updated_at": utc_now(),
        }
    )
    append_event(run_id, {"kind": "protocol", "state": state_name, "iteration": iteration})
    save_run(state)
    return protocol


def sanitize_output(text: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    clean = PRIVATE_KEY_RE.sub("[REDACTED PRIVATE KEY BLOCK]", text)
    if clean != text:
        warnings.append("private-key-block-redacted")
    for pattern in SECRET_RES:
        clean, count = pattern.subn(lambda m: (m.group(1) if m.lastindex else "") + "[REDACTED]", clean)
        if count:
            warnings.append("secret-redacted")
    clean, count = HOME_RE.subn("<HOME>", clean)
    if count:
        warnings.append("home-path-redacted")
    raw = clean.encode("utf-8")
    if len(raw) > MAX_OUTPUT_BYTES:
        clean = raw[:MAX_OUTPUT_BYTES].decode("utf-8", errors="ignore") + "\n[TRUNCATED]\n"
        warnings.append("output-truncated")
    return clean, sorted(set(warnings))


def _safe_relative_files(files: list[str]) -> list[str]:
    safe: list[str] = []
    for raw in files:
        path = Path(raw)
        if path.is_absolute() or ".." in path.parts:
            raise ValidationError(f"changed file must stay workspace-relative: {raw}")
        safe.append(path.as_posix())
    return safe


def record_execution(
    run_id: str,
    *,
    iteration: int,
    changed_files: list[str],
    tests: str,
    exit_status: str,
    command: str | None = None,
    output_file: str | None = None,
) -> dict[str, Any]:
    state = load_run(run_id)
    changed_files = _safe_relative_files(changed_files)
    command = sanitize_output(command)[0] if command else None
    directory = ensure_run_dir(run_id) / "executions"
    directory.mkdir(parents=True, exist_ok=True)
    output_path: Path | None = None
    output_sha256: str | None = None
    output_warnings: list[str] = []
    if output_file:
        raw = Path(output_file).read_text(encoding="utf-8", errors="replace")
        clean, output_warnings = sanitize_output(raw)
        output_path = directory / f"iteration-{iteration}.log"
        atomic_write_text(output_path, clean, private=True)
        output_sha256 = hashlib.sha256(output_path.read_bytes()).hexdigest()
    record = {
        "schema_version": "1.0.0",
        "iteration": iteration,
        "changed_files": changed_files,
        "tests": tests,
        "exit_status": exit_status,
        "command": command,
        "output_path": output_path.name if output_path else None,
        "output_sha256": output_sha256,
        "output_warnings": output_warnings,
    }
    write_json(directory / f"iteration-{iteration}.json", record)
    state.setdefault("executions", []).append(record)
    protocol = _protocol(state)
    protocol["iteration"] = iteration
    if protocol.get("state") == "EXECUTING":
        protocol["state"] = "EXECUTED"
        protocol["updated_at"] = utc_now()
        append_event(run_id, {"kind": "protocol", "state": "EXECUTED", "iteration": iteration})
    save_run(state)
    return record


def record_handoff(run_id: str, brief: str) -> dict[str, Any]:
    brief, _ = sanitize_output(brief.strip())
    if not brief:
        raise ValidationError("handoff brief must not be empty")
    if len(brief.encode("utf-8")) > 1024:
        raise ValidationError("handoff brief must be under 1 KB and must not contain logs or file bodies")
    directory = ensure_run_dir(run_id)
    path = directory / "handoff.md"
    atomic_write_text(path, brief + "\n", private=True)
    state = load_run(run_id)
    state["handoff"] = {"path": path.name, "sha256": sha256_text(brief), "updated_at": utc_now()}
    _protocol(state)["state"] = "HANDOFF"
    append_event(run_id, {"kind": "protocol", "state": "HANDOFF"})
    save_run(state)
    return state["handoff"]


