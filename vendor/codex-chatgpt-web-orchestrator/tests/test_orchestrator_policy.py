from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from orchestrator_policy import (  # noqa: E402
    Completion,
    Mode,
    PreflightObservation,
    RouteRequest,
    RunObservation,
    choose_mode,
    classify_completion,
    conversation_action,
    detect_backend_presence,
    idempotency_decision,
    prompt_fingerprint,
    preflight_decision,
    recovery_decision,
    route_evidence_issues,
    scan_public_tree,
    select_backend,
    submission_decision,
)


FULL = {"send", "observe", "capture", "stable_identity"}


class RoutingTests(unittest.TestCase):
    def test_routing_matrix(self):
        matrix = {
            "consultation": Mode.CHAT_PRO,
            "critique": Mode.CHAT_PRO,
            "source-research": Mode.DEEP_RESEARCH,
            "research-report": Mode.DEEP_RESEARCH,
            "artifact": Mode.WORK,
            "browser-action": Mode.WORK,
        }
        for task_kind, expected in matrix.items():
            with self.subTest(task_kind=task_kind):
                self.assertEqual(choose_mode(RouteRequest(task_kind)), expected)

    def test_explicit_mode_is_preserved(self):
        request = RouteRequest("artifact", requested_mode=Mode.CHAT_PRO)
        self.assertEqual(choose_mode(request), Mode.CHAT_PRO)

    def test_routing_fixtures(self):
        fixture_dir = ROOT / "tests" / "fixtures" / "requests"
        expected = {
            "chat-pro.json": Mode.CHAT_PRO,
            "deep-research.json": Mode.DEEP_RESEARCH,
            "work.json": Mode.WORK,
        }
        for filename, mode in expected.items():
            data = json.loads((fixture_dir / filename).read_text())
            request = RouteRequest(
                data["task_kind"],
                requested_mode=Mode(data["requested_mode"]),
                referenced_conversation=data["referenced_conversation"],
            )
            self.assertEqual(choose_mode(request), mode)

    def test_conversation_reuse_policy(self):
        self.assertEqual(
            conversation_action(referenced_conversation=True, continuity_required=False),
            "reuse",
        )
        self.assertEqual(
            conversation_action(referenced_conversation=False, continuity_required=False),
            "new",
        )


class BackendTests(unittest.TestCase):
    def test_read_only_inventory_detection(self):
        present = detect_backend_presence(
            exposed_tools={
                "browser:control-in-app-browser",
                "mcp__codex_app__read_thread",
                "mcp__codex_app__send_message_to_thread",
                "mcp__agentify__send_prompt",
            },
            exposed_skills={"codex-chatgpt-control"},
            executables={"/opt/local/bin/oracle"},
        )
        self.assertEqual(
            present,
            {
                "native",
                "codex-chatgpt-control",
                "oracle",
                "agentify-desktop",
                "manual",
            },
        )

    def test_partial_native_inventory_is_not_declared_present(self):
        present = detect_backend_presence(
            exposed_tools={"browser:control-in-app-browser"}
        )
        self.assertEqual(present, {"manual"})

    def test_native_preferred_when_capable(self):
        available = {
            "native": FULL | {"deep_research"},
            "oracle": FULL | {"deep_research"},
        }
        self.assertEqual(select_backend(Mode.DEEP_RESEARCH, available), "native")

    def test_degrades_without_installing(self):
        available = {
            "native": {"capture", "stable_identity"},
            "oracle": FULL | {"deep_research"},
            "manual": FULL | {"deep_research"},
        }
        self.assertEqual(select_backend(Mode.DEEP_RESEARCH, available), "oracle")

    def test_requested_backend_fails_closed_when_incapable(self):
        available = {
            "native": FULL | {"work"},
            "manual": FULL | {"work"},
        }
        self.assertIsNone(
            select_backend(Mode.WORK, available, requested_backend="oracle")
        )

    def test_no_complete_backend_returns_none(self):
        self.assertIsNone(select_backend(Mode.CHAT_PRO, {"native": {"send"}}))


