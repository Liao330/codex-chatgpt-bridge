<#
.SYNOPSIS
  One-click client setup for codex-chatgpt-bridge on a machine that runs a bridge.
.DESCRIPTION
  - verifies node/python/ssh and the ssh alias to the relay
  - installs the logon supervisor (bridge + reverse tunnel, see scripts/startup.ps1)
  - starts the bridge for the given workspace and checks the relay hop
  - prints the ChatGPT-side steps for this workspace
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
$supervisor = Join-Path $repo "scripts\startup.ps1"

Step "Checking prerequisites"
if (-not (Test-Path $ccw)) { throw "ccw.cmd not found at $ccw - run this from the codex-chatgpt-bridge checkout." }
if (-not (Test-Path $supervisor)) { throw "supervisor missing: $supervisor" }
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
  throw "Cannot reach '$SshTarget' with key authentication. Add it to ~/.ssh/config and copy your public key to the relay. Last error: $probe"
}
Ok "relay reachable with key auth"

Step "Installing the logon supervisor (bridge + tunnel)"
$startupDir = [Environment]::GetFolderPath("Startup")
$vbsPath = Join-Path $startupDir "codex-chatgpt-bridge.vbs"
$vbs = 'Set sh = CreateObject("WScript.Shell")' + "`r`n" +
       'sh.Run "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""' + $supervisor + '"" -WorkspacePath ""' + $WorkspacePath + '"" -SshTarget ""' + $SshTarget + '"" -RemotePort ' + $RemotePort + ' -LocalPort ' + $LocalPort + '", 0, False' + "`r`n"
Set-Content -Path $vbsPath -Value $vbs -Encoding ASCII
Ok "startup entry: $vbsPath"

$running = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
  Where-Object { $_.CommandLine -match "startup\.ps1" }
if ($running) {
  Ok "supervisor already running (pid $($running.ProcessId -join ','))"
} else {
  $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $supervisor, "-WorkspacePath", $WorkspacePath, "-SshTarget", $SshTarget, "-RemotePort", $RemotePort, "-LocalPort", $LocalPort)
  $p = Start-Process -FilePath "powershell.exe" -ArgumentList $args -WindowStyle Hidden -PassThru
  Start-Sleep -Seconds 15
  Ok "supervisor started (pid $($p.Id))"
}

Step "Bridge status"
$status = (& $ccw c2c exec -- status -w $WorkspacePath --json) | ConvertFrom-Json
Ok "bridge pid $($status.pid), local port $($status.port)"

Step "Reaching the bridge through the relay"
$relayHealth = & ssh -o BatchMode=yes $SshTarget "curl -s -m 10 http://127.0.0.1:$RemotePort/health"
if ($relayHealth -match '"status":"ok"') { Ok "relay -> bridge health ok" } else { Warn "relay health check returned: $relayHealth" }

Step "Next steps (ChatGPT side, once per workspace)"
Write-Host "  1. Create a connector at https://chatgpt.com/plugins#settings/Connectors?create-connector=true&redirectAfter=%2Fplugins"
Write-Host "     Name: Codex with ChatGPT - <workspace name> | Server URL: https://<relay>.<tailnet>.ts.net/mcp | Auth: OAuth + risk acknowledgement"
Write-Host "  2. Press Connect, then run: $ccw c2c exec -- pair -w '$WorkspacePath' --json"
Write-Host "  3. Bind a dedicated Project: $ccw c2c exec -- session set -w '$WorkspacePath' --connector-name '<connector name>' --mode project --project-url <project url>"
