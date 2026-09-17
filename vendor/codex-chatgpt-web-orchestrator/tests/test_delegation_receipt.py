from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from delegation_receipt import (  # noqa: E402
    seal_receipt,
    should_submit,
    validate_private_pair,
    validate_public_receipt,
)


RECEIPTS = ROOT / "tests" / "fixtures" / "receipts"
FAULTS = ROOT / "tests" / "fixtures" / "faults" / "delegation-receipt-faults.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_value(scenario):
    if "value" in scenario:
        return scenario["value"]
    token = scenario["value_token"]
    if token == "zero_hash":
        return "0" * 64
    if token == "credential":
        return "api_" + "key=" + "A" * 20
    if token == "private_path":
        return "/" + "Users/example/private/artifact.md"
    if token == "conversation_url":
        return "https://chatgpt.com/" + "c/" + "synthetic-session"
    raise AssertionError(f"unknown value token: {token}")


def mutate(receipt, scenario):
    changed = deepcopy(receipt)
    target = changed
    for component in scenario["path"][:-1]:
        target = target[component]
    target[scenario["path"][-1]] = resolve_value(scenario)
    return changed


class ReceiptFixtureTests(unittest.TestCase):
    def test_schemas_cover_required_public_and_private_boundaries(self):
        public_schema = load_json(ROOT / "schemas" / "delegation-receipt.schema.json")
        private_schema = load_json(
            ROOT / "schemas" / "delegation-receipt-private.schema.json"
        )
        self.assertEqual(public_schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(public_schema["additionalProperties"])
        self.assertEqual(
            set(public_schema["required"]),
            {
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
            },
        )
        self.assertTrue(
            {"adapter_identity", "run_identity", "continuation_identity"}
            <= set(private_schema["required"])
        )
        self.assertTrue(
            {"adapter_identity", "run_identity", "continuation_identity"}.isdisjoint(
                public_schema["properties"]
            )
        )

    def test_native_control_and_oracle_style_fixtures_validate(self):
        for name, expected_family in (
            ("native-control", "native-control-style"),
            ("oracle", "oracle-style"),
        ):
            with self.subTest(name=name):
                public = load_json(RECEIPTS / f"{name}.public.json")
                private = load_json(RECEIPTS / f"{name}.private.synthetic.json")
                self.assertEqual(public["adapter"]["family"], expected_family)
                self.assertEqual(public["adapter"]["runtime_claim"], "style-mapping-only")
                self.assertEqual(validate_public_receipt(public), [])
                self.assertEqual(validate_private_pair(public, private), [])
                self.assertFalse(should_submit(public, public["prompt"]["sha256"]))

    def test_private_identity_tampering_breaks_pair_commitments(self):
        public = load_json(RECEIPTS / "native-control.public.json")
        private = load_json(RECEIPTS / "native-control.private.synthetic.json")
        for key in ("adapter_identity", "run_identity", "continuation_identity"):
            with self.subTest(key=key):
                changed = deepcopy(private)
                changed[key] += "-changed"
                self.assertTrue(
                    any(
                        issue.startswith("private-commitment-mismatch")
                        for issue in validate_private_pair(public, changed)
                    )
                )

    def test_seal_is_deterministic(self):
        receipt = load_json(RECEIPTS / "native-control.public.json")
        self.assertEqual(seal_receipt(receipt), receipt)

    def test_public_receipt_object_key_order_is_irrelevant(self):
        receipt = load_json(RECEIPTS / "native-control.public.json")
        reordered = dict(reversed(tuple(receipt.items())))
        self.assertEqual(validate_public_receipt(reordered), [])


class ReceiptFaultInjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_json(FAULTS)
        cls.base = load_json(ROOT / cls.catalog["base_receipt"])

    def test_at_least_thirty_structural_faults_are_declared(self):
        self.assertGreaterEqual(len(self.catalog["scenarios"]), 30)
        self.assertEqual(
            len({scenario["id"] for scenario in self.catalog["scenarios"]}),
            len(self.catalog["scenarios"]),
        )

    def test_every_mutated_public_field_is_detected_and_never_submitted(self):
        submit_decisions = 0
        for scenario in self.catalog["scenarios"]:
            with self.subTest(scenario=scenario["id"]):
                changed = mutate(self.base, scenario)
                issues = validate_public_receipt(changed)
                self.assertTrue(issues)
                self.assertIn("integrity-mismatch", issues)
                submit_decisions += int(
                    should_submit(changed, self.base["prompt"]["sha256"])
                )
        self.assertEqual(submit_decisions, self.catalog["expected_submit_decisions"])

    def test_public_privacy_injections_are_rejected_explicitly(self):
        expected = {
            "credential-injection": "sensitive-public-field:credential:",
            "private-path-injection": "sensitive-public-field:private-path:",
            "conversation-url-injection": "sensitive-public-field:conversation-url:",
            "raw-run-identity": "raw-private-field:",
        }
        scenarios = {scenario["id"]: scenario for scenario in self.catalog["scenarios"]}
        for scenario_id, issue_prefix in expected.items():
            with self.subTest(scenario=scenario_id):
                issues = validate_public_receipt(mutate(self.base, scenarios[scenario_id]))
                self.assertTrue(any(issue.startswith(issue_prefix) for issue in issues))

    def test_duplicate_submission_variants_produce_zero_send_decisions(self):
        prompt_hash = self.base["prompt"]["sha256"]
        variants = []
        for state, count, acknowledged in (
            ("committing", 1, False),
            ("committed", 1, True),
            ("committed", 1, False),
            ("not-sent", 1, False),
            ("committed", 2, True),
        ):
            variant = deepcopy(self.base)
            variant["submission"].update(
                state=state, count=count, acknowledgement_observed=acknowledged
            )
            variants.append(seal_receipt(variant))
        self.assertEqual(
            sum(int(should_submit(variant, prompt_hash)) for variant in variants), 0
        )


if __name__ == "__main__":
    unittest.main()