class LifecycleTests(unittest.TestCase):
    def test_visible_pro_label_does_not_override_unstable_surface(self):
        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "preflight" / "pro-label-visible-surface-unstable.json").read_text()
        )
        for attempt in fixture["attempts"]:
            expected = attempt.pop("expected_action")
            with self.subTest(attempt=attempt["attempt"]):
                attempt.pop("attempt")
                self.assertEqual(
                    preflight_decision(PreflightObservation(**attempt)), expected
                )

    def test_preflight_requires_two_stable_reads_before_prompt_fill_and_send(self):
        base = dict(
            bridge_connected=True,
            tab_bound=True,
            identity_stable=True,
            identity_reopenable=True,
            expected_surface="chat",
            observed_surface="chat",
            mode_verified=True,
            model_verified=True,
            composer_interactive=True,
            submission_count=0,
        )
        self.assertEqual(
            preflight_decision(PreflightObservation(**base, stable_read_count=1)),
            "stabilize_surface_no_send",
        )
        self.assertEqual(
            preflight_decision(PreflightObservation(**base, stable_read_count=2)),
            "ready_to_fill_prompt",
        )
        self.assertEqual(
            preflight_decision(
                PreflightObservation(**base, stable_read_count=2, prompt_filled=True)
            ),
            "ready_to_submit_once",
        )

    def test_unstable_post_fill_surface_holds_without_send(self):
        observation = PreflightObservation(
            bridge_connected=True,
            tab_bound=True,
            identity_stable=True,
            identity_reopenable=True,
            expected_surface="chat",
            observed_surface="work",
            mode_verified=False,
            model_verified=True,
            composer_interactive=False,
            stable_read_count=0,
            prompt_filled=True,
        )
        self.assertEqual(
            preflight_decision(observation),
            "hold_draft_surface_unstable_no_send",
        )

    def test_single_submit_for_committed_and_uncertain_runs(self):
        self.assertEqual(submission_decision("committed"), "do_not_send")
        self.assertEqual(submission_decision("unknown", True), "do_not_send")
        self.assertEqual(
            submission_decision("unknown", None), "reconnect_and_inspect"
        )

    def test_prompt_fingerprint_enforces_idempotency(self):
        prompt = "Review the public migration plan."
        self.assertEqual(
            idempotency_decision(
                submission_state="not-sent",
                proposed_prompt=prompt,
                recorded_fingerprint=prompt_fingerprint(prompt),
            ),
            "do_not_send_duplicate",
        )

    def test_uncommitted_run_only_proposes_confirmed_new_send(self):
        self.assertEqual(
            submission_decision("unknown", False),
            "propose_new_send_after_confirmation",
        )

    def test_partial_and_incomplete_never_become_complete(self):
        partial = RunObservation(False, True, False, partial_output_accessible=True)
        incomplete = RunObservation(False, True, False)
        self.assertEqual(classify_completion(partial), Completion.PARTIAL)
        self.assertEqual(classify_completion(incomplete), Completion.INCOMPLETE)

    def test_active_generation_is_generating(self):
        observation = RunObservation(True, False, False, partial_output_accessible=True)
        self.assertEqual(classify_completion(observation), Completion.GENERATING)

    def test_complete_requires_artifact_when_expected(self):
        missing = RunObservation(False, True, True, artifact_expected=True)
        present = RunObservation(
            False, True, True, artifact_expected=True, artifact_accessible=True
        )
        self.assertEqual(classify_completion(missing), Completion.INCOMPLETE)
        self.assertEqual(classify_completion(present), Completion.COMPLETE)

    def test_disconnect_recovery_reuses_identity(self):
        self.assertEqual(
            recovery_decision(
                identity_reopenable=True,
                original_turn_present=True,
                generation_active=True,
            ),
            "wait_same_run",
        )
        self.assertEqual(
            recovery_decision(
                identity_reopenable=True,
                original_turn_present=True,
                generation_active=False,
                final_output_accessible=True,
            ),
            "capture_same_run",
        )

    def test_lost_identity_never_silently_resubmits(self):
        self.assertEqual(
            recovery_decision(identity_reopenable=False), "mark_unknown_no_resend"
        )


