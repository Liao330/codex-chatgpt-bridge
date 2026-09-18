# VPS relay for the C2C bridge

The bridge listens on `127.0.0.1` only. This relay exposes it with a **permanent**
public HTTPS URL without touching the local machine's firewall or router.

    ChatGPT Web
      -> https://codex-c2c-vps.tail8496c3.ts.net/mcp   (Tailscale Funnel, valid cert, port 443)
      -> VPS 127.0.0.1:8081
      -> SSH reverse tunnel                            (scripts/vps-tunnel.ps1)
      -> 127.0.0.1:48765 (C2C bridge, local machine)

## Why this shape

- Cloudflare Quick Tunnels started from the **local** machine die within minutes on
  consumer networks here (`dial tcp <edge>:7844: i/o timeout`, then
  `Unauthorized: Tunnel not found`), which breaks the ChatGPT connector mid-use.
- This Tencent Cloud VPS blocks unfiled domains with SNI filtering, and ChatGPT
  rejects IP-literal connector URLs, so the VPS cannot serve the connector directly.
- Tailscale Funnel terminates TLS on Tailscale's edge, so the public hostname is
  stable, publicly resolvable and certificate-valid, while the VPS only makes an
  outbound connection.

## Components

1. **Local watchdog** - `scripts/vps-tunnel.ps1` keeps
   `ssh -N -R 127.0.0.1:8081:127.0.0.1:48765` alive (reconnect loop, 10s backoff).
   Started at logon by a `.vbs` in the Startup folder; log:
   `%LOCALAPPDATA%\codex-chatgpt-bridge\vps-tunnel.log`.
2. **VPS: tailscaled + Funnel**
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   tailscale up --hostname=codex-c2c-vps      # one-time browser authorisation
   tailscale funnel --bg 8081                 # persists across reboots
   ```
   Requires HTTPS certificates and Funnel enabled for the tailnet in the admin console.
3. **ChatGPT connector** - created against
   `https://codex-c2c-vps.tail8496c3.ts.net/mcp` with OAuth, then paired once with
   `ccw c2c pair`.

## Notes

- The bridge sets `app.set("trust proxy", true)` and derives the OAuth issuer from the
  request `Host`/`X-Forwarded-Proto` when no tunnel provider is running, so the relay
  needs no bridge configuration.
- nginx + a Let's Encrypt IP certificate (`/etc/nginx/ssl`) were installed during
  bring-up as an alternative entry point. They are optional; Funnel does not use them.
- `deploy/cf-quick-tunnel.service` is kept as a fallback relay (Cloudflare Quick
  Tunnel **from the VPS**): a datacenter connection holds up much better than a home
  one, but the hostname changes on every restart, so the ChatGPT connector has to be
  re-pointed when that happens.

## Verify

```powershell
curl.exe -s https://codex-c2c-vps.tail8496c3.ts.net/health          # status ok
curl.exe -s -o NUL -w "%{http_code}" https://codex-c2c-vps.tail8496c3.ts.net/mcp   # 401
node scripts/c2c-data-plane-smoke.mjs https://codex-c2c-vps.tail8496c3.ts.net <pairingCode> <workspaceName>
```

Last verified: ChatGPT Web called `workspace_info` and `read_file` through the relay and
answered `e2e-workspace` / `hello from C2C e2e`.
