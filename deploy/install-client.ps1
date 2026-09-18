<#
.SYNOPSIS
  One-click client setup for codex-chatgpt-bridge on a NEW device.
.DESCRIPTION
  - verifies node/python/ssh and the ssh alias to the relay
  - installs the reverse-tunnel watchdog (starts at logon, reconnects automatically)
  - starts the C2C bridge for the given workspace
  - prints the connector URL to paste into ChatGPT
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File deploy\install-client.ps1 -WorkspacePath E:\github_code\my-project
#>
param(
  [Parameter(Mandatory = $true)][string]$WorkspacePath,
  [string]$SshTarget = "c2c-relay",
  [int]$RemotePort = 8081,
  [int]$LocalPort = 48765
)
$ErrorActionPreference = "Stop"

function Step($msg) { Write-Host ""; Write-Host "== $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "  [ok] $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  [!!] $msg" -ForegroundColor Yellow }

$repo = Split-Path -Parent $PSScriptRoot
$ccw = Join-Path $repo "ccw.cmd"

Step "Checking prerequisites"
if (-not (Test-Path $ccw)) { throw "ccw.cmd not found at $ccw - run this script from the codex-chatgpt-bridge checkout." }
Ok "repo: $repo"
foreach ($tool in @("node", "python", "ssh")) {
  if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "$tool is not on PATH" }
  Ok "$tool found"
}
if (-not (Test-Path $WorkspacePath)) { throw "workspace not found: $WorkspacePath" }
Ok "workspace: $WorkspacePath"

Step "Checking the relay SSH alias '$SshTarget'"
$probe = & ssh -o BatchMode=yes -o ConnectTimeout=10 $SshTarget "echo relay-ok" 2>&1
if ($LASTEXITCODE -ne 0 -or ($probe -notmatch "relay-ok")) {
  throw @"
Cannot reach '$SshTarget' with key authentication.
Add this to ~/.ssh/config (address from your relay operator) and put your public key on the relay:

Host $SshTarget
    HostName <relay-host>
    User <user>
    ServerAliveInterval 30
    ServerAliveCountMax 3

Last error: $probe
"@
}
Ok "relay reachable with key auth"

Step "Installing the reverse-tunnel watchdog"
$watchdog = Join-Path $repo "scripts\vps-tunnel.ps1"
if (-not (Test-Path $watchdog)) { throw "watchdog script missing: $watchdog" }
$startup = [Environment]::GetFolderPath("Startup")
$vbsPath = Join-Path $startup "codex-chatgpt-bridge-tunnel.vbs"
$vbs = @"
Set sh = CreateObject("WScript.Shell")
sh.Run "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""$watchdog""", 0, False
"@
Set-Content -Path $vbsPath -Value $vbs -Encoding ASCII
Ok "startup entry: $vbsPath"

$running = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
  Where-Object { $_.CommandLine -match "vps-tunnel" }
if ($running) {
  Ok "watchdog already running (pid $($running.ProcessId -join ','))"
} else {
  $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $watchdog, "-SshTarget", $SshTarget, "-RemotePort", $RemotePort, "-LocalPort", $LocalPort)
  $p = Start-Process -FilePath "powershell.exe" -ArgumentList $args -WindowStyle Hidden -PassThru
  Start-Sleep -Seconds 12
  Ok "watchdog started (pid $($p.Id))"
}

Step "Starting the C2C bridge"
& $ccw c2c exec -- start -w $WorkspacePath --json | Out-Host
$status = (& $ccw c2c exec -- status -w $WorkspacePath --json) | ConvertFrom-Json
Ok "bridge pid $($status.pid), local port $($status.port)"

Step "Reaching the bridge through the relay"
$relayHealth = & ssh -o BatchMode=yes $SshTarget "curl -s -m 10 http://127.0.0.1:$RemotePort/health"
if ($relayHealth -match '"status":"ok"') { Ok "relay -> bridge health ok" } else { Warn "relay health check returned: $relayHealth" }

Step "Next steps (ChatGPT side, once per workspace)"
Write-Host @"
  1. Open https://chatgpt.com/plugins#settings/Connectors?create-connector=true&redirectAfter=%2Fplugins
  2. Name it:  Codex with ChatGPT - <workspace name>
     Server URL: https://<your-tailnet-host>/mcp
     Auth:       OAuth   -> tick the risk acknowledgement -> Create
  3. Press Connect, then run:  $ccw c2c exec -- pair -w "$WorkspacePath" --json
     and type the printed code into the page.
  4. Record the binding:
     $ccw c2c exec -- session set -w "$WorkspacePath" --connector-name "<connector name>" --mode project
"@ -ForegroundColor Gray