class SensitiveScanTests(unittest.TestCase):
    def test_clean_public_text_passes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text("Public example with no secrets.\n")
            self.assertEqual(scan_public_tree(root), [])

    def test_personal_path_and_secret_are_detected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            personal_path = "/" + "Users/example/private/file"
            assigned_secret = "api_" + "key='" + "abcdefghijklmnop'"
            (root / "bad.txt").write_text(
                personal_path + "\n" + assigned_secret + "\n"
            )
            kinds = {finding.kind for finding in scan_public_tree(root)}
            self.assertIn("personal-absolute-path", kinds)
            self.assertIn("assigned-secret", kinds)

    def test_private_runtime_output_is_excluded_from_public_scan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            private_dir = root / "smoke" / "output"
            private_dir.mkdir(parents=True)
            (private_dir / "run.json").write_text(
                "/" + "Users/example/private/file\n"
            )
            self.assertEqual(scan_public_tree(root), [])


class EvidenceAndCliTests(unittest.TestCase):
    def test_dogfood_artifact_and_long_run_terminal_evidence_stay_distinct(self):
        ledger = json.loads((ROOT / "dogfood" / "results.json").read_text())
        runs = {run["id"]: run for run in ledger["runs"]}
        image_run = runs["pro-image-artifact-chain"]
        long_run = runs["pro-long-running-after-preflight-fix"]
        self.assertEqual(image_run["status"], "passed")
        self.assertEqual(image_run["underlying_image_model"], "not-visible-not-inferred")
        self.assertEqual(image_run["acceptance_results"]["accepted"], 3)
        self.assertEqual(long_run["status"], "complete")
        self.assertEqual(long_run["submission_count"], 1)
        self.assertTrue(long_run["same_run_identity_recovered"])
        self.assertTrue(long_run["terminal_output_captured"])
        self.assertTrue(long_run["terminal_output_verified"])
        self.assertEqual(long_run["output_characters_approx"], 35897)
        self.assertFalse(image_run["release_evidence"])
        self.assertFalse(long_run["release_evidence"])

    def test_model_and_mode_evidence_must_match_exactly(self):
        self.assertEqual(
            route_evidence_issues(
                expected_mode=Mode.CHAT_PRO,
                expected_model="Pro",
                observed_mode="chat-pro",
                observed_model="Pro",
                mode_verified=True,
                model_verified=True,
            ),
            [],
        )
        self.assertEqual(
            route_evidence_issues(
                expected_mode=Mode.WORK,
                expected_model="Pro",
                observed_mode="chat-pro",
                observed_model="Thinking",
                mode_verified=True,
                model_verified=True,
            ),
            ["mode-not-verified", "model-not-verified"],
        )

    def test_readme_quick_start_command_is_executable(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "orchestrator_cli.py"),
                "plan",
                "--request",
                str(ROOT / "tests" / "fixtures" / "requests" / "work.json"),
                "--capabilities",
                str(ROOT / "tests" / "fixtures" / "capabilities" / "native-all.json"),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        output = json.loads(result.stdout)
        self.assertEqual(output["backend"], "native")
        self.assertEqual(output["mode"], "work")
        self.assertFalse(output["transmission_authorized"])

    def test_no_backend_cli_fails_closed(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "orchestrator_cli.py"),
                "plan",
                "--request",
                str(ROOT / "tests" / "fixtures" / "requests" / "work.json"),
                "--capabilities",
                str(ROOT / "tests" / "fixtures" / "capabilities" / "none.json"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["next_action"], "fail-closed-no-capable-backend")

    def test_readme_recovery_command_is_executable(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "orchestrator_cli.py"),
                "recover",
                "--state",
                str(ROOT / "tests" / "fixtures" / "recovery" / "disconnected-generating.json"),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(result.stdout)["action"], "wait_same_run")

    def test_known_unstable_surface_fixture_fails_closed_in_cli(self):
        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "preflight" / "pro-label-visible-surface-unstable.json").read_text()
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "attempt.json"
            attempt = dict(fixture["attempts"][0])
            attempt.pop("attempt")
            attempt.pop("expected_action")
            state_path.write_text(json.dumps(attempt))
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "orchestrator_cli.py"),
                    "preflight",
                    "--state",
                    str(state_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        output = json.loads(result.stdout)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(output["action"], "reacquire_bridge_no_send")
        self.assertFalse(output["ready"])
        self.assertFalse(output["send"])

    def test_dry_demo_is_executable_and_truthfully_labeled(self):
        result = subprocess.run(
            ["bash", str(ROOT / "demo" / "run_dry_demo.sh")],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("DRY RUN ONLY", result.stdout)
        self.assertEqual(result.stdout.count('"transmission_authorized": false'), 3)


if __name__ == "__main__":
    unittest.main()
