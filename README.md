# Codex ChatGPT Bridge

**English** | [中文](README.zh-CN.md)

A dual-plane bridge for using ChatGPT Web as a planning, review, and research brain while Codex keeps execution and final judgment.

The project combines two pinned MIT foundations:

- `chicogong/codex-chatgpt-web-orchestrator` for routing, receipts, lifecycle, recovery, and governance.
- `codex-with-chatgpt` for the C2C control protocol, read-only workspace MCP, OAuth 2.1, pairing, Cloudflare tunnels, execution records, and session recovery.

The Codex In-app Browser is the preferred control surface. A headed system browser is fallback-only and requires explicit user approval.

## Permanent policy

**ChatGPT Work is forbidden.**

The route parser, adapter manifest validation, state machine, tests, MCP policy, and verifier all reject Work. The supported modes are:

- `chat-pro`: architecture analysis, code review, critique, synthesis, and reverse-challenge.
- `deep-research`: source-heavy research with citations and long-running recovery.

## What is implemented

- Receipt-backed authorization and prompt fingerprinting.
- `submission.count <= 1` with explicit `committing` and `committed` states.
- Conversation identity recovery without blind resend.
- `generating`, `complete`, `partial`, `incomplete`, `blocked`, and `unknown` outcomes.
- Separate raw response, compressed working view, and verification record.
- Code-review file and line structural checks.
- Deep Research HTTPS citation checks and semantic-verification handoff.
- Read-only workspace MCP with code, search, git, test, and sanitized execution tools.
- `INIT -> PLAN -> EXECUTING -> EXECUTED -> REVIEW -> DONE/BLOCKED` governance.
- Sanitized execution records and HANDOFF support.
- Read-only external data-source contracts with row, byte, and timeout limits.
- Offline tests that never open a browser or use a ChatGPT account.

## Repository layout

```text
.codex-plugin/       Codex plugin manifest
adapters/            Capability manifests
docs/                Phase status, live smoke, and proxy fallback
examples/            Example manifests and observations
references/          Bridge, data-plane, lifecycle, and output contracts
schemas/             Receipt, verification, and read-only data-source schemas
skills/              Codex skills
src/ccw/             Local Python governance and integration package
tests/               Offline unit and CLI tests
vendor/              Pinned governance and C2C bridge sources
scripts/             Windows launchers, tests, and dependency helpers
```

## Quick start

Run the local governance tests:

```powershell
.\scripts\test.ps1
```

Run the vendored C2C bridge tests:

```powershell
.\scripts\test-c2c.ps1
```

Validate the plugin:

```powershell
.\scripts\validate-plugin.ps1
```

Check the C2C environment and install the project-local tunnel binary:

```powershell
.\ccw.cmd c2c detect
.\ccw.cmd c2c build
.\scripts\install-cloudflared.ps1
```

## Integrated C2C loop

The control plane sends tiny `[C2C]` state messages through the In-app Browser. The data plane exposes read-only workspace MCP tools so ChatGPT can inspect code, diffs, search results, git state, tests, and sanitized execution records itself.

```powershell
.\ccw.cmd c2c exec -- start --tunnel
.\ccw.cmd c2c exec -- doctor
```

Governance transitions are mirrored locally:

```powershell
.\ccw.cmd cycle set <run_id> --state INIT --iteration 0 --task-id <task_id>
.\ccw.cmd cycle set <run_id> --state PLAN --iteration 1
.\ccw.cmd cycle set <run_id> --state EXECUTING --iteration 1
.\ccw.cmd cycle record-execution <run_id> `
  --iteration 1 `
  --changed-file src/a.ts `
  --tests "27 passed" `
  --exit-status ok `
  --command "pnpm test" `
  --output-file .\test.log
.\ccw.cmd cycle set <run_id> --state EXECUTED --iteration 1
```

Control messages stay under 1 KB and never contain file bodies, diffs, or logs. Detailed output is stored locally, sanitized, and exposed to ChatGPT only through the read-only data plane.

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

# 3. Record read-only In-app Browser preflight evidence.
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

The same receipt and single-submission rules apply. Deep Research can run for a long time, but timeout never authorizes a second submission. Capture the complete report and ordinary HTTPS citations before compression.

## Recovery

```powershell
.\ccw.cmd run recover <run_id> --observation .\recovery.json
```

Recovery always prefers the same conversation identity. If identity is lost and no saved capture exists, the run becomes `unknown`; it is never silently rerun.

## Read-only data plane

Workspace MCP is the primary data plane. Optional production data sources must satisfy [references/data-plane.md](references/data-plane.md):

- Read-only views or replicas.
- OAuth 2.1 for remote endpoints.
- Hard row, byte, and timeout limits.
- Sensitive-field redaction and audit logs.
- No write, shell, commit, deployment, or administrative tools.

Validate an external data-source contract:

```powershell
.\ccw.cmd data validate --manifest .\examples\readonly-data-source.sqlite.json
```

## Adapter contract

Required capabilities:

- `send`
- `observe`
- `capture`
- `stable_identity`

Route capability:

- `chat_pro`
- `deep_research`

Adapters must not expose Work. See [references/bridge-contract.md](references/bridge-contract.md).

## Proxy fallback

Prefer the In-app Browser. Only if it cannot reach the target and the user explicitly approves the fallback, use the `agent-browser` proxy configuration in [docs/proxy.md](docs/proxy.md). Do not launch a headed system browser when the In-app Browser works.

## Live smoke

Real browser/account smoke is separate from offline tests. Follow [docs/live-smoke.md](docs/live-smoke.md) only with explicit authorization to use the signed-in ChatGPT account.

## Private data

Runtime state is stored in `CCW_HOME`, default `~/.ccw/runs/<run_id>`. `private.json` and `receipt.private.json` contain raw conversation identities and must never be committed or shared. Public receipts contain commitments only.

## Upstream

See [UPSTREAM.md](UPSTREAM.md) and [THIRD_PARTY.md](THIRD_PARTY.md).
