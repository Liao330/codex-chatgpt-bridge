#!/usr/bin/env python3
"""Dependency-free validation for adapter-neutral delegation receipts.

The public receipt contains evidence and cryptographic commitments only. Raw
adapter, run, and continuation identities belong in a separately protected
sidecar and are never accepted in a public receipt.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any, Iterable
from urllib.parse import urlparse


SCHEMA_VERSION = "1.0.0"
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
PUBLIC_TOP_LEVEL_FIELDS = (
    "schema_version",
    "receipt_id",
    "authorization",
    "prompt",
    "adapter",
    "private_binding",
    "submission",
    "route_evidence",
    "outcome",
    "acceptance",
    "continuation",
    "integrity",
)
INTEGRITY_COVERED_FIELDS = tuple(
    field for field in PUBLIC_TOP_LEVEL_FIELDS if field != "integrity"
)
RAW_PRIVATE_KEYS = {
    "adapter_identity",
    "run_identity",
    "continuation_identity",
    "conversation_url",
    "session_url",
    "private_path",
}
SENSITIVE_PUBLIC_PATTERNS = {
    "credential": re.compile(
        r"(?i)(?:\bsk-[A-Za-z0-9_-]{16,}\b|\bBearer\s+[A-Za-z0-9._~+/-]{12,}=*|"
        r"\b(?:api[_-]?key|access[_-]?token|session[_-]?token|cookie)\s*[:=]\s*[^\s]{8,})"
    ),
    "private-path": re.compile(
        r"/(?:Users|home)/[A-Za-z0-9._-]+/|(?<![A-Za-z0-9])~" + r"/"
    ),
    "conversation-url": re.compile(r"https://chatgpt\.com/(?:c|g)/[A-Za-z0-9_-]+"),
}


def canonical_receipt_bytes(receipt: dict[str, Any]) -> bytes:
    """Serialize every public field except the stored digest deterministically."""
    payload = deepcopy(receipt)
    integrity = payload.get("integrity")
    if isinstance(integrity, dict):
        integrity.pop("canonical_sha256", None)
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def receipt_digest(receipt: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_receipt_bytes(receipt)).hexdigest()


def seal_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    sealed = deepcopy(receipt)
    sealed.setdefault("integrity", {})["canonical_sha256"] = receipt_digest(sealed)
    return sealed


def identity_commitment(kind: str, raw_identity: str) -> str:
    """Domain-separated commitment for a value retained only in the sidecar."""
    return hashlib.sha256(f"delegation-receipt:{kind}:{raw_identity}".encode()).hexdigest()


def _walk(value: Any, path: str = "$") -> Iterable[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            yield child_path, key, child
            yield from _walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            yield child_path, str(index), child
            yield from _walk(child, child_path)


def _require_hash(issues: list[str], value: Any, name: str) -> None:
    if not isinstance(value, str) or not HASH_RE.fullmatch(value):
        issues.append(f"invalid-hash:{name}")


def validate_public_receipt(receipt: dict[str, Any]) -> list[str]:
    """Return deterministic semantic, privacy, and integrity issues."""
    issues: list[str] = []
    if set(receipt) != set(PUBLIC_TOP_LEVEL_FIELDS):
        issues.append("top-level-shape-mismatch")
    if receipt.get("schema_version") != SCHEMA_VERSION:
        issues.append("schema-version-mismatch")
    if not isinstance(receipt.get("receipt_id"), str) or not receipt["receipt_id"]:
        issues.append("invalid-receipt-id")

    for path, key, value in _walk(receipt):
        if key in RAW_PRIVATE_KEYS:
            issues.append(f"raw-private-field:{path}")
        if isinstance(value, str):
            for kind, pattern in SENSITIVE_PUBLIC_PATTERNS.items():
                if pattern.search(value):
                    issues.append(f"sensitive-public-field:{kind}:{path}")

    authorization = receipt.get("authorization", {})
    prompt = receipt.get("prompt", {})
    _require_hash(issues, prompt.get("sha256"), "prompt.sha256")
    _require_hash(issues, authorization.get("scope_sha256"), "authorization.scope_sha256")
    _require_hash(issues, authorization.get("prompt_sha256"), "authorization.prompt_sha256")
    if authorization.get("prompt_sha256") != prompt.get("sha256"):
        issues.append("authorization-prompt-binding-mismatch")
    if authorization.get("exact_prompt_approved") is not True:
        issues.append("authorization-not-bound")

    adapter = receipt.get("adapter", {})
    if adapter.get("runtime_claim") != "style-mapping-only":
        issues.append("adapter-compatibility-overclaim")
    if adapter.get("family") not in {"native-control-style", "oracle-style"}:
        issues.append("unsupported-adapter-family")

    binding = receipt.get("private_binding", {})
    if binding.get("private_sidecar_present") is not True:
        issues.append("private-sidecar-missing")
    for name in (
        "adapter_identity_commitment",
        "run_identity_commitment",
        "continuation_identity_commitment",
    ):
        _require_hash(issues, binding.get(name), f"private_binding.{name}")

    submission = receipt.get("submission", {})
    count = submission.get("count")
    state = submission.get("state")
    if type(count) is not int or count not in {0, 1}:
        issues.append("invalid-submission-count")
    if state not in {"not-sent", "committing", "committed"}:
        issues.append("invalid-submission-state")
    if count == 0 and state != "not-sent":
        issues.append("submission-state-count-mismatch")
    if count == 1 and state not in {"committing", "committed"}:
        issues.append("submission-state-count-mismatch")
    if state == "committed" and submission.get("acknowledgement_observed") is not True:
        issues.append("missing-submit-acknowledgement")

    route = receipt.get("route_evidence", {})
    if route.get("surface") not in {"chat", "work"}:
        issues.append("invalid-route-surface")
    if route.get("mode") not in {"chat-pro", "deep-research", "work"}:
        issues.append("invalid-route-mode")
    if not route.get("model_label") or route.get("mode_verified") is not True:
        issues.append("missing-mode-model-evidence")
    if route.get("model_verified") is not True:
        issues.append("missing-mode-model-evidence")

    outcome = receipt.get("outcome", {})
    status = outcome.get("status")
    if status not in {"generating", "complete", "partial", "incomplete", "blocked", "unknown"}:
        issues.append("invalid-outcome-status")
    if status == "complete" and (
        outcome.get("terminal_signal") is not True
        or outcome.get("final_output_captured") is not True
    ):
        issues.append("false-complete")
    if status == "generating" and outcome.get("terminal_signal") is not False:
        issues.append("generating-terminal-conflict")
    for artifact in outcome.get("artifacts", []):
        _require_hash(issues, artifact.get("sha256"), "outcome.artifacts[].sha256")
        if type(artifact.get("bytes")) is not int or artifact["bytes"] < 0:
            issues.append("invalid-artifact-size")
    for citation in outcome.get("citations", []):
        parsed = urlparse(citation)
        if parsed.scheme != "https" or not parsed.netloc:
            issues.append("invalid-citation-url")

    acceptance = receipt.get("acceptance", {})
    verdict = acceptance.get("verdict")
    if verdict not in {"accept", "hold", "reject"}:
        issues.append("invalid-acceptance-verdict")
    if verdict == "accept" and status != "complete":
        issues.append("accept-without-complete")
    if not isinstance(acceptance.get("criteria"), list) or not acceptance["criteria"]:
        issues.append("missing-acceptance-criteria")

    continuation = receipt.get("continuation", {})
    if continuation.get("available") is True:
        if continuation.get("private_locator_present") is not True:
            issues.append("continuation-private-locator-missing")
        _require_hash(
            issues,
            continuation.get("identity_commitment"),
            "continuation.identity_commitment",
        )
        if continuation.get("identity_commitment") != binding.get(
            "continuation_identity_commitment"
        ):
            issues.append("continuation-commitment-mismatch")

    integrity = receipt.get("integrity", {})
    if integrity.get("algorithm") != "sha256":
        issues.append("unsupported-integrity-algorithm")
    if tuple(integrity.get("covered_fields", ())) != INTEGRITY_COVERED_FIELDS:
        issues.append("integrity-coverage-mismatch")
    _require_hash(issues, integrity.get("canonical_sha256"), "integrity.canonical_sha256")
    if integrity.get("canonical_sha256") != receipt_digest(receipt):
        issues.append("integrity-mismatch")
    return sorted(set(issues))


def validate_private_pair(
    public_receipt: dict[str, Any], private_sidecar: dict[str, Any]
) -> list[str]:
    """Verify raw private identities against the public commitments."""
    issues: list[str] = []
    if private_sidecar.get("receipt_id") != public_receipt.get("receipt_id"):
        issues.append("sidecar-receipt-id-mismatch")
    binding = public_receipt.get("private_binding", {})
    continuation = public_receipt.get("continuation", {})
    for kind, sidecar_key, commitment_key in (
        ("adapter", "adapter_identity", "adapter_identity_commitment"),
        ("run", "run_identity", "run_identity_commitment"),
        ("continuation", "continuation_identity", "continuation_identity_commitment"),
    ):
        raw = private_sidecar.get(sidecar_key)
        if not isinstance(raw, str) or not raw:
            issues.append(f"missing-private-identity:{sidecar_key}")
            continue
        if identity_commitment(kind, raw) != binding.get(commitment_key):
            issues.append(f"private-commitment-mismatch:{sidecar_key}")
    if continuation.get("identity_commitment") != binding.get(
        "continuation_identity_commitment"
    ):
        issues.append("public-continuation-binding-mismatch")
    return sorted(set(issues))


def should_submit(receipt: dict[str, Any], proposed_prompt_sha256: str) -> bool:
    """Allow only the initial submit path; never decide to duplicate a run."""
    if validate_public_receipt(receipt):
        return False
    return (
        receipt["submission"]["count"] == 0
        and receipt["submission"]["state"] == "not-sent"
        and receipt["prompt"]["sha256"] == proposed_prompt_sha256
        and receipt["authorization"]["prompt_sha256"] == proposed_prompt_sha256
    )
