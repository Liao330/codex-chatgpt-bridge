from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import re
import uuid

from .compat import upstream_receipt
from .errors import StateError, ValidationError, WorkForbiddenError
from .fingerprint import prompt_fingerprint, scope_fingerprint, sha256_file, sha256_text
from .models import ALLOWED_MODES
from .policy import choose_route, normalize_mode, validate_adapter_manifest
from .storage import append_event, atomic_write_text, ensure_run_dir, read_json, run_dir, utc_now, write_json


RUN_ID_SAFE = re.compile(r"[^a-z0-9._-]+")


def _run_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:8]}"


def _state_path(run_id: str) -> Path:
    return ensure_run_dir(run_id) / "run.json"


def _private_path(run_id: str) -> Path:
    return ensure_run_dir(run_id) / "private.json"


def _event(state: dict[str, Any], kind: str, **fields: Any) -> None:
    event = {"at": utc_now(), "kind": kind, "status": state.get("status"), **fields}
    state.setdefault("events", []).append(event)
    append_event(state["run_id"], event)


def save_run(state: dict[str, Any]) -> None:
    state["updated_at"] = utc_now()
    write_json(_state_path(state["run_id"]), state)


def load_run(run_id: str) -> dict[str, Any]:
    path = _state_path(run_id)
    if not path.exists():
        raise StateError(f"run not found: {run_id}")
    return read_json(path)


def create_run(
    *,
    mode: str,
    task_kind: str,
    workspace: str | Path,
    prompt_text: str,
    adapter_manifest: dict[str, Any],
    allowed_paths: list[str] | None = None,
) -> dict[str, Any]:
    normalized_mode = choose_route(task_kind=task_kind, requested_mode=mode)
    issues = validate_adapter_manifest(adapter_manifest, mode=normalized_mode)
    if issues:
        raise ValidationError("adapter manifest failed: " + ", ".join(issues))
    prompt_text = prompt_text.strip()
    if not prompt_text:
        raise ValidationError("prompt must not be empty")
    workspace_path = str(Path(workspace).resolve())
    run_id = _run_id(normalized_mode)
    directory = ensure_run_dir(run_id)
    prompt_path = directory / "prompt.md"
    atomic_write_text(prompt_path, prompt_text + "\n", private=True)
    adapter = {
        "family": adapter_manifest["family"],
        "kind": adapter_manifest["kind"],
        "identity": adapter_manifest.get("identity", "native-codex-browser"),
        "capabilities": list(dict.fromkeys(adapter_manifest.get("capabilities", []))),
    }
    state: dict[str, Any] = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "mode": normalized_mode,
        "task_kind": task_kind,
        "workspace": workspace_path,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "status": "draft",
        "prompt": {
            "sha256": prompt_fingerprint(prompt_text),
            "bytes": len(prompt_text.encode("utf-8")),
            "text_stored": True,
            "path": prompt_path.name,
        },
        "authorization": {
            "scope_sha256": scope_fingerprint(workspace_path, allowed_paths),
            "prompt_sha256": prompt_fingerprint(prompt_text),
            "exact_prompt_approved": False,
            "authorized_at": None,
        },
        "adapter": adapter,
        "private": {
            "adapter_identity": adapter["identity"],
            "run_identity": f"run:{run_id}",
            "conversation_identity": None,
            "continuation_identity": f"run:{run_id}",
        },
        "submission": {
            "state": "not-sent",
            "count": 0,
            "acknowledgement_observed": False,
            "committed_at": None,
        },
        "route_evidence": {
            "surface": "chat",
            "mode": normalized_mode,
            "model_label": None,
            "mode_verified": False,
            "model_verified": False,
            "evidence_source": "visible-control",
            "observed_at": None,
        },
        "outcome": {
            "status": "unknown",
            "terminal_signal": False,
            "final_output_captured": False,
            "output_characters": 0,
            "artifacts": [],
            "citations": [],
            "completed_at": None,
            "raw_path": None,
            "raw_sha256": None,
        },
        "acceptance": {
            "verdict": "hold",
            "criteria": [],
            "evaluated_at": None,
        },
        "continuation": {
            "available": False,
            "private_locator_present": True,
            "identity_commitment": None,
        },
        "compression": {"status": "pending", "path": None, "schema_version": "1.0.0"},
        "verification": {"status": "pending", "path": None},
        "protocol": {
            "state": None,
            "iteration": 0,
            "task_id": None,
            "checkpoint": None,
            "updated_at": None,
        },
        "executions": [],
        "last_recovery": None,
        "events": [],
    }
    _event(state, "created", mode=normalized_mode, task_kind=task_kind)
    write_json(_private_path(run_id), {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "adapter_identity": adapter["identity"],
        "run_identity": f"run:{run_id}",
        "conversation_identity": None,
        "continuation_identity": f"run:{run_id}",
    }, private=True)
    save_run(state)
    return state


