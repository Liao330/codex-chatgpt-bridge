# Delegation Receipt Protocol

The delegation receipt is the orchestrator's adapter-neutral handoff. It records what was authorized, submitted, observed, recovered, verified, and accepted without becoming a browser controller or exposing a private ChatGPT identity.

## Two-file boundary

- **Public receipt:** safe evidence, SHA-256 commitments, lifecycle state, route evidence, outputs, citations, acceptance, and integrity digest. It must pass `schemas/delegation-receipt.schema.json` and the stricter semantic validator in `scripts/delegation_receipt.py`.
- **Private sidecar:** raw adapter, run, and continuation identities. It must stay in a protected runtime location; this candidate gitignores `receipts/private/`. `schemas/delegation-receipt-private.schema.json` describes its minimal shape. The checked-in sidecars are synthetic fixtures only.

Never put credentials, personal paths, conversation URLs, cookies, account data, or raw identity fields in a public receipt. The public receipt carries domain-separated commitments for the three private identities so a sidecar can later prove that it belongs to the run without disclosing its values.

## Required bindings

1. `authorization.prompt_sha256` must equal `prompt.sha256`, and `exact_prompt_approved` must be true.
2. `submission.count` is restricted to zero or one. A committed run requires an observed acknowledgement.
3. `route_evidence` records the visible surface, intended mode, exact displayed model label, evidence source, and verification flags.
4. `outcome` keeps `generating`, `partial`, `incomplete`, and `complete` distinct. Complete requires both a terminal signal and captured final output.
5. Artifacts include media type, byte count, capture flag, and content hash. Citations are ordinary HTTPS URLs, never conversation URLs.
6. Acceptance can be `accept` only for a complete outcome; every criterion retains an evidence reference.
7. Continuation exposes only availability, a private-locator flag, and the same continuation commitment stored in `private_binding`.

## Tamper detection

Canonicalize the entire public receipt except `integrity.canonical_sha256` as UTF-8 JSON with sorted keys and compact separators. Hash those bytes with SHA-256. `integrity.covered_fields` must name every public top-level field other than `integrity` in protocol order. Any field mutation, removal, insertion, or reordered coverage list invalidates the receipt.

Private identities use domain-separated commitments:

```text
SHA256("delegation-receipt:" + identity_kind + ":" + raw_identity)
```

Validate the public receipt before any submit decision, then validate the private sidecar pair before recovery or continuation. A failed validation always yields no-send.

## Adapter mappings

The fixtures demonstrate structural mappings only:

- `native-control-style` maps a browser/thread bridge with visible controls and a bound tab or task identity.
- `oracle-style` maps a saved-browser-session workflow whose adapter report is checked against a visible postcondition.

These names do not claim official compatibility, affiliation, or a stable upstream API. The project contains no third-party code, selectors, or session implementation. An adapter must translate its own runtime evidence into this receipt and still satisfy the same governance gates.
