#!/usr/bin/env python3
"""Run the public-safe package checks without third-party dependencies."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True

from delegation_receipt import validate_private_pair, validate_public_receipt
from orchestrator_policy import scan_public_tree


ROOT = Path(__file__).resolve().parents[1]


def check_static_contract() -> list[str]:
    errors: list[str] = []
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_en = (ROOT / "README_EN.md").read_text(encoding="utf-8")
    public_docs = readme + "\n" + readme_en
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    backends = (ROOT / "references" / "backends.md").read_text(encoding="utf-8")
    smoke = json.loads((ROOT / "smoke" / "prompts.json").read_text(encoding="utf-8"))
    dogfood = json.loads((ROOT / "dogfood" / "results.json").read_text(encoding="utf-8"))

    required_files = {
        ".gitignore",
        "CHANGELOG.md",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "LICENSE-CANDIDATES.md",
        "LICENSE",
        "README.md",
        "README_EN.md",
        "SECURITY.md",
        "THIRD_PARTY.md",
        "agents/openai.yaml",
        "assets/brand.svg",
        "assets/social-preview.svg",
        "demo/run_dry_demo.sh",
        "dogfood/results.json",
        "references/delegation-receipt.md",
        "references/architecture.md",
        "references/bridge-contract.md",
        "references/result-loop.md",
        "schemas/delegation-receipt.schema.json",
        "schemas/delegation-receipt-private.schema.json",
        "scripts/delegation_receipt.py",
        "tests/fixtures/faults/delegation-receipt-faults.json",
        "tests/fixtures/preflight/pro-label-visible-surface-unstable.json",
        "tests/fixtures/receipts/native-control.public.json",
        "tests/fixtures/receipts/native-control.private.synthetic.json",
        "tests/fixtures/receipts/oracle.public.json",
        "tests/fixtures/receipts/oracle.private.synthetic.json",
    }
    for relative_path in required_files:
        if not (ROOT / relative_path).is_file():
            errors.append(f"required product file missing: {relative_path}")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    if "/smoke/output/" not in gitignore:
        errors.append("private smoke output is not gitignored")
    if "/receipts/private/" not in gitignore:
        errors.append("private delegation receipt sidecars are not gitignored")

    required_backends = {
        "native",
        "codex-chatgpt-control",
        "oracle",
        "agentify-desktop",
        "manual",
    }
    for backend in required_backends:
        display = backend.replace("agentify-desktop", "Agentify Desktop")
        if display.lower() not in backends.lower():
            errors.append(f"support matrix omits {backend}")
    if "single submission" not in public_docs.lower() and "single-submit" not in public_docs.lower():
        errors.append("README omits single-submit behavior")
    if "PREFLIGHT-SURFACE-001" not in public_docs or "two consecutive" not in skill.lower():
        errors.append("candidate omits unstable-surface preflight regression contract")
    if "adapter-neutral delegation receipt" not in public_docs.lower():
        errors.append("README does not position the delegation receipt as the core")
    if "partial" not in public_docs.lower() or "incomplete" not in public_docs.lower():
        errors.append("README omits partial/incomplete boundary")
    if "exact prompt" not in skill.lower():
        errors.append("SKILL.md omits exact-prompt confirmation gate")
    if "name: codex-chatgpt-web-orchestrator" not in skill:
        errors.append("SKILL.md name does not match candidate repository")
    for phrase in ("free, unlimited", "no limits", "bypass quota", "quota-bypass"):
        if phrase in (public_docs + "\n" + skill).lower():
            errors.append(f"disallowed quota wording: {phrase}")
    for layer in ("Governance layer", "Execution bridge layer", "Result closure layer"):
        if layer not in public_docs:
            errors.append(f"README architecture omits {layer}")
    runs = smoke.get("runs", [])
    all_live_smokes_passed = len(runs) == 3 and all(
        run.get("result", {}).get("status") == "passed" for run in runs
    )
    if smoke.get("overall_status") == "all-live-smokes-passed" and not all_live_smokes_passed:
        errors.append("all-live-smokes-passed requires every live smoke to pass")
    if all_live_smokes_passed:
        if "Public beta" not in public_docs and "Internal beta" not in public_docs:
            errors.append("passing live smokes still require an explicit beta status")
    elif "Internal beta" not in public_docs:
        errors.append("non-passing live smoke requires Internal beta status")
    if {run.get("mode") for run in runs} != {"chat-pro", "deep-research", "work"}:
        errors.append("smoke manifest must contain exactly the three target modes")
    if len(runs) != 3:
        errors.append("smoke manifest must contain exactly three runs")
    for run in runs:
        for key in ("prompt", "expected_evidence", "failure_criteria"):
            if not run.get(key):
                errors.append(f"smoke run {run.get('id', '<missing>')} omits {key}")
        if smoke.get("status") == "executed" and not run.get("result"):
            errors.append(f"executed smoke run {run.get('id', '<missing>')} omits result")
        result = run.get("result", {})
        for path_key, hash_key in (
            ("normalized_output", "normalized_output_sha256"),
            ("artifact", "artifact_sha256"),
        ):
            if path_key not in result:
                continue
            output_path = ROOT / "smoke" / result[path_key]
            if not output_path.is_file():
                errors.append(f"smoke output missing: {result[path_key]}")
                continue
            digest = hashlib.sha256(output_path.read_bytes()).hexdigest()
            if digest != result.get(hash_key):
                errors.append(f"smoke output hash mismatch: {result[path_key]}")
    dogfood_by_id = {run.get("id"): run for run in dogfood.get("runs", [])}
    image_run = dogfood_by_id.get("pro-image-artifact-chain", {})
    long_run = dogfood_by_id.get("pro-long-running-after-preflight-fix", {})
    if dogfood.get("candidate_status") != "internal-beta" or dogfood.get("release_impact") != "none":
        errors.append("dogfood evidence must not change the Internal beta release gate")
    if image_run.get("status") != "passed" or image_run.get("underlying_image_model") != "not-visible-not-inferred":
        errors.append("image dogfood evidence is missing success or no-model-inference boundary")
    if image_run.get("acceptance_results") != {"accepted": 3, "rejected": 0}:
        errors.append("image dogfood acceptance count is inconsistent")
    if (
        long_run.get("status") != "complete"
        or long_run.get("terminal_output_captured") is not True
        or long_run.get("terminal_output_verified") is not True
        or long_run.get("same_run_identity_recovered") is not True
        or long_run.get("output_characters_approx") != 35897
    ):
        errors.append("long-running dogfood terminal evidence is inconsistent")
    if long_run.get("submission_count") != 1 or any(
        long_run.get(key) is not False for key in ("cancelled", "follow_up_sent", "retried")
    ):
        errors.append("long-running dogfood single-submit boundary is inconsistent")
    if any(run.get("release_evidence") is not False for run in dogfood.get("runs", [])):
        errors.append("internal dogfood entries must not be marked as release evidence")
    for name in ("native-control", "oracle"):
        public = json.loads(
            (ROOT / "tests" / "fixtures" / "receipts" / f"{name}.public.json").read_text(
                encoding="utf-8"
            )
        )
        private = json.loads(
            (
                ROOT
                / "tests"
                / "fixtures"
                / "receipts"
                / f"{name}.private.synthetic.json"
            ).read_text(encoding="utf-8")
        )
        errors.extend(f"{name} receipt: {issue}" for issue in validate_public_receipt(public))
        errors.extend(f"{name} sidecar: {issue}" for issue in validate_private_pair(public, private))
    faults = json.loads(
        (ROOT / "tests" / "fixtures" / "faults" / "delegation-receipt-faults.json").read_text(
            encoding="utf-8"
        )
    )
    if len(faults.get("scenarios", [])) < 30:
        errors.append("delegation receipt requires at least 30 fault injections")
    return errors


def main() -> int:
    errors = check_static_contract()
    findings = scan_public_tree(ROOT)
    errors.extend(
        f"sensitive scan: {finding.path}:{finding.line} {finding.kind}"
        for finding in findings
    )

    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
    if errors or not result.wasSuccessful():
        return 1
    print("candidate checks: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
