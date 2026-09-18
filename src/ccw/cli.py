from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from . import __version__
from .c2c import build_bridge, detect_environment, run_c2c
from .compressor import compress_response, validate_compressed
from .cycle import record_execution, record_handoff, set_protocol_state
from .data_plane import load_and_validate
from .errors import CCWError, StateError, ValidationError, WorkForbiddenError
from .policy import (
    choose_route,
    normalize_mode,
    preflight_from_dict,
    required_capabilities,
    select_adapter,
    validate_adapter_manifest,
)
from .state import (
    authorize_run,
    begin_submit,
    capture_raw,
    confirm_submit,
    create_run,
    finalize_run,
    load_run,
    record_observation,
    record_preflight,
    record_recovery,
    set_compression,
    set_verification,
)
from .storage import read_json, run_dir, write_json
from .verifier import verify_compressed


def _read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))


def _read_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    if args.prompt_text:
        return args.prompt_text
    raise ValidationError("provide --prompt-file or --prompt-text")


def command_route_plan(args: argparse.Namespace) -> int:
    mode = choose_route(task_kind=args.task_kind, requested_mode=args.mode)
    capabilities_doc = _read_json(args.capabilities)
    available = capabilities_doc.get("backends", capabilities_doc)
    backend = select_adapter(
        mode=mode, available=available, requested_backend=args.requested_backend
    )
    _print(
        {
            "mode": mode,
            "required_capabilities": sorted(required_capabilities(mode)),
            "backend": backend,
            "transmission_authorized": False,
            "work_forbidden": True,
            "next_action": (
                "prepare-exact-prompt-and-request-confirmation"
                if backend
                else "fail-closed-no-capable-backend"
            ),
        }
    )
    return 0 if backend else 2


def command_adapter_check(args: argparse.Namespace) -> int:
    manifest = _read_json(args.manifest)
    issues = validate_adapter_manifest(manifest, mode=args.mode)
    _print(
        {
            "mode": normalize_mode(args.mode),
            "valid": not issues,
            "issues": issues,
            "work_forbidden": True,
        }
    )
    return 0 if not issues else 2


def command_adapter_detect(args: argparse.Namespace) -> int:
    from .policy import detect_presence

    inventory = _read_json(args.inventory)
    present = detect_presence(inventory)
    _print(
        {
            "present_backends": present,
            "presence_is_capability": False,
            "next_action": "observe and verify send/observe/capture/stable_identity before use",
        }
    )
    return 0 if present else 2


def command_preflight_check(args: argparse.Namespace) -> int:
    observation = _read_json(args.observation)
    action = preflight_from_dict(observation)
    ready = action in {"ready_to_fill_prompt", "ready_to_submit_once"}
    _print({"action": action, "ready": ready, "send": False})
    return 0 if ready else 2


def command_run_init(args: argparse.Namespace) -> int:
    manifest = _read_json(args.adapter_manifest)
    state = create_run(
        mode=args.mode,
        task_kind=args.task_kind,
        workspace=args.workspace,
        prompt_text=_read_prompt(args),
        adapter_manifest=manifest,
        allowed_paths=args.allowed_path,
    )
    _print({"run_id": state["run_id"], "status": state["status"], "mode": state["mode"]})
    return 0


def command_run_authorize(args: argparse.Namespace) -> int:
    state = authorize_run(args.run_id)
    _print({"run_id": args.run_id, "status": state["status"]})
    return 0


def command_run_preflight(args: argparse.Namespace) -> int:
    observation = _read_json(args.observation)
    try:
        state = record_preflight(args.run_id, observation)
    except StateError as error:
        _print({"run_id": args.run_id, "ready": False, "error": str(error), "send": False})
        return 2
    _print({"run_id": args.run_id, "status": state["status"], "ready": True, "send": False})
    return 0


def command_run_begin_submit(args: argparse.Namespace) -> int:
    state = begin_submit(args.run_id)
    _print({"run_id": args.run_id, "status": state["status"], "submission": state["submission"]})
    return 0


