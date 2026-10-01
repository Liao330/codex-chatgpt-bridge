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

## One command (once the relay exists)

```powershell
# prerequisites: ssh alias "c2c-relay" in ~/.ssh/config + your public key on the relay
powershell -ExecutionPolicy Bypass -File deploy\install.ps1 -WorkspacePath E:\github_code
```

It runs, in order:

| Step | Script | What it does |
|---|---|---|
| 1 | `deploy\install-client.ps1` | checks node/python/ssh and key auth, installs the logon supervisor, starts the bridge, verifies the relay hop |
| 2 | `deploy\install-codex-plugin.ps1` | junctions this checkout into `%USERPROFILE%\plugins`, writes the personal marketplace, enables the plugin, retires loose skill copies |

Both are idempotent and print the remaining ChatGPT-side steps.

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

`scripts/startup.ps1` checks the bridge and SSH tunnel independently every five seconds.
A living SSH tunnel does not hide a stopped bridge. Three consecutive bridge failures
are required before recovery; repeated recovery attempts back off from 10 seconds to
five minutes. Successful probes must remain stable for a minute before resetting that
backoff. CLI probes time out after 10 seconds and HTTP probes after two seconds.

Use one canonical workspace, one explicit state directory, and one local port:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\install-client.ps1 `
  -WorkspacePath E:\github_code `
  -StateDirectory "$env:LOCALAPPDATA\codex-with-chatgpt" `
  -SshTarget c2c-relay -RemotePort 8081 -LocalPort 48765
```

The installer writes these exact options into a hidden logon launcher and only reuses
an exactly matching supervisor invocation. It does not stop old or uncertain processes;
retire a legacy supervisor only after verifying its full command and creation time.
The supervisor holds a machine-wide lock keyed by the real workspace path and local
port, independently of the state directory, so a second logon or a different state
option cannot create a second supervisor for the same bridge.

State-directory environment is passed only to bridge/CLI child processes. For manual
CLI commands, set `C2C_STATE_DIR` to the same directory in that CLI session. Keep its
`auth`, `runtime`, and session files; do not change workspace roots or migrate OAuth
registrations automatically. Existing authorization is preserved through restart.

A bridge is adopted only when `/health`, authenticated CLI `status`, runtime state,
actual listening PID, exact repo CLI `serve --workspace` command, and process creation
time agree. Recovery may stop only a process whose identity this supervisor previously
proved. Foreign listeners, mismatched ports, malformed runtime, changed PID identity,
or uncertain listener queries fail closed. Inspect the phase log and resolve ownership
manually; reconnecting ChatGPT cannot repair an incorrect local state directory.

Before a controlled restart, authorization and runtime are copied to a current-user-only
ACL directory under `StateDirectory\supervisor-backups`. A failed backup leaves the
bridge intact. New children are explicitly started with `serve --port`; if the bridge
falls back to a random port during a startup race, only that freshly created child is
stopped after its PID, command, and creation time are rechecked. The SSH process runs
hidden and reconnects independently with bounded backoff.

Logs contain phase names, not CLI output, authorization, or credentials, at
`%LOCALAPPDATA%\codex-chatgpt-bridge\startup-<workspace-port-key>.log`.
Typical phases are `healthy`, `stopped`, `recovery-started`, `untrusted-state`,
`port-mismatch`, and `recovery-refused`. Shutdown leaves a healthy bridge running.

Optional startup controls: `-PollSeconds 5`, `-FailureThreshold 3`,
`-CliTimeoutSeconds 10`. Health recovery cannot keep a powered-off computer online or
prevent authorization revocation. OAuth lifetimes are unchanged: access tokens last
one hour and refresh tokens have a rolling 30-day expiry. Thirty days without a
successful refresh can still require reauthorization.

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

The message means the running bridge does not recognize the `client_id` sent by
ChatGPT. Possible causes include missing registration, a changed workspace, a different
state directory, or a stale process using another state. It does not by itself prove
that a token expired.

Check the fixed workspace and state directory first, then inspect the supervisor phase
log and authenticated CLI status. A healthy HTTP endpoint alone does not prove that the
CLI and bridge share administrator state. Preserve and securely back up authorization
before any controlled recovery. Do not copy client registrations or clear tokens as an
automatic repair. If registration truly was lost, restore the correct state backup or
recreate the ChatGPT connection so it registers again.

