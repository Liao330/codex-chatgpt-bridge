# Reliable Run Lifecycle

Use this procedure for every automated or semi-automated web delegation.

## State record

Track these fields without storing prompt or response content unless needed:

| Field | Meaning |
|---|---|
| Run label | Local, non-sensitive name for this delegation |
| Backend | Native, codex-chatgpt-control, Oracle, Agentify, or manual |
| Intended route | Chat / Deep Research / Work and exact requested model |
| Conversation identity | Thread ID, URL, stable tab key, or backend session ID |
| Submission state | not-sent / committing / committed / unknown |
| Generation state | queued / generating / partial / incomplete / complete / blocked / unknown |
| Capture state | absent / partial / final / artifact-saved |
| Preflight state | acquiring / stabilizing / ready-to-fill / ready-to-send / hold |

Do not record credentials, cookies, account identifiers, or unrelated browser history.

## Before submission

1. Verify the selected backend exists without installing anything.
2. Resolve or create one visible conversation for the run and retain its reopen identity.
3. Acquire a live bridge binding to that exact tab or task.
4. Verify the intended Chat/Work surface, mode, model, and interactive composer twice consecutively on the same identity.
5. Check the prompt and attachments against the privacy boundary.
6. Obtain action-time confirmation for the exact transmission.
7. Fill the prompt only after `ready_to_fill_prompt`, then repeat the same preflight immediately before Send.

If the bridge or tab fails before prompt fill, keep `submission_count=0`, reacquire or reopen, and restart the stable-read count. If a draft is already filled when the surface becomes unstable, Hold without sending or copying it to a different surface. A model label that remains visible does not satisfy the surface or composer checks.

### Reopen order before the first send

1. Reattach the existing bound identity if it is still reopenable.
2. Otherwise reacquire the intended visible tab and establish a new stable identity only while `submission_count=0`.
3. Reapply the expected Chat/Work route and exact model selection.
4. Require two new consecutive stable observations; previous label evidence cannot be reused.
5. If the state cannot stabilize within the bounded preflight, return Hold with a structured reason and do not fill or send.

## Commit exactly once

After activating Send, mark the run `committing`. Look for an observable commit signal such as the user turn appearing, a stop control, a task card, or backend acknowledgement. Then mark it `committed`.

If acknowledgement is absent, mark submission `unknown`. Do not press Send again. Reopen or inspect the same conversation and determine whether the user turn exists.

## Monitor without resubmitting

Poll or wait against the same run identity. Use bounded waits so the user can receive progress updates, but treat a wait timeout only as “no new event observed.” Do not infer failure or completion from a timeout.

Useful completion signals include:

- the active-generation or stop control disappears after being observed;
- the backend reports a terminal success state;
- a final assistant turn is stable and fully readable;
- requested artifacts are present and downloadable.

Require both a terminal signal and accessible final output. Thread `idle` alone is insufficient.

## Capture checkpoint

As soon as completion is established:

1. capture the final assistant message in Markdown or structured text;
2. save or return authorized artifacts;
3. record the conversation URL/session identity and visible model/mode;
4. preserve cited source URLs;
5. label any missing tail, failed download, or inaccessible artifact as partial.

Do not close, replace, or navigate away from the only recoverable tab before capture.

## Recovery decision tree

```text
Can the same run identity be reopened?
  yes -> Is the original user turn present?
           no  -> original did not commit; a new send may be proposed
           yes -> Is generation active?
                    yes -> mark generating and wait/monitor the same run
                    no  -> Is a complete final response accessible?
                             yes -> capture it
                             no  -> mark partial, incomplete, or blocked; ask for direction
  no  -> Is there a saved backend transcript/artifact?
           yes -> recover and verify it
           no  -> mark unknown; do not silently rerun
```

Only the user may authorize a duplicate run when commit status cannot be proven.
