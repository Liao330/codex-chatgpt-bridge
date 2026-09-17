# Chicogong Codex Bridge

**English** | [中文](README.zh-CN.md)

A review-only Codex plugin for using ChatGPT Web **Chat + Pro** and **Deep Research** as external analysis/review capabilities.

This project uses `chicogong/codex-chatgpt-web-orchestrator` as its pinned orchestration base. It deliberately does not implement a browser controller; the preferred adapter is the native Codex Browser / ChatGPT thread bridge.

## Permanent policy

**ChatGPT Work is forbidden.**

The route parser, adapter manifest validation, state machine, tests, and verifier all reject Work. The two supported modes are:

- `chat-pro`: architecture analysis, code review, critique, synthesis, and reverse-challenge.
- `deep-research`: source-heavy research with citations and long-running recovery.

## What is implemented

- Receipt-backed authorization and prompt fingerprinting.
- `submission.count <= 1` with explicit `committing` and `committed` states.
- Conversation identity recovery without blind resend.
- `generating`, `complete`, `partial`, `incomplete`, `blocked`, and `unknown` outcomes.
- Separate raw response, compressed working view, and verification record.
- Code-review file/line structural checks.
- Deep Research HTTPS citation checks and semantic-verification handoff.
- Codex skills for orchestration, Pro analysis, Deep Research, and compression.
- Offline tests with no browser or ChatGPT account access.

## Repository layout

```text
.codex-plugin/       Codex plugin manifest
adapters/            Capability manifests
references/          Bridge, lifecycle, output, and review-only contracts
schemas/             Public receipt schemas copied from upstream context
skills/              Codex skills
src/ccw/             Local Python orchestration package
tests/               Offline unit and CLI tests
vendor/              Pinned upstream orchestration base
scripts/             Windows launchers and validation scripts
```

## Quick start

Run the offline test suite:

```powershell
.\scripts\test.ps1
```

Validate the plugin manifest:

```powershell
.\scripts\validate-plugin.ps1
```

Detect whether a native adapter is present without probing credentials:

```powershell
.\ccw.cmd adapter detect --inventory .\examples\inventory.example.json
```

Run a route plan:

```powershell
.\ccw.cmd route plan `
  --task-kind review `
  --mode chat-pro `
  --capabilities .\examples\capabilities.native.json
```

Attempting a Work-shaped task fails closed:

```powershell
.\ccw.cmd route plan `
  --task-kind artifact `
  --capabilities .\examples\capabilities.native.json
# exit code 3: ChatGPT Work is permanently disabled in this bridge
```

## Pro review lifecycle

```powershell
# 1. Create a run with the exact prompt.
.\ccw.cmd run init `
  --mode chat-pro `
  --task-kind review `
  --workspace E:\path\to\repo `
  --adapter-manifest .\adapters\native-codex-browser.example.json `
  --prompt-file .\prompt.md

# 2. Authorize the exact prompt.
.\ccw.cmd run authorize <run_id>

# 3. Record read-only native-browser preflight evidence.
.\ccw.cmd run preflight <run_id> --observation .\observation.json

# 4. Record the single submission intent and acknowledgement.
.\ccw.cmd run begin-submit <run_id>
.\ccw.cmd run confirm-submit <run_id> --conversation-identity <private-id>

# 5. Capture, compress, verify, and finalize.
.\ccw.cmd run capture <run_id> --raw-file .\response.md --terminal-signal
.\ccw.cmd run compress <run_id>
.\ccw.cmd run verify <run_id>
.\ccw.cmd run finalize <run_id>
```

Raw ChatGPT output is authoritative. `compressed.json` is only a bounded working view. Codex must verify every finding and decision-critical claim locally.

## Deep Research lifecycle

Use `--mode deep-research --task-kind source-research` or `research-report`.

The same receipt and single-submission rules apply. Deep Research runs may wait and reconnect much longer, but a timeout never authorizes a second submission. Capture the complete report and ordinary HTTPS citations before compression.

## Recovery

When a run is disconnected or ambiguous:

```powershell
.\ccw.cmd run recover <run_id> --observation .\recovery.json
```

Recovery always prefers the same conversation identity. If the identity is lost and no saved capture exists, the run becomes `unknown`; it is not silently rerun.

## Adapter contract

Required capabilities:

- `send`
- `observe`
- `capture`
- `stable_identity`

Route capability:

- `chat_pro`
- `deep_research`

The adapter must not expose Work.

See [Bridge contract](references/bridge-contract.md) and [Native Codex Browser adapter](references/native-codex-browser.md). A concrete `agent-browser` adapter example is available at `adapters/agent-browser.example.json`.

## Live smoke

The real browser/account smoke is intentionally separate from offline tests. Follow [docs/live-smoke.md](docs/live-smoke.md) only with explicit authorization to use the signed-in ChatGPT account.

## Private data

Runtime state is stored in `CCW_HOME`, default `~/.ccw/runs/<run_id>`. `private.json` and `receipt.private.json` contain raw conversation identities and must never be committed or shared. Public receipts contain commitments only.

## Upstream

See [UPSTREAM.md](UPSTREAM.md) and [THIRD_PARTY.md](THIRD_PARTY.md).
