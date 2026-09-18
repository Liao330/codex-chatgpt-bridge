# Deployment

One bridge per workspace, one public URL, no inbound ports on the local machine.

     ChatGPT Web
       -> https://<relay>.<tailnet>.ts.net/mcp      Tailscale Funnel (valid TLS, port 443)
       -> relay host 127.0.0.1:<port>               SSH reverse tunnel from your machine
       -> 127.0.0.1:48765                           C2C bridge (read-only MCP)

The bridge only listens on loopback. The relay is a Linux VM that is reachable from
the internet; it terminates nothing itself - Tailscale Funnel publishes the loopback
port and the SSH tunnel carries it back to your machine.

## Why this layout

- The bridge sets `app.set("trust proxy", true)` and derives the OAuth issuer from the
  request `Host` / `X-Forwarded-Proto` when no tunnel provider set a public URL, so a
  plain port forward is enough and the OAuth metadata stays consistent.
- A stable hostname means the ChatGPT connector is configured once. Providers that hand
  out a new hostname on every restart force you to delete and recreate the connector
  each time.
- The relay never stores the workspace: it only forwards bytes to the SSH tunnel.

## 1. Relay host (once)

```bash
sudo bash deploy/relay-setup.sh --port 8081 --hostname codex-c2c-vps
# if it asks: enable HTTPS Certificates and Funnel for the tailnet in the
# Tailscale admin console, then run the printed command again
```

Requires an account that can log into Tailscale (free tier is fine) and a Linux VM
with outbound internet. Any small VPS works.

## 2. Each machine that runs a bridge

```powershell
# one-time: add the relay to ~/.ssh/config as an alias and put your public key on it
#   Host c2c-relay
#       HostName <relay host>
#       User <user>
#       ServerAliveInterval 30
#       ServerAliveCountMax 3

powershell -ExecutionPolicy Bypass -File deploy\install-client.ps1 -WorkspacePath <absolute path to repo>
```

The installer verifies node/python/ssh, checks key auth to the relay, installs the
logon supervisor, starts the bridge, checks the relay hop, and prints the ChatGPT-side
steps. It is idempotent.

## 3. Auto-start

`scripts/startup.ps1` is the single supervisor: it keeps **both** the bridge and the
SSH tunnel alive and restarts them after a reboot or crash. It is launched at logon by
a `.vbs` in the Startup folder (`deploy/install-client.ps1` writes it) and logs to
`%LOCALAPPDATA%\codex-chatgpt-bridge\startup.log`.

```powershell
# run it by hand if you ever want to restart everything
powershell -ExecutionPolicy Bypass -File scripts\startup.ps1 -WorkspacePath <path>
```

## 4. ChatGPT side (once per workspace)

1. Create a connector at
   `https://chatgpt.com/plugins#settings/Connectors?create-connector=true&redirectAfter=%2Fplugins`
   Name it `Codex with ChatGPT - <workspace name>`, Server URL `https://<relay>.<tailnet>.ts.net/mcp`,
   Authentication `OAuth`, tick the risk acknowledgement, Create.
2. Press **Connect**, then run
   `.\ccw.cmd c2c exec -- pair -w <workspace> --json` and type the code on the page.
3. Keep the conversation inside a dedicated ChatGPT Project:
   `.\ccw.cmd c2c exec -- session set -w <workspace> --project-url <project url> --connector-name "<connector name>" --mode project`

One connector per workspace, one Project per workspace. Never point two workspaces at
the same connector.

## Multi-user

Each person runs **their own bridge** on their own machine and pairs **their own
ChatGPT account**. Isolation options for the relay:

| Setup | How |
|---|---|
| Own relay (simplest, recommended) | Each person runs `deploy/relay-setup.sh` on their own VM. Nothing is shared. |
| Shared relay | Funnel can publish several ports (443, 8443, 10000): give each person a different `--port` on the relay and a matching SSH tunnel. Path prefixes are **not** supported - the bridge derives OAuth URLs from the host only. |

The OAuth token lives in the bridge state of the machine that runs it. A different
machine serving the same workspace needs its own pairing (30 seconds: `c2c pair`).

## Verify

```powershell
curl.exe -s https://<relay>.<tailnet>.ts.net/health              # {"status":"ok"}
curl.exe -s -o NUL -w "%{http_code}" https://<relay>.<tailnet>.ts.net/mcp   # 401
node scripts/c2c-data-plane-smoke.mjs https://<relay>.<tailnet>.ts.net <pairingCode> <workspaceName>
```

Last verified end to end: ChatGPT Web called `workspace_info` and `read_file` through
the relay and answered `e2e-workspace` / `hello from C2C e2e`; the same flow was
re-checked after killing the bridge and the tunnel (the supervisor restored both).
