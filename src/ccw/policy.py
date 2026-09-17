from __future__ import annotations

from typing import Iterable, Mapping

from .compat import upstream_policy
from .errors import StateError, ValidationError, WorkForbiddenError
from .models import ALLOWED_MODES, ALLOWED_TASK_KINDS, FORBIDDEN_MODE


def normalize_mode(mode: str) -> str:
    normalized = mode.strip().lower().replace("_", "-")
    if normalized == FORBIDDEN_MODE:
        raise WorkForbiddenError("ChatGPT Work is permanently disabled in this bridge")
    if normalized not in ALLOWED_MODES:
        raise ValidationError(f"unsupported mode: {mode!r}; allowed: {', '.join(ALLOWED_MODES)}")
    return normalized


def choose_route(*, task_kind: str, requested_mode: str | None = None) -> str:
    normalized_kind = task_kind.strip().lower()
    if normalized_kind in {"artifact", "browser-action", "multi-step"}:
        raise WorkForbiddenError(
            f"task kind {task_kind!r} would require ChatGPT Work, which is disabled"
        )
    if requested_mode:
        return normalize_mode(requested_mode)
    if normalized_kind not in ALLOWED_TASK_KINDS:
        raise ValidationError(f"unsupported task kind: {task_kind!r}")
    if normalized_kind in {"source-research", "research-report"}:
        return "deep-research"
    return "chat-pro"


def required_capabilities(mode: str) -> frozenset[str]:
    normalized = normalize_mode(mode)
    base = {"send", "observe", "capture", "stable_identity"}
    return frozenset(base | ({"chat_pro"} if normalized == "chat-pro" else {"deep_research"}))


def validate_adapter_manifest(manifest: Mapping[str, object], *, mode: str) -> list[str]:
    issues: list[str] = []
    capabilities = frozenset(str(item) for item in manifest.get("capabilities", []))
    if FORBIDDEN_MODE in capabilities:
        issues.append("work-capability-forbidden")
    missing = required_capabilities(mode) - capabilities
    for item in sorted(missing):
        issues.append(f"missing-capability:{item}")
    if manifest.get("family") not in {"native-control-style", "oracle-style"}:
        issues.append("invalid-adapter-family")
    if manifest.get("kind") not in {"browser-thread-bridge", "saved-browser-session"}:
        issues.append("invalid-adapter-kind")
    return sorted(set(issues))


def preflight_from_dict(value: Mapping[str, object]) -> str:
    policy = upstream_policy()
    allowed = {
        "bridge_connected",
        "tab_bound",
        "identity_stable",
        "identity_reopenable",
        "expected_surface",
        "observed_surface",
        "observed_mode",
        "model_label",
        "mode_verified",
        "model_verified",
        "composer_interactive",
        "stable_read_count",
        "prompt_filled",
        "submission_count",
    }
    unknown = set(value) - allowed
    if unknown:
        raise ValidationError(f"unknown preflight fields: {', '.join(sorted(unknown))}")
    cleaned = {
        "bridge_connected": False,
        "tab_bound": False,
        "identity_stable": False,
        "identity_reopenable": False,
        "expected_surface": "chat",
        "observed_surface": None,
        "mode_verified": False,
        "model_verified": False,
        "composer_interactive": False,
        "stable_read_count": 0,
        "prompt_filled": False,
        "submission_count": 0,
    }
    cleaned.update({key: item for key, item in value.items() if key not in {"observed_mode", "model_label"}})
    observation = policy.PreflightObservation(**cleaned)
    return policy.preflight_decision(observation)


def submission_decision(state: str, *, original_turn_present: bool | None = None) -> str:
    return upstream_policy().submission_decision(state, original_turn_present)


def classify_completion(value: Mapping[str, object]) -> str:
    policy = upstream_policy()
    observation = policy.RunObservation(**value)
    return policy.classify_completion(observation).value


def recovery_decision(value: Mapping[str, object]) -> str:
    return upstream_policy().recovery_decision(**value)


def detect_presence(value: Mapping[str, object]) -> list[str]:
    policy = upstream_policy()
    present = policy.detect_backend_presence(
        exposed_tools=value.get("exposed_tools", []),
        exposed_skills=value.get("exposed_skills", []),
        executables=value.get("executables", []),
    )
    return sorted(present)


def select_adapter(
    *, mode: str, available: Mapping[str, Iterable[str]], requested_backend: str | None = None
) -> str | None:
    policy = upstream_policy()
    upstream_mode = policy.Mode(normalize_mode(mode))
    return policy.select_backend(
        upstream_mode, available, requested_backend=requested_backend
    )
