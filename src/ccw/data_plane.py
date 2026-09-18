from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re

from .errors import ValidationError


FORBIDDEN_TOOL_RE = re.compile(r"(?i)(?:^|[_-])(write|delete|remove|exec|shell|bash|commit|push|update|insert|drop|alter)(?:$|[_-])")
ALLOWED_KINDS = {"sqlite", "json_file", "http_readonly"}


def validate_data_source(value: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if value.get("read_only") is not True:
        issues.append("read_only-must-be-true")
    if value.get("kind") not in ALLOWED_KINDS:
        issues.append("unsupported-kind")
    if not value.get("id"):
        issues.append("missing-id")
    tools = value.get("tools", [])
    if not isinstance(tools, list) or not tools:
        issues.append("tools-must-be-non-empty-list")
    else:
        for tool in tools:
            name = str(tool.get("name") if isinstance(tool, dict) else tool)
            if FORBIDDEN_TOOL_RE.search(name):
                issues.append(f"forbidden-write-tool:{name}")
    auth = value.get("auth", {})
    if not isinstance(auth, dict) or auth.get("type") not in {"oauth2", "local_only"}:
        issues.append("auth-must-be-oauth2-or-local-only")
    limits = value.get("limits", {})
    if not isinstance(limits, dict):
        issues.append("limits-must-be-object")
    else:
        for field in ("max_rows", "timeout_ms", "max_bytes"):
            if not isinstance(limits.get(field), int) or limits[field] <= 0:
                issues.append(f"invalid-limit:{field}")
    if value.get("kind") == "http_readonly":
        url = str(value.get("url", ""))
        if auth.get("type") != "oauth2":
            issues.append("http-readonly-requires-oauth2")
        if not url.startswith("https://"):
            issues.append("http-readonly-requires-https")
    return sorted(set(issues))


def load_and_validate(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    issues = validate_data_source(value)
    if issues:
        raise ValidationError("data source validation failed: " + ", ".join(issues))
    return value

