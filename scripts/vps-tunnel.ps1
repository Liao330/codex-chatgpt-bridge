# codex-chatgpt-bridge: keep a reverse SSH tunnel to the relay VPS alive.
# Forwards  <relay>:127.0.0.1:<RemotePort>  ->  this machine 127.0.0.1:<LocalPort>
# The relay address lives in ~/.ssh/config (alias "c2c-relay"), never in this repo.
# Usage: powershell -ExecutionPolicy Bypass -File vps-tunnel.ps1 [-SshTarget c2c-relay]
param(
  [string]$SshTarget = "c2c-relay",
  [int]$RemotePort = 8081,
  [int]$LocalPort = 48765
)
$logDir = Join-Path $env:LOCALAPPDATA "codex-chatgpt-bridge"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "vps-tunnel.log"
function Write-Log([string]$msg) {
  $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
  Add-Content -Path $log -Value $line
}
Write-Log "watchdog started (target=$SshTarget remote=$RemotePort local=$LocalPort)"
while ($true) {
  Write-Log "connecting..."
  & ssh -N -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ConnectTimeout=15 -R "127.0.0.1:$RemotePort`:127.0.0.1:$LocalPort" $SshTarget 2>> $log
  Write-Log "ssh exited (code $LASTEXITCODE); retrying in 10s"
  Start-Sleep -Seconds 10
}
