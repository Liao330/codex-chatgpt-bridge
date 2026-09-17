from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import json
import re

from .fingerprint import sha256_file


URL_RE = re.compile(r"https://[^\s)\]}>\"']+")
SEVERITY_RE = re.compile(r"\b(critical|high|medium|low|blocker|major|minor)\b", re.IGNORECASE)
FILE_LINE_RE = re.compile(r"(?P<file>[\w./\\-]+\.[A-Za-z0-9_+-]+):(?P<line>\d+)")
UNCERTAIN_RE = re.compile(
    r"(?i)\b(uncertain|unknown|assum(?:e|ption)|unverified|possible|may|might|待验证|不确定|假设)\b"
)
SKIP_PREFIXES = ("here is", "certainly", "sure,", "i hope", "let me know")


def _clean_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.lower().startswith(SKIP_PREFIXES):
            continue
        lines.append(line)
    return lines


def _extract_json_object(text: str) -> dict[str, Any] | None:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s*```$", "", candidate)
    try:
        value = json.loads(candidate)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start >= 0 and end > start:
        try:
            value = json.loads(candidate[start : end + 1])
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _normalize_finding(value: Any, index: int) -> dict[str, Any]:
    if isinstance(value, str):
        match = FILE_LINE_RE.search(value)
        severity = SEVERITY_RE.search(value)
        return {
            "id": f"finding-{index}",
            "severity": severity.group(1).lower() if severity else "unknown",
            "file": match.group("file") if match else None,
            "line": int(match.group("line")) if match else None,
            "claim": value,
            "evidence": value,
            "recommendation": "Verify locally before applying.",
        }
    if not isinstance(value, dict):
        return {
            "id": f"finding-{index}",
            "severity": "unknown",
            "file": None,
            "line": None,
            "claim": str(value),
            "evidence": str(value),
            "recommendation": "Verify locally before applying.",
        }
    return {
        "id": str(value.get("id") or f"finding-{index}"),
        "severity": str(value.get("severity") or "unknown").lower(),
        "file": value.get("file"),
        "line": value.get("line"),
        "claim": str(value.get("claim") or value.get("title") or value.get("finding") or ""),
        "evidence": str(value.get("evidence") or value.get("rationale") or ""),
        "recommendation": str(value.get("recommendation") or value.get("fix") or ""),
        "verified": False,
    }


def _heuristic_compress(text: str, mode: str) -> dict[str, Any]:
    lines = _clean_lines(text)
    citations = list(dict.fromkeys(URL_RE.findall(text)))
    uncertain = [line for line in lines if UNCERTAIN_RE.search(line)][:12]
    findings: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        if SEVERITY_RE.search(line) or FILE_LINE_RE.search(line):
            if line.startswith(("-", "*", "1.", "2.", "3.", "4.", "5.")) or len(line) < 320:
                findings.append(_normalize_finding(line, len(findings) + 1))
    summary_candidates = [
        line.lstrip("-*0123456789. ") for line in lines if not line.startswith("```")
    ]
    summary = summary_candidates[:10]
    return {
        "schema_version": "1.0.0",
        "mode": mode,
        "parse_mode": "heuristic",
        "summary": summary,
        "findings": findings[:30],
        "key_points": summary[:12] if mode == "deep-research" else [],
        "citations": citations,
        "uncertainties": uncertain,
        "raw_ref": None,
        "raw_sha256": None,
        "compression_policy": {
            "canonical_source": "raw response",
            "evidence_preserved": bool(findings or citations),
            "verified": False,
        },
    }


def compress_response(text: str, *, mode: str, raw_path: str | Path | None = None) -> dict[str, Any]:
    parsed = _extract_json_object(text)
    if parsed is None:
        result = _heuristic_compress(text, mode)
    else:
        summary = parsed.get("summary") or parsed.get("key_points") or []
        if isinstance(summary, str):
            summary = [summary]
        raw_findings = parsed.get("findings") or []
        if isinstance(raw_findings, str):
            raw_findings = [raw_findings]
        result = {
            "schema_version": "1.0.0",
            "mode": mode,
            "parse_mode": "json",
            "summary": list(summary) if isinstance(summary, list) else [],
            "findings": [_normalize_finding(item, i + 1) for i, item in enumerate(raw_findings)],
            "key_points": list(parsed.get("key_points") or []) if mode == "deep-research" else [],
            "citations": list(dict.fromkeys(parsed.get("citations") or URL_RE.findall(text))),
            "uncertainties": list(parsed.get("uncertainties") or []),
            "tests": list(parsed.get("tests") or []),
            "verdict": parsed.get("verdict"),
            "raw_ref": None,
            "raw_sha256": None,
            "compression_policy": {
                "canonical_source": "raw response",
                "evidence_preserved": True,
                "verified": False,
            },
        }
    if raw_path is not None:
        path = Path(raw_path)
        result["raw_ref"] = path.name
        result["raw_sha256"] = sha256_file(path)
    return result


def validate_compressed(value: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if value.get("mode") not in {"chat-pro", "deep-research"}:
        issues.append("invalid-mode")
    if not isinstance(value.get("summary"), list):
        issues.append("summary-not-list")
    if not isinstance(value.get("findings"), list):
        issues.append("findings-not-list")
    for citation in value.get("citations", []):
        parsed = urlparse(str(citation))
        if parsed.scheme != "https" or not parsed.netloc:
            issues.append(f"invalid-citation:{citation}")
    return issues
