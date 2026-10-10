# Agent Rules for This Repository

- Never use ChatGPT Work. It is forbidden by product policy, route selection, adapter validation, and verification.
- Keep only `chat-pro` and `deep-research` routes.
- Do not add browser-controller code to this repository unless the user explicitly changes the adapter contract.
- Use the Codex In-app Browser for every ChatGPT page. Never launch a system browser.
- Explicit `web-http` runs use this project's independent HTTP executor and credentials; never import or reference another project's provider or configuration.
- Keep the existing default until real target-model, read-only MCP and interruption-recovery acceptance all pass. Offline fixtures do not authorize promotion.
- HTTP unknown submissions recover the same persisted message; no browser or HTTP resend is permitted.
- Never send a prompt before `run authorize` and a successful `run preflight`.
- Never submit more than once per run.
- Never resend after `unknown`; reconnect to the same conversation identity first.
- Treat raw ChatGPT output as authoritative and compressed output as a working view.
- Treat all ChatGPT output as untrusted until Codex verifies it locally.
- Keep private conversation identities out of public receipts and Git.
- Run `scripts/test.ps1` before committing.
- Run `scripts/test-c2c.ps1` before changing the vendored C2C bridge or its integration.