def authorize_run(run_id: str) -> dict[str, Any]:
    state = load_run(run_id)
    if state["mode"] == "work":
        raise WorkForbiddenError("ChatGPT Work is permanently disabled")
    state["authorization"]["exact_prompt_approved"] = True
    state["authorization"]["authorized_at"] = utc_now()
    state["status"] = "authorized"
    _event(state, "authorized", prompt_sha256=state["prompt"]["sha256"])
    save_run(state)
    return state


def record_preflight(run_id: str, observation: dict[str, Any]) -> dict[str, Any]:
    from .policy import preflight_from_dict

    state = load_run(run_id)
    action = preflight_from_dict(observation)
    ready = action in {"ready_to_fill_prompt", "ready_to_submit_once"}
    if ready:
        state["status"] = "prepared"
        state["route_evidence"].update(
            {
                "surface": observation.get("observed_surface") or observation.get("expected_surface") or "chat",
                "mode": observation.get("observed_mode") or state["mode"],
                "model_label": observation.get("model_label"),
                "mode_verified": bool(observation.get("mode_verified")),
                "model_verified": bool(observation.get("model_verified")),
                "observed_at": utc_now(),
            }
        )
    _event(state, "preflight", action=action, ready=ready)
    save_run(state)
    if not ready:
        raise StateError(f"preflight failed closed: {action}")
    return state


def begin_submit(run_id: str) -> dict[str, Any]:
    state = load_run(run_id)
    if state["status"] != "prepared":
        raise StateError(f"cannot submit from status {state['status']}")
    if state["submission"]["count"] != 0 or state["submission"]["state"] != "not-sent":
        raise StateError("submission already attempted; duplicate sends are forbidden")
    state["status"] = "committing"
    state["submission"]["state"] = "committing"
    _event(state, "submission-committing")
    save_run(state)
    return state


def confirm_submit(run_id: str, *, acknowledged: bool, conversation_identity: str | None = None) -> dict[str, Any]:
    state = load_run(run_id)
    if state["status"] != "committing":
        raise StateError(f"cannot confirm submit from status {state['status']}")
    if state["submission"]["count"] != 0:
        raise StateError("submission count already advanced")
    state["submission"]["count"] = 1
    state["submission"]["state"] = "committed"
    state["submission"]["acknowledgement_observed"] = bool(acknowledged)
    state["submission"]["committed_at"] = utc_now()
    if conversation_identity:
        state["private"]["conversation_identity"] = conversation_identity
    private = read_json(_private_path(run_id))
    private.update(state["private"])
    write_json(_private_path(run_id), private, private=True)
    state["status"] = "generating" if acknowledged else "unknown"
    _event(state, "submission-confirmed", acknowledged=bool(acknowledged))
    save_run(state)
    return state


