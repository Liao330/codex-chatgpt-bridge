# Vendor patches

Both upstream bases are vendored nearly verbatim. Everything not listed here is
upstream code. `dist/` inside the vendored packages is git-ignored; run
`.\ccw.cmd c2c build` (or `pnpm build` inside the package) after changing `src/`.

Re-apply the patches below after syncing an upstream base.

## XiaoDuoYa/codex-with-chatgpt

### 1. Quick-tunnel readiness must not depend on the local resolver

- Files: `src/tunnel/cloudflared.ts`, `src/tunnel/cloudflared-named.ts`, `tests/tunnel.test.ts`
- Symptom: `ccw c2c start --tunnel` failed with `Tunnel start timed out` while the
  public URL was already serving (`/health` = 200 from the internet, `/mcp` = 401).
- Cause: the Quick Tunnel provider only resolved `start()` after a successful
  `GET <publicUrl>/health` **from the local machine**. On networks where a
  brand-new `*.trycloudflare.com` name does not resolve locally, that probe
  returned `ENOTFOUND` for the whole 45s window (measured 50s+ of `fetch failed /
  ENOTFOUND`), even though `curl` resolved the same name immediately.
- Change: after cloudflared prints `Registered tunnel connection`, the provider
  keeps probing for `healthGraceMs` and then accepts the tunnel with a warning if
  the local probe still cannot confirm the bridge. Behaviour is unchanged for
  healthy networks, and the existing tests still require the probe when it works.
- Environment:
  - `C2C_TUNNEL_HEALTH_GRACE_MS` - default `15000`; `0` accepts the tunnel as soon
    as cloudflared registers the connection.
  - `C2C_TUNNEL_START_TIMEOUT_MS` - default `45000`; raise on slow networks.
    Applied to both the quick and the named provider.
- Upstream sync note: keep the new `envMs()` helper, the `healthGraceMs` option,
  the `registeredAt` bookkeeping inside `startProcess()`, and the extra test
  ("accepts a registered connection when the local health probe cannot resolve the
  public name").

### 2. Retry a failed quick-tunnel spawn

- File: `src/tunnel/cloudflared.ts`, `tests/tunnel.test.ts`
- Symptom: `ccw c2c start --tunnel` failed with `cloudflared exited (code 1) before
  establishing a tunnel`, and cloudflared's stderr said
  `failed to request quick Tunnel: Post "https://api.trycloudflare.com/tunnel":
  context deadline exceeded (Client.Timeout exceeded while awaiting headers)`.
- Cause: Cloudflare's account-less quick-tunnel API is intermittently slow. The very
  same POST completed in ~4s over HTTP/1.1 (curl) while cloudflared's HTTP/2 client
  stalled, so a single attempt failed the whole start even though the next would work.
- Change: `start()` retries `startProcess()` up to `C2C_TUNNEL_START_ATTEMPTS` times
  with `C2C_TUNNEL_RETRY_DELAY_MS` between attempts, and only then throws the last
  error.
- Environment:
  - `C2C_TUNNEL_START_ATTEMPTS` - default `3`.
  - `C2C_TUNNEL_RETRY_DELAY_MS` - default `2000`.
- Test note: existing cases keep single-attempt semantics through `setupTunnel()`;
  retry behaviour has its own case ("retries the spawn when cloudflared exits before
  establishing a tunnel").
