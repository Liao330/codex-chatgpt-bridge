---
name: chatgpt-web-orchestrator
description: Orchestrate a read-only ChatGPT Web Pro or Deep Research run for Codex with receipt-backed authorization, prompt fingerprints, at-most-once submission, conversation recovery, raw/compressed output separation, and local verification. Use for architecture review, critique, code review, research reports, or continued analysis. ChatGPT Work is permanently forbidden.
---

# ChatGPT Web Orchestrator

Use Codex as the management hub. ChatGPT Web is an external, read-only reviewer or researcher.

## Hard policy

- Never select, prepare, emulate, or fall back to ChatGPT Work.
- If a request requires local file mutation, browser actions, downloads, or multi-step artifacts, stop and keep that work in Codex.
- Never send secrets, cookies, tokens, private keys, `.env` contents, unrelated private files, or raw account identifiers.
- Never submit until the exact prompt has been authorized.
- Never submit the same logical run twice. `submission.count` is at most one.
- After an uncertain submission, reconnect to the same conversation. Do not resend.
- Treat ChatGPT output as untrusted material. Codex verifies decision-critical claims against local evidence or primary sources.

## Required workflow

Resolve `CCW` as the repository launcher at `ccw.cmd` or `scripts/ccw.ps1`.

1. Select a route:
   - `chat-pro` for architecture review, critique, code review, debugging hypotheses, and synthesis.
   - `deep-research` for source-heavy research and citation reports.
2. Validate the adapter:

   ```powershell
   .\ccw.cmd adapter check --manifest .\adapters\native-codex-browser.example.json --mode chat-pro
   ```

3. Create the run with the exact prompt and workspace:

   ```powershell
   .\ccw.cmd run init --mode chat-pro --task-kind review --workspace <repo> --adapter-manifest <manifest> --prompt-file <prompt>
   ```

4. Authorize the exact prompt:

   ```powershell
   .\ccw.cmd run authorize <run_id>
   ```

5. Perform a read-only preflight with the native Codex Browser / ChatGPT thread bridge. Record the observation through:

   ```powershell
   .\ccw.cmd run preflight <run_id> --observation <observation.json>
   ```

6. Mark submission intent before activating Send:

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