def record_observation(run_id: str, observation: dict[str, Any]) -> dict[str, Any]:
    from .policy import classify_completion

    state = load_run(run_id)
    normalized = {
        "active_generation": None,
        "terminal_signal": False,
        "final_output_accessible": False,
        "partial_output_accessible": False,
        "artifact_expected": False,
        "artifact_accessible": False,
        "blocker": None,
    }
    normalized.update(observation)
    status = classify_completion(normalized)
    state["outcome"]["status"] = status
    state["outcome"]["terminal_signal"] = bool(normalized.get("terminal_signal", False))
    state["outcome"]["final_output_captured"] = bool(normalized.get("final_output_accessible", False))
    state["outcome"]["partial_output_captured"] = bool(normalized.get("partial_output_accessible", False))
    if normalized.get("blocker"):
        state["outcome"]["blocker"] = normalized["blocker"]
    if status in {"complete", "partial", "incomplete", "blocked", "unknown"}:
        state["status"] = status
    else:
        state["status"] = "generating"
    _event(state, "observed", classified=status)
    save_run(state)
    return state


def capture_raw(run_id: str, raw_text: str, *, terminal_signal: bool) -> dict[str, Any]:
    state = load_run(run_id)
    if state["submission"]["count"] != 1:
        raise StateError("raw capture requires one confirmed submission")
    directory = ensure_run_dir(run_id)
    raw_path = directory / "response.raw.md"
    atomic_write_text(raw_path, raw_text, private=True)
    state["outcome"]["raw_path"] = raw_path.name
    state["outcome"]["raw_sha256"] = sha256_file(raw_path)
    state["outcome"]["output_characters"] = len(raw_text)
    state["outcome"]["final_output_captured"] = terminal_signal
    state["outcome"]["terminal_signal"] = terminal_signal
    if terminal_signal:
        state["status"] = "complete"
        state["outcome"]["status"] = "complete"
        state["outcome"]["completed_at"] = utc_now()
    elif state["status"] not in {"partial", "incomplete", "blocked", "unknown"}:
        state["status"] = "partial"
        state["outcome"]["status"] = "partial"
    _event(state, "captured-raw", sha256=state["outcome"]["raw_sha256"], terminal=terminal_signal)
    save_run(state)
    return state


def record_recovery(run_id: str, value: dict[str, Any]) -> dict[str, Any]:
    from .policy import recovery_decision

    state = load_run(run_id)
    action = recovery_decision(value)
    state["last_recovery"] = {"input": value, "action": action, "resubmit": False, "at": utc_now()}
    if action == "mark_partial_no_resend":
        state["status"] = "partial"
    elif action == "mark_incomplete_no_resend":
        state["status"] = "incomplete"
    elif action == "mark_unknown_no_resend":
        state["status"] = "unknown"
    _event(state, "recovery", action=action, resubmit=False)
    save_run(state)
    return state


def set_compression(run_id: str, value: dict[str, Any], path: Path) -> dict[str, Any]:
    state = load_run(run_id)
    state["compression"] = {"status": "complete", "path": path.name, "schema_version": "1.0.0"}
    if value.get("citations"):
        state["outcome"]["citations"] = value["citations"]
    _event(state, "compressed", path=path.name)
    save_run(state)
    return state


def set_verification(run_id: str, value: dict[str, Any], path: Path) -> dict[str, Any]:
    state = load_run(run_id)
    status = "passed" if value.get("passed") else "needs-review"
    state["verification"] = {"status": status, "path": path.name}
    _event(state, "verified", status=status)
    save_run(state)
    return state


