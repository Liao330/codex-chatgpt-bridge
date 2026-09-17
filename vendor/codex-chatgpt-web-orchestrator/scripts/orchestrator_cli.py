#!/usr/bin/env python3
"""Side-effect-free planner for the Codex ChatGPT web orchestrator.

This CLI never opens a browser or submits a prompt. It makes routing and
recovery decisions inspectable before an agent uses an authorized bridge.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

from orchestrator_policy import (
    Mode,
    PreflightObservation,
    RouteRequest,
    choose_mode,
    conversation_action,
    preflight_decision,
    recovery_decision,
    select_backend,
)


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def plan(args: argparse.Namespace) -> int:
    request_data = load_json(args.request)
    capabilities = load_json(args.capabilities)["backends"]
    requested_mode = request_data.get("requested_mode")
    request = RouteRequest(
        task_kind=request_data["task_kind"],
        requested_mode=Mode(requested_mode) if requested_mode else None,
        referenced_conversation=request_data.get("referenced_conversation", False),
    )
    mode = choose_mode(request)
    backend = select_backend(
        mode,
        capabilities,
        requested_backend=request_data.get("requested_backend"),
    )
    output = {
        "backend": backend,
        "conversation": conversation_action(
            referenced_conversation=request.referenced_conversation,
            continuity_required=request_data.get("continuity_required", False),
        ),
        "mode": mode.value,
        "next_action": (
            "prepare-exact-prompt-and-request-confirmation"
            if backend
            else "fail-closed-no-capable-backend"
        ),
        "transmission_authorized": False,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if backend else 2


def recover(args: argparse.Namespace) -> int:
    state = load_json(args.state)
    action = recovery_decision(**state)
    print(json.dumps({"action": action, "resubmit": False}, sort_keys=True))
    return 0


def preflight(args: argparse.Namespace) -> int:
    state = load_json(args.state)
    observation = PreflightObservation(**state)
    action = preflight_decision(observation)
    ready = action in {"ready_to_fill_prompt", "ready_to_submit_once"}
    print(json.dumps({"action": action, "ready": ready, "send": False}, sort_keys=True))
    return 0 if ready else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan", help="plan a route without sending")
    plan_parser.add_argument("--request", required=True)
    plan_parser.add_argument("--capabilities", required=True)
    plan_parser.set_defaults(func=plan)
    recover_parser = subparsers.add_parser("recover", help="evaluate reconnect state")
    recover_parser.add_argument("--state", required=True)
    recover_parser.set_defaults(func=recover)
    preflight_parser = subparsers.add_parser(
        "preflight", help="evaluate a read-only bridge and surface snapshot"
    )
    preflight_parser.add_argument("--state", required=True)
    preflight_parser.set_defaults(func=preflight)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
