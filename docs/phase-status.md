# Phase Status

## Phase 1: Adapter verification

- [x] Pinned upstream orchestration base.
- [x] Read-only backend presence detection.
- [x] Adapter manifest validation.
- [x] Required capabilities: send, observe, capture, stable identity.
- [x] Mode capabilities: chat_pro and deep_research.
- [x] Dynamic preflight contract.
- [x] Fail-closed behavior when the adapter is incomplete.
- [x] Work capability rejected.

Acceptance evidence:

```powershell
.\ccw.cmd adapter detect --inventory .\examples\inventory.example.json
.\ccw.cmd adapter check --manifest .\adapters\native-codex-browser.example.json --mode chat-pro
.\ccw.cmd preflight check --observation .\examples\preflight.ready.json
```

## Phase 2: Chat + Pro review only

- [x] Exact prompt authorization.
- [x] SHA-256 prompt fingerprint.
- [x] `submission.count <= 1`.
- [x] Explicit `committing` and `committed` transitions.
- [x] `unknown` acknowledgement handling.
- [x] Same-conversation recovery policy.
- [x] File and line structural verification.
- [x] Work hard-forbidden at all layers.

## Phase 3: Compression and verification

- [x] Raw response captured separately.
- [x] Raw SHA-256 recorded.
- [x] Compressed JSON generated locally.
- [x] Citations and uncertainties preserved.
- [x] No second ChatGPT request used for compression.
- [x] Structural verification separate from semantic verification.
- [x] Public and private receipt separation.

## Phase 4: Deep Research

- [x] `deep-research` route.
- [x] Long-run recovery through stable identity.
- [x] Citation preservation and validation.
- [x] Research claims marked pending for primary-source verification.
- [x] Same at-most-once submission rule.
- [x] No Work or artifact route.

## Offline validation

```powershell
.\scripts\test.ps1
.\scripts\validate-plugin.ps1
```

The offline suite never opens a browser and never calls a ChatGPT account.

## Live acceptance

The real adapter smoke test is intentionally separated into [live-smoke.md](live-smoke.md). Run it only with explicit authorization to use the signed-in ChatGPT Web account.

## 0.2.0 integrated iteration

- [x] Vendored codex-with-chatgpt for the C2C control and read-only MCP data planes.
- [x] Added ccw c2c build, detect, and pass-through integration.
- [x] Added INIT -> PLAN -> EXECUTING -> EXECUTED -> REVIEW -> DONE/BLOCKED governance.
- [x] Added sanitized execution records and HANDOFF.
- [x] Added read-only external data-source contracts and validation.
- [x] Kept receipt, at-most-once submission, recovery, compression, verification, and the Work ban.
- [x] Prefer the In-app Browser; headed system Chrome is fallback-only.
