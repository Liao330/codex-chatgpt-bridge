# Changelog

- Remove the experimental tunnel paths and keep one supported deployment story:
  dropped `deploy/cf-quick-tunnel.service`, `scripts/install-cloudflared.ps1`,
  `scripts/vps-tunnel.ps1`, `docs/proxy.md`, and `docs/phase-status.md`; added
  `docs/deployment.md`. `scripts/startup.ps1` now supervises both the bridge and the
  reverse tunnel at logon, so a reboot needs no manual step (verified by killing both
  and letting the supervisor restore them).

## Unreleased

- Fix `c2c start --tunnel` failing with `Tunnel start timed out` on networks where the
  local machine cannot resolve a brand-new `*.trycloudflare.com` name: once cloudflared
  reports a registered connection the quick-tunnel provider no longer blocks forever on
  the local `/health` probe. See `docs/vendor-patches.md`.
- Add `C2C_TUNNEL_START_TIMEOUT_MS` and `C2C_TUNNEL_HEALTH_GRACE_MS` knobs.
- Add `scripts/c2c-data-plane-smoke.mjs` for end-to-end read-only data-plane checks
  (OAuth discovery, PKCE pairing, tool listing, `workspace_info`, `read_file`, git and
  execution tools, `.env` denial).
## 0.2.0

- Rename the project to `codex-chatgpt-bridge`.
- Vendor `XiaoDuoYa/codex-with-chatgpt` at `9663b88753e35c76796c5bce000293e0bd22cd9e`.
- Add `ccw c2c` integration for the C2C bridge, OAuth, read-only MCP, tunnel, session, doctor, and execution-record commands.
- Add the `INIT -> PLAN -> EXECUTING -> EXECUTED -> REVIEW -> DONE/BLOCKED` governance state machine.
- Add sanitized execution records and HANDOFF support.
- Add read-only external data-source contracts and validation.
- Keep receipt, prompt fingerprint, single submission, recovery, compression, verification, and the permanent Work ban.
- Prefer the In-app Browser and explicitly demote headed browser usage to an approved fallback.

## 0.1.1

- Add English and Simplified Chinese README files with top-level language switching.
- Add a concrete `agent-browser` adapter example.
- Add the live adapter smoke checklist.

## 0.1.0

- Vendor `chicogong/codex-chatgpt-web-orchestrator` at `0781dc2f18d853b77c546d5d59c6bed1243c5c47`.
- Add review-only Codex plugin and skills.
- Permit `chat-pro` and `deep-research`.
- Permanently reject `work` at routing, adapter validation, state, and verification layers.
- Add prompt fingerprints, single-submission state machine, recovery, raw/compressed output separation, and local verification.
- Add offline tests and Windows launchers.

- Add the relay path for networks where Cloudflare Quick Tunnels cannot hold a
  connection: `scripts/startup.ps1` (logon supervisor for the bridge and the reverse
  tunnel) and `docs/deployment.md`. Verified end to end: ChatGPT Web called `workspace_info` and
  `read_file` through the relay and returned the workspace name and file contents.
