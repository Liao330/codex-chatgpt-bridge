from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ALLOWED_MODES = ("chat-pro", "deep-research")
FORBIDDEN_MODE = "work"
ALLOWED_TASK_KINDS = (
    "consultation",
    "critique",
    "review",
    "architecture-review",
    "synthesis",
    "debug",
    "source-research",
    "research-report",
)
RUN_STATES = (
    "draft",
    "authorized",
    "prepared",
    "committing",
    "committed",
    "generating",
    "partial",
    "complete",
    "incomplete",
    "blocked",
    "unknown",
)
TERMINAL_STATES = {"complete", "partial", "incomplete", "blocked", "unknown"}
OUTCOME_STATES = ("generating", "complete", "partial", "incomplete", "blocked", "unknown")


@dataclass
class RunRecord:
    schema_version: str
    run_id: str
    mode: str
    task_kind: str
    workspace: str
    status: str
    prompt: dict[str, Any]
    authorization: dict[str, Any]
    adapter: dict[str, Any]
    submission: dict[str, Any]
    route_evidence: dict[str, Any]
    outcome: dict[str, Any]
    acceptance: dict[str, Any]
    continuation: dict[str, Any]
    compression: dict[str, Any]
    verification: dict[str, Any]
    events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RunRecord":
        return cls(**value)
