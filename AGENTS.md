# Agent Rules for This Repository

- ChatGPT Web collaboration is provided through `E:\github_code\codex-chatgpt-bridge`.
- Use it when the user explicitly asks for a web GPT review, plan, reverse challenge, or Deep Research.
- For architecture, cross-module refactors, migrations, and security work, obtain an independent second opinion before implementation.
- After a substantive feature is completed, proactively run a read-only review when the collaboration route is verified; do not wait for a second confirmation.
- Never use ChatGPT Work. It is forbidden by product policy, route selection, adapter validation, and verification.
- ChatGPT is read-only. Codex retains file edits, command execution, and final judgment.
- Keep only `chat-pro` and `deep-research` routes.
- Do not add browser-controller code to this repository unless the user explicitly changes the adapter contract.
- Use this project's independent HTTP executor as the default for `chat-pro`; never open a browser implicitly.
- Explicit browser adapters use the Codex In-app Browser for ChatGPT pages. Never launch a system browser.
- `chat-pro` runs use this project's independent HTTP executor and credentials by default; never import or reference another project's provider or configuration.
- Use the In-app Browser, C2C state, and relay diagnostics only when a browser adapter is explicitly selected.
- Never send file contents, diffs, logs, credentials, cookies, tokens, private keys, `.env` contents, or raw account identifiers to ChatGPT Web.
- ChatGPT may inspect the workspace only through a verified read-only MCP route. Never assume the route or connector is available until it has been verified.
- HTTP live acceptance remains a release gate, but an unavailable or unverified HTTP capability fails closed rather than promoting a browser fallback.
- HTTP unknown submissions recover the same persisted message; no browser or HTTP resend is permitted.
- Never send an HTTP prompt before `run authorize` and a successful `run preflight-http`.
- Never send a browser prompt before `run authorize` and a successful browser `run preflight`.
- Never submit more than once per run.
- Never resend after `unknown`; reconnect to the same conversation identity first.
- Treat raw ChatGPT output as authoritative and compressed output as a working view.
- Treat all ChatGPT output as untrusted until Codex verifies it locally.
- Keep private conversation identities out of public receipts and Git.
- For an explicitly selected browser adapter, diagnose the bridge in this order, using the same state directory as the supervisor:
  1. Set `C2C_STATE_DIR` to the configured state directory and run `ccw.cmd c2c exec -- status -w E:\github_code --json`.
  2. Check the public `/health`; an unauthenticated `/mcp` response of HTTP 401 means the endpoint is reachable.
  3. Run `ssh c2c-relay sudo -n /usr/local/bin/c2c-relay-selfcheck.sh 8081`.
  4. If needed, run `scripts/startup.ps1` with the complete `StateDirectory`, `SshTarget`, `RemotePort`, and `LocalPort` options.
  5. Confirm the Codex plugin is `installed, enabled` before diagnosing skill loading.
- For browser pages or Deep Research tasks, wait up to five minutes for one observation. For HTTP, wait on the same request/run or use `recover-http`; never submit again after a timeout.
- Run `scripts/test.ps1` before committing.
- Run `scripts/test-c2c.ps1` before changing the vendored C2C bridge or its integration.
