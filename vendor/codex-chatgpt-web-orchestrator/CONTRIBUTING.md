# Contributing

Contributions should preserve the project's narrow role: orchestration and governance around visible, user-directed ChatGPT web work. Do not add hidden endpoints, credential extraction, browser-profile copying, quota bypass, or a second general browser controller.

## Before proposing a change

1. Explain the observable failure or missing capability.
2. Keep provider-specific UI mechanics behind the bridge contract.
3. Add or update a public fixture that reproduces the behavior without account data.
4. Add a behavioral test; avoid tests that merely match prose.
5. Run `python3 scripts/check_candidate.py` and Codex's bundled `quick_validate.py`.
6. Review changed files for personal paths, private identifiers, credentials, and copied third-party text or code.

Do not include live conversation transcripts, screenshots of account state, private repository context, or unpublished artifacts in an issue or contribution.

## Compatibility claims

State whether a capability was verified in a live authorized run, observed only in public upstream documentation, or inferred from an interface contract. Do not describe an optional backend as official or bundled.

## Release-impacting changes

Changes to external transmission, prompt confirmation, uploads, duplicate-run behavior, archival, licensing, publishing, or third-party dependencies require explicit maintainer review. A local test pass does not authorize a live smoke or release.
