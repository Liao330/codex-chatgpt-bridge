# Output Contract

Each run keeps three separate artifacts:

## Raw response

`response.raw.md` is the authoritative response. It is never replaced by a summary.

## Compressed working view

`compressed.json` contains:

- `summary`
- `findings` for `chat-pro`
- `key_points` for `deep-research`
- `citations`
- `uncertainties`
- `raw_ref`
- `raw_sha256`

The compressor must preserve file references, line numbers, commands, warnings, counterexamples, and citation URLs. It must not strengthen uncertainty or remove contrary evidence.

## Verification

`verification.json` records:

- structural checks;
- missing or invalid file/line references;
- invalid citation URLs;
- checks that only Codex can complete;
- whether semantic verification is still required.

`passed` means structural checks passed. It does not mean the model's claims are true.

## Public receipt

`receipt.public.json` contains commitments and evidence only. It must not contain raw conversation URLs, private paths, prompt text, or secrets.
