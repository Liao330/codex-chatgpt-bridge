---
name: codex-chatgpt-loop
description: Run a bounded ChatGPT planning/review loop with Codex execution using the vendored Codex with ChatGPT bridge. Use when ChatGPT should inspect the actual workspace through read-only MCP, Codex should execute, and each iteration needs checkpoint, receipt, recovery, and sanitized evidence. ChatGPT Work remains forbidden.
---

# Codex ChatGPT Loop

Use the In-app Browser only. Never launch a headed system Chrome unless the user explicitly approves that fallback.

## Control plane

Use the tiny C2C state protocol:

```text
INIT -> PLAN -> EXECUTING -> EXECUTED -> REVIEW -> PLAN | DONE | BLOCKED
```

Control messages must stay under 1 KB. They carry state, task ID, goal, success criteria, checkpoint, and next step. They never carry file bodies, diffs, or logs.

Mirror each transition into the local governance ledger:

```powershell
.\ccw.cmd cycle set <run_id> --state INIT --iteration 0 --task-id <task_id>
```

## Data plane

Start and diagnose the vendored bridge through:

```powershell
.\ccw.cmd c2c build
.\ccw.cmd c2c detect
.\ccw.cmd c2c exec -- start --tunnel
.\ccw.cmd c2c exec -- doctor
```

ChatGPT must read workspace facts through the read-only MCP tools. Do not paste files, diffs, or logs into the browser chat.

## Execution record

After Codex executes an iteration:

```powershell
.\ccw.cmd cycle set <run_id> --state EXECUTING --iteration <n>
.\ccw.cmd cycle record-execution <run_id> `
  --iteration <n> `
  --changed-file path/to/file `
  --tests "27 passed" `
  --exit-status ok `
  --command "pnpm test" `
  --output-file .\test.log
.\ccw.cmd cycle set <run_id> --state EXECUTED --iteration <n>
```

The local sanitizer redacts secrets and home paths, caps output, and never grants ChatGPT shell access.

## Final gates

- No ChatGPT Work.
- No write/shell/commit MCP tools.
- No duplicate prompt submission for the same iteration.
- Verify the actual git diff and test evidence.
- `DONE` requires objective completion evidence.
- `BLOCKED` preserves the reason.
- `unknown` or disconnected work must reconnect to the same conversation or use HANDOFF.

External production data is optional and must satisfy `references/data-plane.md`.
