#!/usr/bin/env python3
"""Pure, dependency-free policy helpers for ChatGPT web orchestration.

The helpers do not open a browser, inspect an account, or send anything. They
turn already-observed, non-sensitive capability and run state into auditable
routing, degradation, submission, completion, and recovery decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import hashlib
import re
from typing import Iterable, Mapping


class Mode(str, Enum):
    CHAT_PRO = "chat-pro"
    DEEP_RESEARCH = "deep-research"
    WORK = "work"


class Completion(str, Enum):
    GENERATING = "generating"
    COMPLETE = "complete"
    PARTIAL = "partial"
    INCOMPLETE = "incomplete"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


BACKEND_ORDER = (
    "native",
    "codex-chatgpt-control",
    "oracle",
    "agentify-desktop",
    "manual",
)

BASE_CAPABILITIES = frozenset({"send", "observe", "capture", "stable_identity"})
MODE_CAPABILITY = {
    Mode.CHAT_PRO: "chat_pro",
    Mode.DEEP_RESEARCH: "deep_research",
    Mode.WORK: "work",
}


@dataclass(frozen=True)
class RouteRequest:
    task_kind: str
    requested_mode: Mode | None = None
    referenced_conversation: bool = False


@dataclass(frozen=True)
class RunObservation:
    active_generation: bool | None
    terminal_signal: bool
    final_output_accessible: bool
    partial_output_accessible: bool = False
    artifact_expected: bool = False
    artifact_accessible: bool = False
    blocker: str | None = None


@dataclass(frozen=True)
class PreflightObservation:
    """Read-only evidence gathered immediately before prompt fill or Send."""

    bridge_connected: bool
    tab_bound: bool
    identity_stable: bool
    identity_reopenable: bool
    expected_surface: str
    observed_surface: str | None
    mode_verified: bool
    model_verified: bool
    composer_interactive: bool
    stable_read_count: int
    prompt_filled: bool = False
    submission_count: int = 0


@dataclass(frozen=True)
class Finding:
    path: str
    kind: str
    line: int


def conversation_action(*, referenced_conversation: bool, continuity_required: bool) -> str:
    """Reuse a known conversation when continuity is requested; otherwise isolate."""
    if referenced_conversation or continuity_required:
        return "reuse"
    return "new"


def prompt_fingerprint(prompt: str) -> str:
    """Create a content-safe idempotency key without storing prompt text."""
    normalized = "\n".join(line.rstrip() for line in prompt.strip().splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def idempotency_decision(
    *,
    submission_state: str,
    proposed_prompt: str,
    recorded_fingerprint: str | None,
    original_turn_present: bool | None = None,
) -> str:
    """Block duplicate content and defer uncertain commits to inspection."""
    proposed = prompt_fingerprint(proposed_prompt)
    if recorded_fingerprint == proposed:
        return "do_not_send_duplicate"
    return submission_decision(submission_state, original_turn_present)


def route_evidence_issues(
    *,
    expected_mode: Mode,
    expected_model: str | None,
    observed_mode: str | None,
    observed_model: str | None,
    mode_verified: bool,
    model_verified: bool,
) -> list[str]:
    """Return missing or conflicting model/mode evidence."""
    issues: list[str] = []
    if not mode_verified or observed_mode != expected_mode.value:
        issues.append("mode-not-verified")
    if expected_model is not None:
        if not model_verified or observed_model != expected_model:
            issues.append("model-not-verified")
    return issues


def preflight_decision(observation: PreflightObservation) -> str:
    """Fail closed when labels survive but the bound ChatGPT surface does not.

    A visible model label is only one signal. Prompt fill and Send require two
    consecutive read-only observations of the same bound, interactive surface.
    """
    if observation.submission_count != 0:
        return "use_existing_run_recovery_no_send"
    if not observation.bridge_connected:
        if observation.identity_reopenable:
            return "reattach_same_identity_no_send"
        return "reacquire_bridge_no_send"
    if not observation.tab_bound or not observation.identity_stable:
        if observation.identity_reopenable:
            return "reopen_same_identity_no_send"
        return "acquire_visible_tab_no_send"
    route_stable = (
        observation.observed_surface == observation.expected_surface
        and observation.mode_verified
        and observation.model_verified
    )
    if (
        not route_stable
        or not observation.composer_interactive
        or observation.stable_read_count < 2
    ):
        if observation.prompt_filled:
            return "hold_draft_surface_unstable_no_send"
        return "stabilize_surface_no_send"
    if observation.prompt_filled:
        return "ready_to_submit_once"
    return "ready_to_fill_prompt"


def detect_backend_presence(
    *,
    exposed_tools: Iterable[str] = (),
    exposed_skills: Iterable[str] = (),
    executables: Iterable[str] = (),
) -> frozenset[str]:
    """Classify a caller-supplied, read-only inventory without probing anything.

    Presence is not capability. Callers must still observe and declare the
    mode-specific capabilities before passing a manifest to ``select_backend``.
    """
    tools = {item.lower() for item in exposed_tools}
    skills = {item.lower() for item in exposed_skills}
    commands = {Path(item).name.lower() for item in executables}
    present = {"manual"}
    browser_present = any("browser" in item for item in tools)
    thread_read = any("read_thread" in item for item in tools)
    thread_send = any("send_message_to_thread" in item for item in tools)
    if browser_present and thread_read and thread_send:
        present.add("native")
    if any("codex-chatgpt-control" in item for item in skills | tools):
        present.add("codex-chatgpt-control")
    if "oracle" in commands or "oracle-mcp" in commands or any(
        item == "oracle" for item in skills
    ):
        present.add("oracle")
    if any("agentify" in item for item in skills | tools | commands):
        present.add("agentify-desktop")
    return frozenset(present)


def choose_mode(request: RouteRequest) -> Mode:
    """Route by intent while preserving an explicit mode exactly."""
    if request.requested_mode is not None:
        return request.requested_mode
    routes = {
        "consultation": Mode.CHAT_PRO,
        "critique": Mode.CHAT_PRO,
        "synthesis": Mode.CHAT_PRO,
        "source-research": Mode.DEEP_RESEARCH,
        "research-report": Mode.DEEP_RESEARCH,
        "artifact": Mode.WORK,
        "browser-action": Mode.WORK,
        "multi-step": Mode.WORK,
    }
    try:
        return routes[request.task_kind]
    except KeyError as exc:
        raise ValueError(f"unsupported task kind: {request.task_kind}") from exc


def required_capabilities(mode: Mode) -> frozenset[str]:
    return BASE_CAPABILITIES | {MODE_CAPABILITY[mode]}


def select_backend(
    mode: Mode,
    available: Mapping[str, Iterable[str]],
    *,
    requested_backend: str | None = None,
) -> str | None:
    """Pick a backend from declared capabilities; never probe or install one."""
    required = required_capabilities(mode)
    candidates = (requested_backend,) if requested_backend else BACKEND_ORDER
    for backend in candidates:
        if backend is None:
            continue
        capabilities = frozenset(available.get(backend, ()))
        if required <= capabilities:
            return backend
    return None


def submission_decision(
    submission_state: str, original_turn_present: bool | None = None
) -> str:
    """Return the only safe next action under single-submit semantics."""
    if submission_state == "not-sent":
        return "send_once_after_confirmation"
    if submission_state in {"committing", "committed"}:
        return "do_not_send"
    if submission_state == "unknown":
        if original_turn_present is True:
            return "do_not_send"
        if original_turn_present is False:
            return "propose_new_send_after_confirmation"
        return "reconnect_and_inspect"
    raise ValueError(f"unsupported submission state: {submission_state}")


def classify_completion(observation: RunObservation) -> Completion:
    """Require terminal state and accessible final output before completion."""
    if observation.blocker:
        return Completion.BLOCKED
    if observation.active_generation is True:
        return Completion.GENERATING
    artifact_ok = not observation.artifact_expected or observation.artifact_accessible
    if (
        observation.active_generation is False
        and observation.terminal_signal
        and observation.final_output_accessible
        and artifact_ok
    ):
        return Completion.COMPLETE
    if observation.partial_output_accessible:
        return Completion.PARTIAL
    if observation.terminal_signal and (
        not observation.final_output_accessible or not artifact_ok
    ):
        return Completion.INCOMPLETE
    return Completion.UNKNOWN


def recovery_decision(
    *,
    identity_reopenable: bool,
    original_turn_present: bool | None = None,
    generation_active: bool | None = None,
    final_output_accessible: bool = False,
    partial_output_accessible: bool = False,
    saved_capture_available: bool = False,
) -> str:
    """Choose a reconnect-first action without silently duplicating a run."""
    if identity_reopenable:
        if original_turn_present is None:
            return "inspect_original_turn"
        if original_turn_present is False:
            return "propose_new_send_after_confirmation"
        if generation_active is True:
            return "wait_same_run"
        if final_output_accessible:
            return "capture_same_run"
        if partial_output_accessible:
            return "mark_partial_no_resend"
        return "mark_incomplete_no_resend"
    if saved_capture_available:
        return "recover_saved_capture"
    return "mark_unknown_no_resend"


SENSITIVE_PATTERNS = {
    "personal-absolute-path": re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/"),
    "home-relative-path": re.compile(r"(?<![A-Za-z0-9])~" + r"/"),
    "uuid-or-conversation-id": re.compile(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
        r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
    ),
    "chatgpt-conversation-url": re.compile(r"https://chatgpt\.com/(?:c|g)/[A-Za-z0-9_-]+"),
    "email-address": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "openai-style-key": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    "bearer-token": re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{12,}=*"),
    "assigned-secret": re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|session[_-]?token|cookie)\s*[:=]\s*['\"][^'\"\s]{8,}"
    ),
}


def scan_public_tree(root: Path) -> list[Finding]:
    """Scan UTF-8 public-package files for likely personal or secret material."""
    findings: list[Finding] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in {".git", "__pycache__"} for part in path.parts):
            continue
        relative = path.relative_to(root)
        if relative.parts[:2] in {("smoke", "output"), ("demo", "output")}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(Finding(str(relative), "binary-file", 0))
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            for kind, pattern in SENSITIVE_PATTERNS.items():
                if pattern.search(line):
                    findings.append(Finding(str(relative), kind, line_number))
    return findings
