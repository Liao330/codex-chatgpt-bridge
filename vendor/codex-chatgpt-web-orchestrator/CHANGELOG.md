# Changelog

All notable project changes will be recorded here.

## Unreleased

### Added

- Simplified Chinese default README with installation requirements, supported use cases, copy-ready invocation examples, execution flow, and CLI boundaries; the original English documentation is retained in `README_EN.md`.
- Three-layer orchestration architecture: governance, execution bridge, and result closure.
- Capability-based native and optional backend selection with fail-closed degradation.
- Side-effect-free planning and recovery CLI.
- Fixture tests for Chat Pro, Deep Research, and Work routing.
- Prompt fingerprinting, single-submit decisions, terminal state classification, and reconnect-first recovery.
- Model and mode evidence validation.
- Public-package sensitive information scanner.
- Exact live smoke prompts and evidence gates.
- Public project documentation, brand candidates, and deterministic dry-run demo.
- Dynamic preflight policy requiring a live bound identity, matching Chat/Work surface, interactive composer, and two consecutive stable observations before prompt fill and Send.
- Adapter-neutral delegation receipt protocol with public/private identity separation, JSON Schemas, canonical tamper detection, runtime-style fixtures, and deterministic fault injection.

### Status

- Public beta; the repository is public, while a tagged release remains gated on independent-user validation.
- Authorized live smoke results: Chat Pro passed; a separately authorized Deep Research rerun passed with a complete cited report; Work passed with a recovered and read-back Markdown artifact.
- Reattached the exact recorded Deep Research conversation without any new submission or message. Two final 30-second read-only windows found no active-generation control, assistant report, citations, status message, or explicit error; the run remains incomplete and the evidence snapshot is hashed.
- Registered reproducible defect `PREFLIGHT-SURFACE-001`: two internal Chat Pro attempts showed a visible Pro label while bridge/tab or Chat/Work state failed before prompt fill. Both remained `submission_count=0`; the new fixture and fail-closed tests prevent label-only readiness.
- Recorded a three-image Pro artifact chain with three ACCEPT decisions and source/hash archival. The image model was not visible and was not inferred.
- Updated the long-running Pro dogfood run to `complete`: one submission, the same recoverable identity, and an approximately 35,897-character report captured and verified. No prompt hash, conversation URL, or private path is published.
- Re-ran the public W3C-only Deep Research smoke after separate action-time authorization. One committed user turn produced an 11,226-character terminal report with 21 citation links; decision-critical WCAG claims were independently checked against current W3C pages.
- MIT License selected and added.
- Public GitHub repository created; no tagged Release or external CI workflow was created.
