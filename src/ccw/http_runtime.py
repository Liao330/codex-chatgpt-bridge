"""Opt-in HTTP execution with durable, single-attempt submission.

Credentials and server locators are confined to memory/private sidecars.
"""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import os
import re
import threading
import uuid

from .errors import StateError, ValidationError
from .fingerprint import prompt_fingerprint
from .state import load_run, save_run, invalidate_http_derivatives
from .storage import ccw_home, run_dir, read_json, write_json, utc_now, atomic_write_text
from .fingerprint import sha256_file, sha256_text


_held_locks = threading.local()

_ERROR_CODES = frozenset({
    "authentication_required", "invalid_endpoint", "http_client_unavailable",
    "response_deadline", "redirect_rejected", "authentication_or_challenge_required",
    "response_too_large", "transport_error", "unsupported_or_invalid_sse",
    "conversation_mismatch", "conversation_unverified", "locator_persistence_failed",
    "account_unverified", "invalid_conversation_response", "assistant_branch_unverified",
    "user_branch_unverified", "model_unverified_or_mismatch", "invalid_locator",
    "unsupported_conversation_listing", "conversation_identity_ambiguous",
    "conversation_not_located", "invalid_recovery_response", "identity_unverified",
    "invalid_intent", "project_context_protocol_unverified",
    "challenge_required", "requirements_invalid", "conversation_prepare_failed",
    "preparation_response_invalid", "project_membership_mismatch",
})


def _safe_error(value):
    if value is None:
        return None
    if isinstance(value, str) and (value in _ERROR_CODES or re.fullmatch(r"http_status_[1-5][0-9]{2}", value)):
        return value
    return "unclassified_error"


@contextmanager
def process_lock(identity):
    directory = ccw_home() / "http-locks"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (sha256(identity.encode()).hexdigest() + ".lock")
    key = (os.getpid(), str(path.resolve()))
    held = getattr(_held_locks, "keys", set())
    if key in held:
        yield
        return
    with path.open("a+b") as handle:
        handle.seek(0)
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise StateError("HTTP execution is already locked") from None
        _held_locks.keys = held | {key}
        try:
            yield
        finally:
            _held_locks.keys = held
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def load_config(path, *, for_probe=False):
    try:
        config = read_json(Path(path))
        if not isinstance(config, dict):
            raise ValueError()
        if config.get("access_token") or config.get("token"):
            raise ValueError()
        from .credentials import load_access_token
        config["access_token"] = load_access_token(config.get("credentials_file"))
        if not for_probe:
            validate_config(config)
        return config
    except Exception:
        raise ValidationError("invalid HTTP configuration") from None