def finalize_run(run_id: str) -> dict[str, Any]:
    state = load_run(run_id)
    if state["status"] != "complete":
        raise StateError("only complete runs can be finalized")
    if not state["outcome"].get("raw_path"):
        raise StateError("raw response must be captured before finalization")
    if state["compression"]["status"] != "complete":
        raise StateError("compressed output must exist before finalization")
    if state["verification"]["status"] not in {"passed", "needs-review"}:
        raise StateError("verification must be recorded before finalization")

    receipt_mod = upstream_receipt()
    private = read_json(_private_path(run_id))
    adapter = state["adapter"]
    private_binding = {
        "private_sidecar_present": True,
        "adapter_identity_commitment": receipt_mod.identity_commitment("adapter", private["adapter_identity"]),
        "run_identity_commitment": receipt_mod.identity_commitment("run", private["run_identity"]),
        "continuation_identity_commitment": receipt_mod.identity_commitment(
            "continuation", private["continuation_identity"]
        ),
    }
    route = state["route_evidence"]
    if not route.get("model_label"):
        raise StateError("route evidence has no model label")
    outcome = state["outcome"]
    verification = read_json(run_dir(run_id) / state["verification"]["path"])
    verdict = "accept" if verification.get("passed") and state["verification"]["status"] == "passed" else "hold"
    criteria = [
        {
            "id": item.get("id", f"check-{index + 1}"),
            "status": "pass" if item.get("status") == "pass" else "fail" if item.get("status") == "fail" else "pending",
            "evidence_ref": item.get("evidence_ref", "verification.json"),
        }
        for index, item in enumerate(verification.get("checks", []))
    ]
    if not criteria:
        criteria = [{"id": "manual-review", "status": "pending", "evidence_ref": "verification.json"}]
    receipt = {
        "schema_version": "1.0.0",
        "receipt_id": run_id,
        "authorization": state["authorization"],
        "prompt": {
            "sha256": state["prompt"]["sha256"],
            "bytes": state["prompt"]["bytes"],
            "stored_in_public_receipt": False,
        },
        "adapter": {
            "family": adapter["family"],
            "kind": adapter["kind"],
            "runtime_claim": "style-mapping-only",
            "capabilities": adapter["capabilities"],
        },
        "private_binding": private_binding,
        "submission": state["submission"],
        "route_evidence": route,
        "outcome": {
            "status": outcome["status"],
            "terminal_signal": bool(outcome["terminal_signal"]),
            "final_output_captured": bool(outcome["final_output_captured"]),
            "output_characters": int(outcome["output_characters"]),
            "artifacts": [],
            "citations": list(outcome.get("citations", [])),
            "completed_at": outcome.get("completed_at"),
        },
        "acceptance": {
            "verdict": verdict,
            "criteria": criteria,
            "evaluated_at": utc_now(),
        },
        "continuation": {
            "available": True,
            "private_locator_present": True,
            "identity_commitment": private_binding["continuation_identity_commitment"],
        },
        "integrity": {
            "algorithm": "sha256",
            "covered_fields": list(receipt_mod.INTEGRITY_COVERED_FIELDS),
            "canonical_sha256": "0" * 64,
        },
    }
    # The adapter capability surface in the receipt never advertises Work.
    receipt["adapter"]["capabilities"] = [
        item for item in receipt["adapter"]["capabilities"] if item != "work"
    ]
    receipt = receipt_mod.seal_receipt(receipt)
    public_issues = receipt_mod.validate_public_receipt(receipt)
    private_issues = receipt_mod.validate_private_pair(receipt, {
        "schema_version": "1.0.0",
        "receipt_id": run_id,
        "synthetic_fixture": False,
        "adapter_identity": private["adapter_identity"],
        "run_identity": private["run_identity"],
        "continuation_identity": private["continuation_identity"],
    })
    if public_issues or private_issues:
        raise ValidationError(
            "receipt validation failed: " + "; ".join(public_issues + private_issues)
        )
    write_json(ensure_run_dir(run_id) / "receipt.public.json", receipt)
    write_json(ensure_run_dir(run_id) / "receipt.private.json", {
        "schema_version": "1.0.0",
        "receipt_id": run_id,
        "synthetic_fixture": False,
        "adapter_identity": private["adapter_identity"],
        "run_identity": private["run_identity"],
        "continuation_identity": private["continuation_identity"],
    }, private=True)
    state["status"] = "complete"
    state["finalized"] = True
    _event(state, "finalized", verdict=verdict)
    save_run(state)
    return {"state": state, "receipt": receipt}