def command_run_confirm_submit(args: argparse.Namespace) -> int:
    state = confirm_submit(
        args.run_id,
        acknowledged=not args.unknown,
        conversation_identity=args.conversation_identity,
    )
    _print({"run_id": args.run_id, "status": state["status"], "submission": state["submission"]})
    return 0


def command_run_observe(args: argparse.Namespace) -> int:
    observation = _read_json(args.observation)
    state = record_observation(args.run_id, observation)
    _print({"run_id": args.run_id, "status": state["status"], "outcome": state["outcome"]})
    return 0


def command_run_capture(args: argparse.Namespace) -> int:
    raw = Path(args.raw_file).read_text(encoding="utf-8")
    state = capture_raw(args.run_id, raw, terminal_signal=args.terminal_signal)
    _print({"run_id": args.run_id, "status": state["status"], "outcome": state["outcome"]})
    return 0


def command_run_recover(args: argparse.Namespace) -> int:
    state = record_recovery(args.run_id, _read_json(args.observation))
    _print({"run_id": args.run_id, "status": state["status"], "recovery": state["last_recovery"]})
    return 0


def command_run_compress(args: argparse.Namespace) -> int:
    state = load_run(args.run_id)
    raw_path = run_dir(args.run_id) / state["outcome"]["raw_path"]
    response = compress_response(raw_path.read_text(encoding="utf-8"), mode=state["mode"], raw_path=raw_path)
    issues = validate_compressed(response)
    if issues:
        raise ValidationError("compressed output failed validation: " + ", ".join(issues))
    output_path = run_dir(args.run_id) / "compressed.json"
    write_json(output_path, response)
    set_compression(args.run_id, response, output_path)
    _print({"run_id": args.run_id, "path": str(output_path), "summary": response["summary"]})
    return 0


def command_run_verify(args: argparse.Namespace) -> int:
    state = load_run(args.run_id)
    compressed_path = run_dir(args.run_id) / state["compression"]["path"]
    compressed = read_json(compressed_path)
    result = verify_compressed(
        compressed,
        workspace=state["workspace"],
        raw_sha256=state["outcome"].get("raw_sha256"),
    )
    output_path = run_dir(args.run_id) / "verification.json"
    write_json(output_path, result)
    set_verification(args.run_id, result, output_path)
    _print({"run_id": args.run_id, "path": str(output_path), **result})
    return 0 if result["passed"] else 4


def command_run_finalize(args: argparse.Namespace) -> int:
    result = finalize_run(args.run_id)
    _print(
        {
            "run_id": args.run_id,
            "receipt": str(run_dir(args.run_id) / "receipt.public.json"),
            "verdict": result["receipt"]["acceptance"]["verdict"],
            "status": result["state"]["status"],
        }
    )
    return 0


def command_run_status(args: argparse.Namespace) -> int:
    state = load_run(args.run_id)
    _print(
        {
            "run_id": state["run_id"],
            "mode": state["mode"],
            "status": state["status"],
            "submission_count": state["submission"]["count"],
            "outcome": state["outcome"]["status"],
            "compression": state["compression"]["status"],
            "verification": state["verification"]["status"],
            "finalized": bool(state.get("finalized", False)),
        }
    )
    return 0


def command_c2c_detect(args: argparse.Namespace) -> int:
    _print(detect_environment())
    return 0


def command_c2c_build(args: argparse.Namespace) -> int:
    _print(build_bridge(timeout=args.timeout))
    return 0


def command_c2c_exec(args: argparse.Namespace) -> int:
    forwarded = list(args.args)
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    if not forwarded:
        raise ValidationError("provide C2C arguments after `--`")
    return run_c2c(forwarded)


def command_cycle_set(args: argparse.Namespace) -> int:
    protocol = set_protocol_state(
        args.run_id,
        state_name=args.state,
        iteration=args.iteration,
        task_id=args.task_id,
        checkpoint=args.checkpoint,
    )
    _print({"run_id": args.run_id, "protocol": protocol})
    return 0


def command_cycle_execution(args: argparse.Namespace) -> int:
    record = record_execution(
        args.run_id,
        iteration=args.iteration,
        changed_files=args.changed_file,
        tests=args.tests,
        exit_status=args.exit_status,
        command=args.command,
        output_file=args.output_file,
    )
    _print({"run_id": args.run_id, "execution": record})
    return 0