def validate_config(config):
    for key in ("model", "account_hash", "expected_connector", "expected_tool"):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValidationError("HTTP configuration requires model/account/MCP binding")
    if not (config.get("access_token") or config.get("token")):
        raise ValidationError("HTTP credentials unavailable")
    if config.get("context"):
        raise ValidationError("HTTP project/context unsupported")
    if config.get("project_id") and not re.fullmatch(r"g-p-[0-9a-f]{32}", str(config["project_id"])):
        raise ValidationError("HTTP project identifier invalid")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", config["model"]):
        raise ValidationError("HTTP model identifier invalid")
    if config.get("conversation_id") and not config.get("parent_message_id"):
        raise ValidationError("HTTP continuation requires exact parent identity")
    proxy = config.get("proxy")
    if proxy is not None and (not isinstance(proxy, str) or not re.fullmatch(r"https?://[^\s]{1,200}", proxy)):
        raise ValidationError("HTTP proxy invalid")
    fallback = config.get("fallback_model")
    if fallback is not None and (not isinstance(fallback, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", fallback)):
        raise ValidationError("HTTP fallback model invalid")


def _binding(config):
    return {key: config.get(key) for key in (
        "account_hash", "model", "expected_connector", "expected_tool", "project_id", "context", "conversation_id", "parent_message_id")}


def _private(run_id):
    return read_json(run_dir(run_id) / "private.json")


def _save_private(run_id, value):
    try:
        write_json(run_dir(run_id) / "private.json", value, private=True)
    except Exception:
        raise StateError("HTTP private persistence failed") from None


_LOCATOR_IDENTITY = ("user_message_id", "parent_message_id", "requested_model",
                     "account_hash", "expected_connector", "expected_tool")


def _identity_value_ok(key, returned_value, locator_value, config):
    """True when an identity field matches, allowing a requested-model fallback.

    The requested model may legitimately change from the configured model to the
    configured fallback_model when the server refuses the requested model (for
    example a Pro model on a non-Pro account). Every other field must match.
    """
    if returned_value == locator_value:
        return True
    if key == "requested_model":
        fallback = config.get("fallback_model")
        return bool(fallback) and returned_value == fallback and locator_value == config.get("model")
    return False


def _validate_locator(private, config):
    locator, intent = private.get("http_locator"), private.get("http_intent")
    if not isinstance(locator, dict) or not isinstance(intent, dict):
        raise StateError("HTTP recovery requires persisted intent")
    for key in _LOCATOR_IDENTITY:
        value = locator.get(key)
        if not isinstance(value, str) or not value or value != intent.get(key):
            raise StateError("HTTP recovery identity mismatch")
    for key, binding in (("requested_model", "model"), ("account_hash", "account_hash"),
                         ("expected_connector", "expected_connector"), ("expected_tool", "expected_tool")):
        if locator[key] != config[binding]:
            raise StateError("HTTP recovery binding mismatch")
    cid = locator.get("conversation_id")
    if cid is not None and (not isinstance(cid, str) or not cid):
        raise StateError("HTTP recovery conversation mismatch")
    if intent.get("conversation_id") and cid != intent["conversation_id"]:
        raise StateError("HTTP recovery conversation mismatch")
    return locator


def _persist_locator(run_id, config, returned):
    private = _private(run_id)
    locator = _validate_locator(private, config)
    if not isinstance(returned, dict):
        raise StateError("HTTP recovery identity mismatch")
    for key in _LOCATOR_IDENTITY:
        if not _identity_value_ok(key, returned.get(key), locator[key], config):
            raise StateError("HTTP recovery identity mismatch")
    cid = returned.get("conversation_id")
    if not isinstance(cid, str) or not cid or (locator.get("conversation_id") and cid != locator["conversation_id"]):
        raise StateError("HTTP recovery conversation mismatch")
    private["http_locator"] = dict(locator, conversation_id=cid)
    _save_private(run_id, private)


def _prompt(state):
    text = (run_dir(state["run_id"]) / "prompt.md").read_text(encoding="utf-8").strip()
    fingerprint = prompt_fingerprint(text)
    auth = state["authorization"]
    if not auth.get("exact_prompt_approved") or fingerprint != auth.get("prompt_sha256") or fingerprint != state["prompt"]["sha256"]:
        raise StateError("HTTP prompt authorization mismatch")
    return text


def _client(config, client):
    if client is not None:
        return client
    from .web_http import BridgeHttpClient
    return BridgeHttpClient(config)


def _check(state, config):
    validate_config(config)
    if state["adapter"]["kind"] != "web-http" or state["mode"] != "chat-pro":
        raise StateError("HTTP supports only opt-in chat-pro runs")
    _prompt(state)


def _probe(client, config):
    try:
        result = client.probe()
    except Exception:
        raise StateError("HTTP preflight unavailable") from None
    if result.get("account_hash") != config["account_hash"]:
        raise StateError("HTTP account binding mismatch")
    if result.get("state") in {"unsupported", "failed", "unknown"}:
        raise StateError("HTTP preflight unsupported")
    return result


def probe_http(config):
    result = _client(config, None).probe()
    return {"state": result.get("state", "unknown"), "account_hash": result.get("account_hash"),
            "model_available": result.get("model_verified") is True,
            "models": [slug for slug in result.get("models", []) if isinstance(slug, str)
                       and re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", slug)][:100],
            "error_code": result.get("error_code")}


def preflight_http(run_id, config, *, client=None):
    with process_lock("run:" + run_id):
        state = load_run(run_id)
        _check(state, config)
        if state["submission"]["state"] != "not-sent":
            raise StateError("HTTP submission already attempted")
        _probe(_client(config, client), config)
        private = _private(run_id)
        if "http_intent" in private:
            raise StateError("HTTP durable submission intent exists; recover only")
        existing = private.get("http_binding")
        if existing is not None and existing != _binding(config):
            raise StateError("HTTP binding cannot change")
        private["http_binding"] = _binding(config)
        _save_private(run_id, private)
        state["status"] = "prepared"
        state["route_evidence"].update(evidence_source="http-server", mode_verified=False, model_verified=False)
        save_run(state)
        return public_status(state)


def public_status(state):
    return {"run_id": state["run_id"], "status": state["status"],
            "submission_count": state["submission"]["count"],
            "model_verified": state["route_evidence"].get("model_verified", False),
            "mcp_verified": state.get("http_evidence", {}).get("mcp_verified", False),
            "review_complete": state.get("http_evidence", {}).get("review_complete", False),
            "error_code": _safe_error(state.get("http_evidence", {}).get("error_code"))}


def _apply(run_id, state, config, observation):
    private = _private(run_id)
    locator = _validate_locator(private, config)
    returned = observation.get("locator") or {}
    for key in _LOCATOR_IDENTITY:
        if returned and not _identity_value_ok(key, returned.get(key), locator.get(key), config):
            raise StateError("HTTP recovery identity mismatch")
    if locator.get("conversation_id") and returned.get("conversation_id") not in (None, locator["conversation_id"]):
        raise StateError("HTTP recovery conversation mismatch")
    if observation.get("account_hash") not in (None, config["account_hash"]):
        raise StateError("HTTP recovery account mismatch")
    if returned.get("conversation_id"):
        if not isinstance(returned["conversation_id"], str):
            raise StateError("HTTP recovery conversation mismatch")
        locator["conversation_id"] = returned["conversation_id"]
    if returned.get("requested_model") and returned["requested_model"] != locator.get("requested_model"):
        locator["requested_model"] = returned["requested_model"]
    private["http_locator"] = locator
    _save_private(run_id, private)
    actual = observation.get("actual_model")
    route = observation.get("route_evidence") or {}
    requested_model = returned.get("requested_model") or config["model"]
    model_ok = bool(actual and actual == requested_model and route.get("actual_model") == actual
                    and route.get("provenance") == "conversation_mapping_metadata")
    tools = observation.get("tool_evidence") or []
    mcp_ok = any(isinstance(item, dict) and item.get("source") == "http-server"
                 and item.get("connector") == config["expected_connector"]
                 and item.get("tool") == config["expected_tool"]
                 and item.get("read_only") is True and item.get("message_id")
                 and item.get("provenance") == "conversation_mapping_tool_metadata" for item in tools)
    terminal = observation.get("terminal_evidence") or {}
    terminal_hash = sha256_text(str(terminal["message_id"])) if terminal.get("message_id") else None
    text = observation.get("text")
    raw_changed = isinstance(text, str) and bool(text) and sha256_text(text) != state["outcome"].get("raw_sha256")
    complete = (observation.get("state") == "complete" and observation.get("complete") is True
                and bool(returned) and bool(locator.get("conversation_id"))
                and observation.get("identity_verified") is True and terminal.get("message_id")
                and terminal.get("status") == "finished_successfully" and terminal.get("end_turn") is True
                and observation.get("account_hash") == config["account_hash"] and model_ok and mcp_ok)
    evidence_downgraded = state.get("http_evidence", {}).get("review_complete") and not complete
    if raw_changed or terminal_hash != state["outcome"].get("terminal_identity_sha256") or evidence_downgraded:
        invalidate_http_derivatives(state)
        state["outcome"]["terminal_identity_sha256"] = terminal_hash
    if not complete:
        state["outcome"].update(final_output_captured=False, terminal_signal=False, completed_at=None)
    private["http_server_evidence"] = {"route": route, "terminal": terminal, "tools": tools}
    _save_private(run_id, private)
    state["route_evidence"].update(model_label=requested_model if model_ok else None,
        model_verified=model_ok, mode_verified=model_ok, evidence_source="http-server", observed_at=utc_now())
    state["route_evidence"]["mcp_verified"] = bool(mcp_ok)
    state["route_evidence"]["server_provenance"] = "conversation_mapping_metadata" if model_ok else "unverified"
    state["http_evidence"] = {"source": "http-server", "mcp_verified": mcp_ok,
                              "review_complete": bool(complete),
                              "error_code": _safe_error(observation.get("error_code"))}
    state["submission"]["acknowledgement_observed"] = bool(observation.get("acknowledged"))
    state["submission"]["state"] = "committed"
    state["status"] = "complete" if complete else "partial" if observation.get("text") else "unknown"
    state["outcome"]["status"] = state["status"]
    save_run(state)
    if isinstance(text, str) and text:
        path = run_dir(run_id) / "response.raw.md"
        atomic_write_text(path, text, private=True)
        state["outcome"].update(raw_path=path.name, raw_sha256=sha256_file(path),
            output_characters=len(text), final_output_captured=bool(complete), terminal_signal=bool(complete),
            completed_at=utc_now() if complete else None)
        save_run(state)
    return public_status(state)


def execute_http(run_id, config, *, client=None):
    with process_lock("run:" + run_id):
        state = load_run(run_id)
        _check(state, config)
        private = _private(run_id)
        if "http_intent" in private:
            raise StateError("HTTP durable submission intent exists; recover only")
        if private.get("http_binding") != _binding(config):
            raise StateError("HTTP preflight binding missing or changed")
        if state["status"] != "prepared" or state["submission"]["state"] != "not-sent" or state["submission"]["count"]:
            raise StateError("HTTP duplicate submission forbidden; recover only")
        http = _client(config, client)
        _probe(http, config)
        locator = {"conversation_id": config.get("conversation_id"),
                   "user_message_id": str(uuid.uuid4()), "parent_message_id": config.get("parent_message_id") or str(uuid.uuid4()),
                   "requested_model": config["model"], "account_hash": config["account_hash"],
                   "expected_connector": config["expected_connector"], "expected_tool": config["expected_tool"]}
        identity = "conversation:" + config["account_hash"] + ":" + str(locator["conversation_id"] or run_id)
        with process_lock(identity):
            private["http_locator"] = locator
            private["http_intent"] = {**locator, "project_id": config.get("project_id"), "prompt_sha256": state["prompt"]["sha256"]}
            _save_private(run_id, private)
            state["status"] = "committing"
            state["submission"].update(state="committing", count=1, committed_at=utc_now())
            save_run(state)
            intent = {"text": _prompt(state), "model": config["model"], **locator,
                      "project_id": config.get("project_id"), "context": config.get("context")}
            try:
                if hasattr(http, "set_locator_callback"):
                    http.set_locator_callback(lambda value: _persist_locator(run_id, config, value))
                observation = http.submit(intent)
            except Exception:
                state["status"] = "unknown"
                state["outcome"]["status"] = "unknown"
                state["http_evidence"] = {"error_code": "transport_error"}
                save_run(state)
                return public_status(state)
            return _apply(run_id, state, config, observation)


def recover_http(run_id, config, *, client=None):
    with process_lock("run:" + run_id):
        state = load_run(run_id)
        _check(state, config)
        private = _private(run_id)
        if private.get("http_binding") != _binding(config):
            raise StateError("HTTP recovery binding mismatch")
        locator = _validate_locator(private, config)
        http = _client(config, client)
        _probe(http, config)
        if state["submission"]["count"] == 0:
            state["submission"].update(count=1, state="committing", committed_at=utc_now())
            state["status"] = "unknown"
            save_run(state)
        with process_lock("conversation:" + config["account_hash"] + ":" + str(locator.get("conversation_id") or run_id)):
            try:
                observation = http.recover(locator)
            except Exception:
                observation = {"state": "unknown", "error_code": "transport_error"}
            return _apply(run_id, state, config, observation)
