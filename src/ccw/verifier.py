from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _inside_workspace(workspace: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(workspace.resolve())
        return True
    except ValueError:
        return False


def verify_compressed(value: dict[str, Any], *, workspace: str | Path, raw_sha256: str | None = None) -> dict[str, Any]:
    workspace_path = Path(workspace).resolve()
    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    warnings: list[str] = []

    if raw_sha256 and value.get("raw_sha256") != raw_sha256:
        failures.append("raw-sha256-mismatch")
        checks.append({"id": "raw-integrity", "status": "fail", "evidence_ref": "response.raw.md"})
    else:
        checks.append({"id": "raw-integrity", "status": "pass", "evidence_ref": "response.raw.md"})

    if value.get("mode") == "chat-pro":
        for index, finding in enumerate(value.get("findings", []), start=1):
            check_id = f"finding-{index}"
            file_value = finding.get("file")
            line_value = finding.get("line")
            if not file_value:
                warnings.append(f"{check_id}: no file reference")
                checks.append({"id": check_id, "status": "pending", "evidence_ref": "compressed.json"})
                continue
            candidate = workspace_path / str(file_value)
            if not _inside_workspace(workspace_path, candidate) or not candidate.exists():
                failures.append(f"{check_id}: file missing or outside workspace: {file_value}")
                checks.append({"id": check_id, "status": "fail", "evidence_ref": str(file_value)})
                continue
            if line_value is not None:
                try:
                    line_number = int(line_value)
                    line_count = len(candidate.read_text(encoding="utf-8", errors="replace").splitlines())
                    if line_number < 1 or line_number > line_count:
                        failures.append(f"{check_id}: line {line_number} outside {file_value}")
                        checks.append({"id": check_id, "status": "fail", "evidence_ref": str(file_value)})
                        continue
                except (TypeError, ValueError):
                    failures.append(f"{check_id}: invalid line value")
                    checks.append({"id": check_id, "status": "fail", "evidence_ref": str(file_value)})
                    continue
            checks.append({"id": check_id, "status": "pass", "evidence_ref": str(file_value)})
    elif value.get("mode") == "deep-research":
        citations = value.get("citations", [])
        if not citations:
            warnings.append("deep-research has no citations")
            checks.append({"id": "citations-present", "status": "pending", "evidence_ref": "compressed.json"})
        for index, citation in enumerate(citations, start=1):
            parsed = urlparse(str(citation))
            status = "pass" if parsed.scheme == "https" and parsed.netloc else "fail"
            if status == "fail":
                failures.append(f"citation-{index}: invalid URL")
            checks.append({"id": f"citation-{index}", "status": status, "evidence_ref": str(citation)})
        checks.append({
            "id": "claim-verification",
            "status": "pending",
            "evidence_ref": "Codex must verify decision-critical claims against primary sources",
        })
        warnings.append("decision-critical research claims remain pending Codex verification")
    else:
        failures.append("work-mode-forbidden")
        checks.append({"id": "work-mode", "status": "fail", "evidence_ref": "policy"})

    return {
        "schema_version": "1.0.0",
        "passed": not failures,
        "checks": checks,
        "failures": failures,
        "warnings": warnings,
        "verified_by": "local-structural-verifier",
        "semantic_verification_required": True,
    }