def command_cycle_handoff(args: argparse.Namespace) -> int:
    if args.brief_file:
        brief = Path(args.brief_file).read_text(encoding="utf-8")
    elif args.brief_text:
        brief = args.brief_text
    else:
        raise ValidationError("provide --brief-file or --brief-text")
    record = record_handoff(args.run_id, brief)
    _print({"run_id": args.run_id, "handoff": record})
    return 0


def command_cycle_status(args: argparse.Namespace) -> int:
    state = load_run(args.run_id)
    _print({"run_id": args.run_id, "protocol": state.get("protocol"), "executions": state.get("executions", [])})
    return 0


def command_data_validate(args: argparse.Namespace) -> int:
    value = load_and_validate(args.manifest)
    _print({"valid": True, "data_source": value["id"], "kind": value["kind"]})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ccw",
        description="Review-only ChatGPT Web orchestration for Codex (Work permanently forbidden).",
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="group", required=True)

    route = sub.add_parser("route", help="route planning and policy")
    route_sub = route.add_subparsers(dest="command", required=True)
    route_plan = route_sub.add_parser("plan", help="plan a route without sending")
    route_plan.add_argument("--task-kind", required=True)
    route_plan.add_argument("--mode", choices=("chat-pro", "deep-research"))
    route_plan.add_argument("--capabilities", required=True)
    route_plan.add_argument("--requested-backend")
    route_plan.set_defaults(func=command_route_plan)

    adapter = sub.add_parser("adapter", help="adapter capability checks")
    adapter_sub = adapter.add_subparsers(dest="command", required=True)
    adapter_check = adapter_sub.add_parser("check", help="validate an adapter manifest")
    adapter_check.add_argument("--manifest", required=True)
    adapter_check.add_argument("--mode", required=True, choices=("chat-pro", "deep-research"))
    adapter_check.set_defaults(func=command_adapter_check)
    adapter_detect = adapter_sub.add_parser("detect", help="classify a read-only tool/skill inventory")
    adapter_detect.add_argument("--inventory", required=True)
    adapter_detect.set_defaults(func=command_adapter_detect)

    preflight = sub.add_parser("preflight", help="read-only preflight evaluation")
    preflight_sub = preflight.add_subparsers(dest="command", required=True)
    preflight_check = preflight_sub.add_parser("check", help="evaluate an adapter observation")
    preflight_check.add_argument("--observation", required=True)
    preflight_check.set_defaults(func=command_preflight_check)

    run = sub.add_parser("run", help="run lifecycle")
    run_sub = run.add_subparsers(dest="command", required=True)

    run_init = run_sub.add_parser("init")
    run_init.add_argument("--mode", required=True, choices=("chat-pro", "deep-research"))
    run_init.add_argument("--task-kind", required=True)
    run_init.add_argument("--workspace", required=True)
    run_init.add_argument("--adapter-manifest", required=True)
    run_init.add_argument("--prompt-file")
    run_init.add_argument("--prompt-text")
    run_init.add_argument("--allowed-path", action="append", default=[])
    run_init.set_defaults(func=command_run_init)

    for name, handler in (
        ("authorize", command_run_authorize),
        ("begin-submit", command_run_begin_submit),
        ("finalize", command_run_finalize),
        ("status", command_run_status),
    ):
        cmd = run_sub.add_parser(name)
        cmd.add_argument("run_id")
        cmd.set_defaults(func=handler)

    run_preflight = run_sub.add_parser("preflight")
    run_preflight.add_argument("run_id")
    run_preflight.add_argument("--observation", required=True)
    run_preflight.set_defaults(func=command_run_preflight)

    run_confirm = run_sub.add_parser("confirm-submit")
    run_confirm.add_argument("run_id")
    run_confirm.add_argument("--unknown", action="store_true", help="record ambiguous acknowledgement")
    run_confirm.add_argument("--conversation-identity")
    run_confirm.set_defaults(func=command_run_confirm_submit)

    run_observe = run_sub.add_parser("observe")
    run_observe.add_argument("run_id")
    run_observe.add_argument("--observation", required=True)
    run_observe.set_defaults(func=command_run_observe)

    run_capture = run_sub.add_parser("capture")
    run_capture.add_argument("run_id")
    run_capture.add_argument("--raw-file", required=True)
    run_capture.add_argument("--terminal-signal", action="store_true")
    run_capture.set_defaults(func=command_run_capture)

    run_recover = run_sub.add_parser("recover")
    run_recover.add_argument("run_id")
    run_recover.add_argument("--observation", required=True)
    run_recover.set_defaults(func=command_run_recover)

    run_compress = run_sub.add_parser("compress")
    run_compress.add_argument("run_id")
    run_compress.set_defaults(func=command_run_compress)

    run_verify = run_sub.add_parser("verify")
    run_verify.add_argument("run_id")
    run_verify.set_defaults(func=command_run_verify)

    c2c = sub.add_parser("c2c", help="vendored Codex with ChatGPT bridge")
    c2c_sub = c2c.add_subparsers(dest="command", required=True)
    c2c_detect = c2c_sub.add_parser("detect", help="check the vendored bridge environment")
    c2c_detect.set_defaults(func=command_c2c_detect)
    c2c_build = c2c_sub.add_parser("build", help="install and build the vendored bridge")
    c2c_build.add_argument("--timeout", type=int, default=900)
    c2c_build.set_defaults(func=command_c2c_build)
    c2c_exec = c2c_sub.add_parser("exec", help="pass through to the vendored c2c CLI")
    c2c_exec.add_argument("args", nargs=argparse.REMAINDER)
    c2c_exec.set_defaults(func=command_c2c_exec)

    cycle = sub.add_parser("cycle", help="C2C control-plane state and execution records")
    cycle_sub = cycle.add_subparsers(dest="command", required=True)
    cycle_set = cycle_sub.add_parser("set")
    cycle_set.add_argument("run_id")
    cycle_set.add_argument("--state", required=True, choices=("INIT", "PLAN", "EXECUTING", "EXECUTED", "REVIEW", "DONE", "BLOCKED", "ERROR", "HANDOFF"))
    cycle_set.add_argument("--iteration", type=int, required=True)
    cycle_set.add_argument("--task-id")
    cycle_set.add_argument("--checkpoint")
    cycle_set.set_defaults(func=command_cycle_set)
    cycle_execution = cycle_sub.add_parser("record-execution")
    cycle_execution.add_argument("run_id")
    cycle_execution.add_argument("--iteration", type=int, required=True)
    cycle_execution.add_argument("--changed-file", action="append", default=[])
    cycle_execution.add_argument("--tests", required=True)
    cycle_execution.add_argument("--exit-status", required=True)
    cycle_execution.add_argument("--command")
    cycle_execution.add_argument("--output-file")
    cycle_execution.set_defaults(func=command_cycle_execution)
    cycle_handoff = cycle_sub.add_parser("handoff")
    cycle_handoff.add_argument("run_id")
    cycle_handoff.add_argument("--brief-file")
    cycle_handoff.add_argument("--brief-text")
    cycle_handoff.set_defaults(func=command_cycle_handoff)
    cycle_status = cycle_sub.add_parser("status")
    cycle_status.add_argument("run_id")
    cycle_status.set_defaults(func=command_cycle_status)

    data = sub.add_parser("data", help="read-only external data-plane contracts")
    data_sub = data.add_subparsers(dest="command", required=True)
    data_validate = data_sub.add_parser("validate")
    data_validate.add_argument("--manifest", required=True)
    data_validate.set_defaults(func=command_data_validate)

    return parser


def _exit_code(error: CCWError) -> int:
    if isinstance(error, WorkForbiddenError):
        return 3
    if isinstance(error, StateError):
        return 4
    if isinstance(error, ValidationError):
        return 2
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except CCWError as error:
        print(json.dumps({"error": str(error), "type": type(error).__name__}, ensure_ascii=False), file=sys.stderr)
        return _exit_code(error)
    except FileNotFoundError as error:
        print(json.dumps({"error": str(error), "type": "FileNotFoundError"}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
