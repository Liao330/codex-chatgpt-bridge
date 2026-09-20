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

## One workspace for every repository

Rooting the bridge at a parent directory (for example `E:\github_code`) gives **one
connector for every project** on the machine:

```
workspace root  E:\github_code        <- one bridge, one connector, one ChatGPT Project
  |- financial-system                 (git repo)
  |- gogo-resolve-migration           (git repo)
  |- gogo-resolve-migration-...       (worktrees of the same repo)
  |- ...
```

- `workspace_info` returns `repos`: every git repository found under the root.
- `git_status {repo: "<name>"}` and `git_diff {repo: "<name>", mode: "unstaged"}`
  scope the git tools to one repository; `path` is relative to that repo.
- `read_file` / `list_directory` / `search_workspace` take workspace-relative paths,
  so `financial-system/src/app.py` works for any repository.
- Containment is unchanged: anything that escapes the root is rejected with
  `PATH_OUTSIDE_WORKSPACE`, and sensitive files stay denied.

Trade-off: one connector means one OAuth grant covering every repository below the
root. Run separate workspaces (separate ports + connectors) for projects that must
stay isolated.

### If the connector says "Unknown client"

ChatGPT caches one OAuth client registration per connector, and the bridge keeps those
registrations per workspace under
`%LOCALAPPDATA%\codex-with-chatgpt\auth\<workspaceId>.json`. After the workspace root
changes, the new store is empty and the authorize page answers *"Unknown client. Please
reconnect from ChatGPT."* Copy the client registrations over (tokens are workspace-bound
and can be dropped):

```powershell
# copy "clients" from the old store, keep "tokens" empty
# <old-id> -> <new-id> from: ccw.cmd c2c exec -- status -w <workspace> --json
```

Then restart the bridge (so the store is re-read) and press **Reconnect** on the
connector page. The tool list is refreshed at the same time, which is required after
upgrading the bridge (for example when the git tools gained the `repo` argument).

## Relay self-check

`deploy/relay-selfcheck.sh` verifies the three hops **from the relay's point of view**:
the client tunnel port is listening, Funnel still points at it, and the bridge answers
`/health`. Install it together with the shipped systemd timer (every 5 minutes):

```bash
scp deploy/relay-selfcheck.sh <relay>:/usr/local/bin/c2c-relay-selfcheck.sh
scp deploy/c2c-relay-selfcheck.service deploy/c2c-relay-selfcheck.timer <relay>:/etc/systemd/system/
ssh <relay> "chmod +x /usr/local/bin/c2c-relay-selfcheck.sh && systemctl daemon-reload && systemctl enable --now c2c-relay-selfcheck.timer"
```

Output goes to stdout and to syslog:

```bash
journalctl -t c2c-relay-selfcheck -n 20      # PASS / FAIL lines
/usr/local/bin/c2c-relay-selfcheck.sh 8081   # run on demand, non-zero exit when degraded
```

Typical failures it catches: the client machine is off (port not listening), Funnel lost
its mapping, or the bridge process died (health probe fails).

## Wire it into Codex (make it part of the normal flow)

The bridge runs in the background; Codex also has to know **when** to use it. Two
one-time steps per machine:

1. Install the skills into the Codex home:

   ```powershell
   powershell -ExecutionPolicy Bypass -File deploy\install-codex-skills.ps1
   ```

   It copies `skills/*` into `%USERPROFILE%\.codex\skills` and rewrites the
   repo-relative `.\ccw.cmd` references to this checkout, because global skills run
   from arbitrary repositories.

2. Add a short section to `%USERPROFILE%\.codex\AGENTS.md` with the endpoint, the
   connector name and the trigger policy. Recommended policy:

   | Situation | Behaviour |
   |---|---|
   | The user asks ("review this with GPT", "deep research", "challenge this") | Use it directly |
   | High-risk change: architecture, cross-module refactor, migration, security | Use it before implementing |
   | A substantial feature just landed | **Offer** a review, do not auto-run |
   | Trivial or mechanical edits, low risk, not requested | Do not use it |

   Hard rules to repeat in AGENTS.md: ChatGPT is read-only, Work is forbidden, never
   paste file bodies/diffs/logs into the chat, and show the outgoing prompt to the
   user before submitting unless they already said "just send it".

Without step 2 the skills exist but nothing invokes them: the loop stays manual.

## Verify

```powershell
curl.exe -s https://<relay>.<tailnet>.ts.net/health              # {"status":"ok"}
curl.exe -s -o NUL -w "%{http_code}" https://<relay>.<tailnet>.ts.net/mcp   # 401
node scripts/c2c-data-plane-smoke.mjs https://<relay>.<tailnet>.ts.net <pairingCode> <workspaceName>
```

Last verified end to end: ChatGPT Web called `workspace_info` and `read_file` through
the relay and answered `e2e-workspace` / `hello from C2C e2e`; the same flow was
re-checked after killing the bridge and the tunnel (the supervisor restored both).
