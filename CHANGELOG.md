# Changelog

## 0.2.0

- Rename the project to `codex-chatgpt-bridge`.
- Vendor `XiaoDuoYa/codex-with-chatgpt` at `9663b88753e35c76796c5bce000293e0bd22cd9e`.
- Add `ccw c2c` integration for the C2C bridge, OAuth, read-only MCP, tunnel, session, doctor, and execution-record commands.
- Add the `INIT -> PLAN -> EXECUTING -> EXECUTED -> REVIEW -> DONE/BLOCKED` governance state machine.
- Add sanitized execution records and HANDOFF support.
- Add read-only external data-source contracts and validation.
- Keep receipt, prompt fingerprint, single submission, recovery, compression, verification, and the permanent Work ban.
- Prefer the In-app Browser and explicitly demote headed browser usage to an approved fallback.

## 0.1.1

- Add English and Simplified Chinese README files with top-level language switching.
- Add a concrete `agent-browser` adapter example.
- Add the live adapter smoke checklist.

## 0.1.0

- Vendor `chicogong/codex-chatgpt-web-orchestrator` at `0781dc2f18d853b77c546d5d59c6bed1243c5c47`.
- Add review-only Codex plugin and skills.
- Permit `chat-pro` and `deep-research`.
- Permanently reject `work` at routing, adapter validation, state, and verification layers.
- Add prompt fingerprints, single-submission state machine, recovery, raw/compressed output separation, and local verification.
- Add offline tests and Windows launchers.
