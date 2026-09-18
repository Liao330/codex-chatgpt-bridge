# codex-chatgpt-bridge: start-at-logon supervisor.
# Keeps BOTH halves alive on this machine:
#   1. the C2C bridge for one workspace  (ccw.c2c start, idempotent)
#   2. the reverse SSH tunnel to the relay (reconnect loop)
# The relay address lives in ~/.ssh/config as the alias passed to -SshTarget.
#
# Usage: powershell -ExecutionPolicy Bypass -File scripts\startup.ps1 -WorkspacePath <ws>
param(
  [Parameter(Mandatory = $true)][string]$WorkspacePath,
  [string]$SshTarget = "c2c-relay",
  [int]$RemotePort = 8081,
  [int]$LocalPort = 48765
)
$repo = Split-Path -Parent $PSScriptRoot
$ccw = Join-Path $repo "ccw.cmd"
$logDir = Join-Path $env:LOCALAPPDATA "codex-chatgpt-bridge"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "startup.log"

function Write-Log([string]$msg) {
  Add-Content -Path $log -Value ("{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg)
}

function Bridge-Running {
  try {
    $status = (& $ccw c2c exec -- status -w $WorkspacePath --json 2>$null) | Out-String
    return ($status -match '"running":true')
  } catch { return $false }
}

function Ensure-Bridge {
  if (Bridge-Running) { Write-Log "bridge already running"; return }
  Write-Log "starting bridge for $WorkspacePath"
  & $ccw c2c exec -- start -w $WorkspacePath --json 2>&1 | ForEach-Object { Write-Log "  $_" }
}

Write-Log "supervisor started (workspace=$WorkspacePath target=$SshTarget remote=$RemotePort local=$LocalPort)"

while ($true) {
  Ensure-Bridge
  Write-Log "opening reverse tunnel 127.0.0.1:$RemotePort -> 127.0.0.1:$LocalPort via $SshTarget"
  & ssh -N -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ConnectTimeout=15 -R "127.0.0.1:$RemotePort`:127.0.0.1:$LocalPort" $SshTarget 2>> $log
  Write-Log "ssh exited (code $LASTEXITCODE); bridge+tunnel restart in 10s"
  Start-Sleep -Seconds 10
}
