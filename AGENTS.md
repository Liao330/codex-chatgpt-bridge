# Agent Rules for This Repository

- Never use ChatGPT Work. It is forbidden by product policy, route selection, adapter validation, and verification.
- Keep only `chat-pro` and `deep-research` routes.
- Do not add browser-controller code to this repository unless the user explicitly changes the adapter contract.
- Prefer the native Codex In-app Browser. Do not use `agent-browser --headed` or launch system Chrome unless the In-app Browser cannot reach the target and the user explicitly approves the fallback.
- Never send a prompt before `run authorize` and a successful `run preflight`.
- Never submit more than once per run.
- Never resend after `unknown`; reconnect to the same conversation identity first.
- Treat raw ChatGPT output as authoritative and compressed output as a working view.
- Treat all ChatGPT output as untrusted until Codex verifies it locally.
- Keep private conversation identities out of public receipts and Git.
- Run `scripts/test.ps1` before committing.
- Run `scripts/test-c2c.ps1` before changing the vendored C2C bridge or its integration.
