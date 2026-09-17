# Live Adapter Smoke Checklist

Run this checklist only with explicit user authorization. It opens a signed-in ChatGPT Web session and sends prompts under the user's account.

## Phase 1: Native adapter

- [ ] Confirm the native Codex Browser / ChatGPT thread tools are exposed.
- [ ] Run `ccw adapter detect` with the actual read-only inventory.
- [ ] Confirm `native` is present.
- [ ] Verify send, observe, capture, and stable identity capabilities.
- [ ] Confirm `work` is absent.
- [ ] Run two read-only preflight reads with the same bound chat and stable composer.
- [ ] Confirm the visible model is the exact approved Pro model.

## Phase 2: Chat + Pro review

- [ ] Create a run with a small diff and `--mode chat-pro --task-kind review`.
- [ ] Authorize the exact prompt.
- [ ] Record native preflight.
- [ ] Activate Send exactly once.
- [ ] Confirm the acknowledgement.
- [ ] Capture the complete raw response.
- [ ] Compress and verify the response.
- [ ] Confirm every file/line finding against the repository.
- [ ] Finalize the receipt.

## Phase 3: Recovery and compression

- [ ] Force one safe timeout by waiting on the same run without sending again.
- [ ] Confirm `ccw run recover` returns a reconnect-first action.
- [ ] Confirm `partial`, `incomplete`, `blocked`, and `unknown` never become `complete`.
- [ ] Confirm `response.raw.md` remains authoritative.
- [ ] Confirm `compressed.json` preserves citations and uncertainty.
- [ ] Confirm private identities are absent from `receipt.public.json`.

## Phase 4: Deep Research

- [ ] Create a run with `--mode deep-research --task-kind source-research`.
- [ ] Confirm the adapter exposes `deep_research`.
- [ ] Start exactly one Deep Research run.
- [ ] Disconnect or wait through a safe timeout without resending.
- [ ] Reconnect to the same task identity.
- [ ] Capture the complete report and HTTPS citations.
- [ ] Verify decision-critical claims against primary sources.
- [ ] Finalize the public receipt.

## Evidence to retain

- `run.json`
- `events.jsonl`
- `response.raw.md`
- `compressed.json`
- `verification.json`
- `receipt.public.json`
- private sidecars kept locally and out of Git
