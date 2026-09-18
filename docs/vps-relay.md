# VPS relay for the C2C bridge

The bridge listens on `127.0.0.1` only. This relay exposes it with a public HTTPS
URL without touching the local machine's firewall or router.

    ChatGPT Web
      -> https://<public-url>/mcp            (Cloudflare edge, valid certificate)
      -> relay VPS: cloudflared              (datacenter network, QUIC)
      -> VPS 127.0.0.1:8081
      -> SSH reverse tunnel                  (scripts/vps-tunnel.ps1)
      -> 127.0.0.1:48765 (C2C bridge)        (local machine)

## Why this shape

- Cloudflare Quick Tunnels run from the **local** machine die quickly on consumer
  networks (port 7844 timeouts, "Unauthorized: Tunnel not found"). Running
  cloudflared on the VPS avoids that.
- The bridge sets `app.set("trust proxy", true)` and falls back to the request
  `Host` header when no tunnel provider set a public URL, so a plain reverse proxy
  is enough and the OAuth issuer stays consistent.
- Tencent Cloud blocks unfiled domains with SNI filtering on this VPS and ChatGPT
  rejects IP-literal connector URLs, so the public hop is a Cloudflare hostname.

## Components

1. **Local watchdog** - `scripts/vps-tunnel.ps1` keeps
   `ssh -N -R 127.0.0.1:8081:127.0.0.1:48765` alive (reconnects every 10s).
   Installed at logon through a `.vbs` file in the Startup folder; log:
   `%LOCALAPPDATA%\codex-chatgpt-bridge\vps-tunnel.log`.
2. **VPS cloudflared** - quick tunnel to `http://127.0.0.1:8081`; see
   `deploy/cf-quick-tunnel.service`.
3. **ChatGPT connector** - created against `https://<public-url>/mcp` with OAuth,
   then paired with a one-time `ccw c2c pair` code.

## Known limitation

A Quick Tunnel gets a new hostname every time cloudflared restarts, so the ChatGPT
connector has to be pointed at the new URL again (delete this workspace's connector,
recreate it, re-pair). For a permanent URL use a provider with a static domain
(for example an ngrok reserved domain) and keep the same relay layout.

## Verify

```powershell
curl.exe -s https://<public-url>/health          # {"service":"c2c-bridge",...,"status":"ok"}
curl.exe -s -o NUL -w "%{http_code}" https://<public-url>/mcp   # 401
node scripts/c2c-data-plane-smoke.mjs https://<public-url> <pairingCode> <workspaceName>
```
