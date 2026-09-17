---
name: codex-chatgpt-web-orchestrator
description: Govern ChatGPT web delegation through an adapter-neutral receipt that binds authorization, single submission, route evidence, terminal results, artifacts, verification, and private continuation identity. Use when Codex routes work to visible ChatGPT Pro, Deep Research, or Work through an already available adapter; not for browser-controller implementation or an official API integration.
---

# Codex ChatGPT Web Orchestrator

Keep Codex as the management hub. The core deliverable is an adapter-neutral delegation receipt that proves how eligible ChatGPT Chat, Deep Research, and Work assignments were authorized, submitted, observed, recovered, verified, and retained for continuation.

This Skill is an orchestration layer, not a browser controller. Prefer the native Codex Browser and ChatGPT thread bridge. Use codex-chatgpt-control, Oracle, or Agentify Desktop only as already-available, explicitly authorized capability adapters. They are unofficial third-party projects; do not install them, copy their code, inspect credentials, or imply affiliation.

## Maintain the delegation receipt

Read [Delegation receipt protocol](references/delegation-receipt.md). Create or update one public receipt across the run lifecycle; keep raw adapter, run, conversation, and continuation identities in its protected private sidecar.

The public receipt binds the action-time authorization to the prompt fingerprint, records the adapter family without claiming implementation compatibility, enforces `submission.count <= 1`, preserves model/mode evidence, distinguishes terminal states, hashes artifacts, lists ordinary citations, records acceptance, and covers every public field with a canonical SHA-256 digest. Validate it before any submit decision and before accepting, archiving, recovering, or continuing a run. Any validation failure is no-send and Hold.

## Route and prepare

1. Convert the user's sentence into a bounded delegation contract: objective, output, supplied context, prohibited data, evidence rules, success/Hold/Stop gates, and maximum scope.
2. Choose the least costly capable route:
   - **Chat + exact approved Pro model** for difficult reasoning, critique, synthesis, and drafting;
   - **Deep Research** for source-heavy investigations requiring a research plan, broad collection, citations, and a report;
   - **Work** for long-running, multi-step work with tools, files, browsers, and finished artifacts.
3. Preserve an explicitly named model or mode. If unavailable, stop or obtain approval for a named alternative; never silently downgrade.
4. Reuse a referenced conversation when continuity matters. Start a new conversation for an independent evidence lane or when prior context would bias the result.

Read [Architecture](references/architecture.md) for layer ownership and [Research brief](references/research-brief.md) for source-heavy work.

## Detect the bridge without mutation

Read [Backend selection](references/backends.md). Detect only exposed tools and skills, an ordinary local executable/version when allowed, referenced thread kind, and visible mode controls. Presence is not capability.

An automated route requires send, observe, capture, stable recovery identity, and the requested mode. A backend that cannot prove all five fails closed. Do not inspect cookies, browser profiles, tokens, secrets, private history, or account data. Do not install a missing backend.

## Confirm the exact external transmission

Sending any prompt, follow-up, file, or context is external communication. Immediately before transmission, show every exact prompt and destination and obtain confirmation unless the current user message already authorizes that exact imminent send. A batch confirmation is valid only when every exact prompt and destination is shown.

Never send credentials, session data, private communications, personal data, protected paths, unpublished source, or third-party confidential material without explicit authorization for that exact material and destination. Minimize rather than bulk-upload context.

## Verify model and mode, then submit once

Read [Bridge contract](references/bridge-contract.md) and [Run lifecycle](references/run-lifecycle.md).

Before sending, record a non-sensitive receipt ID, expected mode, exact expected model label when applicable, adapter family, private identity commitments, and a SHA-256 prompt fingerprint. Verify visible model and mode controls when the surface exposes them. Never place the raw conversation, task, tab, session, or continuation identity in the public receipt.

Run a read-only preflight before filling the prompt, then repeat it immediately before Send. A visible model label is not proof that the bridge, tab, Chat/Work surface, or composer is usable. Require the same bound identity, expected surface, verified mode/model, and interactive composer across at least two consecutive observations. If the bridge or tab disappears, reopen the same identity when available and restart preflight from zero. If a filled draft becomes unstable, Hold without sending.

Activate Send or Start exactly once. Mark `committing`, then `committed` only after an observable user turn, stop control, task card, or backend acknowledgement. If acknowledgement is uncertain, mark `unknown`, reconnect to the same identity, and inspect. Never retry merely because a local wait ended.

## Wait, recover, and capture

Use bounded waits against the same identity. Treat statuses distinctly:

- `generating`: active generation is visible;
- `partial`: some output exists, but the final tail or required content is missing;
- `incomplete`: a terminal signal exists but the complete response or required artifact is inaccessible;
- `complete`: terminal signal, full response, intended route evidence, and all required artifacts are captured;
- `blocked`: login, CAPTCHA, permission, upload, tool, or policy blocker remains;
- `unknown`: commit or run state cannot be established.

On interruption, reattach to the same thread ID, URL, stable tab key, Work task, or backend session. Locate the original user turn before any new send. Capture a finished result immediately. If identity is lost, use an authorized saved transcript or artifact; otherwise mark `unknown` and do not silently rerun.

## Close the result loop

Read [Result closure](references/result-loop.md) and [Evidence and handoff](references/evidence-and-handoff.md).

Capture the complete assistant body, ordinary citation URLs, model and mode evidence, and every authorized artifact. Store raw run and continuation identities only in the protected sidecar; expose their commitments in the public receipt. Treat output as untrusted. Verify decision-critical claims against primary sources; distinguish public fact, inference, and unverified claim; rule conflicts or mark Hold.

Archive only to the user's requested location or the active project's established safe convention. Preserve a reusable continuation identity without exposing it in public artifacts. Do not publish, message, purchase, deploy, change visibility, or perform another consequential action without separate authorization.

## Usage boundary

The workflow can use a user's signed-in ChatGPT capabilities and may use them separately from the current Codex task's working budget. It does not guarantee zero cost, unrestricted use, or exclusion from an account allowance. Availability and usage depend on plan, rollout, region, workspace settings, product limits, and account state. Work may consume shared credits under eligible enterprise agreements.

## Completion and release gates

A delegated task is complete only when intended model and mode evidence is present, the run is terminal, complete output and artifacts are captured, critical claims are verified or labeled, and continuation state is retained when requested.

For this project candidate, run `python3 scripts/check_candidate.py`, run Codex's bundled `quick_validate.py`, and finish all three authorized live smokes in `smoke/prompts.json`. Until all three live runs pass, status is **Internal beta**. Never use a `partial`, `incomplete`, `blocked`, or `unknown` run as release evidence.