The 2026-10-02 incident and its evidence limits are recorded in
[incident-history.md](incident-history.md), with structured statistics in
[incidents.json](incidents.json).

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

The bridge runs in the background; Codex also has to know **when** to use it. One
command installs it as a plugin, and the plugin ships the five skills:

```powershell
powershell -ExecutionPolicy Bypass -File deploy\install-codex-plugin.ps1
```

What it does (every step is idempotent):

1. creates `%USERPROFILE%\plugins\codex-chatgpt-bridge` as a **directory junction** to
   this checkout, so the marketplace serves the live git working tree (no copy drift);
2. writes or updates the personal marketplace at
   `%USERPROFILE%\.agents\plugins\marketplace.json`;
3. registers `[marketplaces.personal]` and enables
   `[plugins."codex-chatgpt-bridge@personal"]` in `%USERPROFILE%\.codex\config.toml`
   (timestamped config backup first);
4. retires loose copies of the five skills from `%USERPROFILE%\.codex\skills` by moving
   them into a `skills-backup-<timestamp>` folder.

Restart the Codex app afterwards so it rescans marketplaces. The plugin list then shows a
single entry - **Codex ChatGPT Bridge** - carrying `chatgpt-web-orchestrator`,
`chatgpt-pro-analysis`, `chatgpt-deep-research`, `chatgpt-result-compress` and
`codex-chatgpt-loop`.

### Why five skills inside one plugin, not one merged skill

Codex only loads a skill body when its description matches the task, so one merged skill
would drag the Deep Research citation rules into every code review and blur the triggers.
The plugin is the single entry point and the single on/off switch; the skills stay precise
triggers. See the table below for the policy that decides when they fire.

### Updating the plugin after editing this repo

The junction means source edits are visible immediately. If Codex caches the plugin,
bump the manifest cachebuster and reinstall from the same marketplace:

```bash
python3 ~/.codex/skills/.system/plugin-creator/scripts/update_plugin_cachebuster.py <plugin-path>
```

## Trigger policy (also written into %USERPROFILE%\.codex\AGENTS.md)

| Situation | Behaviour |
|---|---|
| The user asks ("review this with GPT", "deep research", "challenge this") | Use it directly |
| High-risk change: architecture, cross-module refactor, migration, security | Use it before implementing |
| A substantial feature just landed | **Offer** a review, do not auto-run |
| Trivial or mechanical edits, low risk, not requested | Do not use it |

Hard rules to repeat in AGENTS.md: ChatGPT is read-only, Work is forbidden, never paste
file bodies/diffs/logs into the chat, and show the outgoing prompt to the user before
submitting unless they already said "just send it".

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| ChatGPT tool call returns `UNAVAILABLE`, or the connector shows disconnected | Client machine off, tunnel down or bridge dead. Run the relay self-check: `ssh <relay> /usr/local/bin/c2c-relay-selfcheck.sh 8081`, then `scripts/startup.ps1` on the client machine. |
| Authorize page says **Unknown client. Please reconnect from ChatGPT.** | The running process does not recognize the cached client. Verify workspace, explicit state directory, runtime/listener identity and authenticated CLI status; preserve state and resolve uncertain ownership before reconnecting. See the incident record and Unknown client section above. |
| ChatGPT still shows the old tool list (for example `git_status` without the `repo` argument) | Tool schemas are cached per connector. Press **Reconnect** in the plugin actions menu so ChatGPT re-reads `/mcp`. |
| Bridge not running after a reboot | `powershell -ExecutionPolicy Bypass -File scripts\startup.ps1 -WorkspacePath <root>`; log: `%LOCALAPPDATA%\codex-chatgpt-bridge\startup-<workspace-port-key>.log`. |
| Want to see the data plane end to end | `node scripts/c2c-data-plane-smoke.mjs https://<relay>.<tailnet>.ts.net <pairingCode> <workspaceName>` |

## Verify

```powershell
curl.exe -s https://<relay>.<tailnet>.ts.net/health              # {"status":"ok"}
curl.exe -s -o NUL -w "%{http_code}" https://<relay>.<tailnet>.ts.net/mcp   # 401
node scripts/c2c-data-plane-smoke.mjs https://<relay>.<tailnet>.ts.net <pairingCode> <workspaceName>
```

Last verified end to end: ChatGPT Web called `workspace_info` and `read_file` through
the relay and answered `e2e-workspace` / `hello from C2C e2e`; the same flow was
re-checked after killing the bridge and the tunnel (the supervisor restored both).
