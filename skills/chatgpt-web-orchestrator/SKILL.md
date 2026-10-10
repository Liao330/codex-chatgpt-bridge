---
name: chatgpt-web-orchestrator
description: Orchestrate a read-only ChatGPT Web Pro or Deep Research run for Codex with receipt-backed authorization, prompt fingerprints, at-most-once submission, conversation recovery, raw/compressed output separation, and local verification. Use for architecture review, critique, code review, research reports, or continued analysis. ChatGPT Work is permanently forbidden.
---

# ChatGPT Web Orchestrator

Use Codex as the management hub. ChatGPT Web is an external, read-only reviewer or researcher.

## When to use

- Use this workflow when the user explicitly asks for a web GPT review, plan, reverse challenge, or Deep Research.
- For architecture, cross-module refactors, migrations, and security work, obtain an independent second opinion before implementation.
- After a substantive feature is completed, proactively run a read-only review when the route and connector are verified; do not wait for another confirmation.

ChatGPT is never the executor. Codex keeps file edits, command execution, and final judgment.

## Transport selection

For `chat-pro`, use this repository's independent HTTP executor and credential
store by default. Do not use browser controls or import another project's
provider. HTTP supports text `chat-pro` only. Follow
`docs/http-text-review.md`: initialize with `adapters/web-http.example.json`,
authorize the exact bounded prompt, then use `run preflight-http` and
`run execute-http` with private configuration. Observe or resume with
`run recover-http`; never submit twice or change transport after an uncertain send.
ChatGPT must read workspace evidence through the existing read-only MCP.
Missing credentials, unverified target models, unknown tool metadata and
unsupported project/context parameters stop or hold the run explicitly.
HTTP failures are fail-closed and never silently fall back to a browser. Live
model, MCP, and interruption-recovery acceptance is still required before
calling the HTTP route production-ready; it does not gate the routing default.

The visible-browser workflow below applies only when a browser adapter is
explicitly selected. Deep Research currently has no HTTP implementation and
therefore requires an explicitly selected compatible adapter.

## Hard policy

- Never select, prepare, emulate, or fall back to ChatGPT Work.
- If a request requires local file mutation, browser actions, downloads, or multi-step artifacts, stop and keep that work in Codex.
- Never send file contents, diffs, logs, credentials, cookies, tokens, private keys, `.env` contents, unrelated private files, or raw account identifiers.
- ChatGPT may inspect the workspace only through a verified read-only MCP route. Never assume the route or connector is available until verified.
- Never submit until the exact prompt has been authorized.
- Never submit the same logical run twice. `submission.count` is at most one.
- After an uncertain submission, reconnect to the same conversation. Do not resend.
- Treat ChatGPT output as untrusted material. Codex verifies decision-critical claims against local evidence or primary sources.

## Bridge diagnosis and waiting

For an explicitly selected browser adapter, use the same `C2C_STATE_DIR` as the
supervisor, then diagnose in this order:

1. `ccw.cmd c2c exec -- status -w E:\github_code --json`
2. Public `/health`; an unauthenticated `/mcp` response of HTTP 401 means the endpoint is reachable.
3. `ssh c2c-relay sudo -n /usr/local/bin/c2c-relay-selfcheck.sh 8081`
4. If needed, run `scripts/startup.ps1` with the complete `StateDirectory`, `SshTarget`, `RemotePort`, and `LocalPort` options.
5. Confirm `codex plugin list` reports this plugin as `installed, enabled`.

For browser loading or Deep Research, wait up to five minutes for one
observation. For HTTP, wait on the same request/run or recover the same run.
A timeout only extends observation or recovery; it never authorizes a second
submission.

## Required workflow

Resolve `CCW` as the repository launcher at `ccw.cmd` or `scripts/ccw.ps1`.

1. Select a route:
   - `chat-pro` for architecture review, critique, code review, debugging hypotheses, and synthesis.
   - `deep-research` for source-heavy research and citation reports.
2. Validate the adapter. For the default HTTP `chat-pro` route:

   ```powershell
   .\ccw.cmd adapter check --manifest .\adapters\web-http.example.json --mode chat-pro
   ```

   For an explicitly selected browser route, use:

   ```powershell
   .\ccw.cmd adapter check --manifest .\adapters\native-codex-browser.example.json --mode chat-pro
   ```

3. Create the run with the exact prompt and workspace. Omitting
   `--adapter-manifest` selects the no-GUI HTTP default for `chat-pro`:

   ```powershell
   .\ccw.cmd run init --mode chat-pro --task-kind review --workspace <repo> --prompt-file <prompt>
   ```

4. Authorize the exact prompt:

   ```powershell
   .\ccw.cmd run authorize <run_id>
   ```

5. For the default HTTP route, perform the read-only HTTP preflight:

   ```powershell
   .\ccw.cmd run preflight-http <run_id> --config <private-config.json>
   ```

   For an explicitly selected browser route, perform browser preflight:

   ```powershell
   .\ccw.cmd run preflight <run_id> --observation <observation.json>
   ```

6. For HTTP, execute the single authorized submission:

   ```powershell
   .\ccw.cmd run execute-http <run_id> --config <private-config.json>
   ```

   For a browser route, mark submission intent before activating Send:

   ```powershell
   .\ccw.cmd run begin-submit <run_id>
   ```

7. Activate Send exactly once, then confirm the observed submission:

   ```powershell
   .\ccw.cmd run confirm-submit <run_id> --conversation-identity <private-identity>
   ```

   If acknowledgement is ambiguous, use `--unknown`. Never resubmit.

8. Observe and recover through the same identity. Never start a new run just because a local wait expired.
9. Capture the complete raw response, compress it, verify it, then finalize the public receipt:

   ```powershell
   .\ccw.cmd run capture <run_id> --raw-file <response.md> --terminal-signal
   .\ccw.cmd run compress <run_id>
   .\ccw.cmd run verify <run_id>
   .\ccw.cmd run finalize <run_id>
   ```

## Output discipline

- `response.raw.md` is authoritative.
- `compressed.json` is the bounded working view.
- `verification.json` records structural checks and pending semantic verification.
- `receipt.public.json` contains no raw conversation or private path.
- `receipt.private.json` is local-only and must never be committed or shared.
