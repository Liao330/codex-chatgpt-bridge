# Logon supervisor. No token output and no automatic adoption of uncertain processes.
param(
  [Parameter(Mandatory = $true)][string]$WorkspacePath,
  [string]$StateDirectory = (Join-Path $env:LOCALAPPDATA 'codex-with-chatgpt'),
  [string]$SshTarget = 'c2c-relay',
  [int]$RemotePort = 8081,
  [int]$LocalPort = 48765,
  [int]$PollSeconds = 5,
  [int]$FailureThreshold = 3,
  [int]$CliTimeoutSeconds = 10
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'bridge-supervisor.ps1')
if ($LocalPort -lt 1 -or $LocalPort -gt 65535 -or $RemotePort -lt 1 -or $RemotePort -gt 65535 -or $PollSeconds -lt 1 -or $FailureThreshold -lt 2 -or $CliTimeoutSeconds -lt 1) { throw 'Invalid supervisor options.' }
$repo = Split-Path -Parent $PSScriptRoot
$cli = Join-Path $repo 'vendor\codex-with-chatgpt\dist\cli\index.js'
$node = (Get-Command node -ErrorAction Stop).Source
$ssh = (Get-Command ssh -ErrorAction Stop).Source
$WorkspacePath = (Resolve-Path -LiteralPath $WorkspacePath).ProviderPath.TrimEnd('\')
if ($WorkspacePath -match '^[A-Za-z]:$') { $WorkspacePath += '\' }
$StateDirectory = [IO.Path]::GetFullPath($StateDirectory)
foreach ($value in @($WorkspacePath, $StateDirectory, $SshTarget, $cli)) { if ($value -match '["\r\n]') { throw 'Unsupported characters in supervisor option.' } }
if ($SshTarget.StartsWith('-')) { throw 'Invalid SSH target.' }
if (-not (Test-Path -LiteralPath $cli)) { throw 'Build the bundled bridge before installing its supervisor.' }
$lock = $null
$state = New-SupervisorState
$tunnel = $null; $nextTunnel = 0; $tunnelAttempts = 0; $bridgeChild = $null
$logDir = Join-Path $env:LOCALAPPDATA 'codex-chatgpt-bridge'
[void](New-Item -ItemType Directory -Force -Path $logDir)
$log = $null
$config = @{ Workspace = $WorkspacePath; LocalPort = $LocalPort; FailureThreshold = $FailureThreshold; InitialBackoffSeconds = 10; MaxBackoffSeconds = 300; CliEntry = $cli }
function Write-Phase([string]$Phase) { Add-Content -LiteralPath $log -Value ('{0:u} {1}' -f [datetime]::UtcNow, $Phase) }
function Read-Runtime {
  $file = Join-Path $StateDirectory ('runtime\' + $config.WorkspaceId + '.json')
  if (-not (Test-Path -LiteralPath $file)) { return $null }
  # Malformed state must never be mistaken for an empty state.
  try { return (Get-Content -LiteralPath $file -Raw | ConvertFrom-Json) } catch { return @{ port = -1; workspaceId = 'invalid' } }
}
function Read-Listener {
  return @(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object { $_.LocalPort -eq $LocalPort } | Select-Object -ExpandProperty OwningProcess -Unique)
}
function Read-Process([int]$ProcessId) { Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction Stop }
function Read-Health { try { Invoke-RestMethod -Uri "http://127.0.0.1:$LocalPort/health" -TimeoutSec 2 -ErrorAction Stop } catch { return $null } }
function Read-Status {
  try {
    $json = Invoke-BoundedProcess $node ('"' + $cli + '" status --workspace "' + $WorkspacePath + '" --json') $StateDirectory $CliTimeoutSeconds
    if ($json) { return ($json | ConvertFrom-Json) }
  } catch { }
  return $null
}
function Start-Bridge {
  if (@(Read-Listener).Count -ne 0) { throw 'port-occupied' }
  $matching = @(Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction Stop | Where-Object { Test-BridgeCommand $_ $config })
  if ($matching.Count -gt 0) { throw 'unregistered-process' }
  $old = Read-Runtime
  if ($old -and (Read-Process $old.pid)) { throw 'existing-process' }
  $info = New-Object Diagnostics.ProcessStartInfo
  $info.FileName = $node; $info.Arguments = '"' + $cli + '" serve --workspace "' + $WorkspacePath + '" --port ' + $LocalPort
  $info.UseShellExecute = $false; $info.CreateNoWindow = $true
  $info.EnvironmentVariables['C2C_STATE_DIR'] = $StateDirectory
  $info.RedirectStandardOutput = $true; $info.RedirectStandardError = $true
  $script:bridgeChild = New-Object Diagnostics.Process
  $script:bridgeChild.StartInfo = $info
  [void]$script:bridgeChild.Start()
  # Drain output asynchronously without persisting CLI output or credentials.
  $script:bridgeOut = $script:bridgeChild.StandardOutput.BaseStream.CopyToAsync([IO.Stream]::Null)
  $script:bridgeErr = $script:bridgeChild.StandardError.BaseStream.CopyToAsync([IO.Stream]::Null)
  $created = Read-Process $script:bridgeChild.Id
  $createdIdentity = Get-BridgeIdentity $created
  if (-not $createdIdentity -or -not (Test-BridgeCommand $created $config)) { throw 'child-identity-unavailable' }
  $childAdapters = @{
    Runtime = { Read-Runtime }; Listener = { Read-Listener }; Process = { param($ProcessId) Read-Process $ProcessId }
    Delay = { Start-Sleep -Milliseconds 500 }
    Stop = { param($ProcessId, $Identity)
      if ((Get-BridgeIdentity (Read-Process $ProcessId)) -ne $Identity) { throw 'identity-changed' }
      Stop-Process -Id $ProcessId -ErrorAction Stop
    }
  }
  Wait-SupervisedChild $script:bridgeChild $createdIdentity $config $childAdapters
  $state.Owned = $createdIdentity
}
function Stop-OwnedBridge([int]$ProcessId, [string]$Identity) {
  $runtime = Read-Runtime
  if (-not $runtime -or $runtime.pid -ne $ProcessId -or $runtime.port -ne $LocalPort -or $runtime.workspaceId -ne $config.WorkspaceId) { throw 'runtime-changed' }
  $target = Read-Process $ProcessId
  if ((Get-BridgeIdentity $target) -ne $Identity -or -not (Test-BridgeCommand $target $config)) { throw 'identity-changed' }
  Stop-Process -Id $ProcessId -ErrorAction Stop
  # Wait for vacancy before starting; do not fall back to a random port.
  for ($attempt = 0; $attempt -lt 20; $attempt++) { if (@(Read-Listener).Count -eq 0) { return }; Start-Sleep -Milliseconds 100 }
  throw 'port-still-occupied'
}
function Ensure-Tunnel([double]$Now) {
  if ($script:tunnel -and -not $script:tunnel.HasExited) {
    if (($Now - $script:tunnelStarted) -ge 60) { $script:tunnelAttempts = 0 }
    return
  }
  if ($script:tunnel) { $script:tunnel.Dispose(); $script:tunnel = $null }
  if ($Now -lt $script:nextTunnel) { return }
  $script:tunnelAttempts++
  $script:nextTunnel = $Now + [Math]::Min(300, 10 * [Math]::Pow(2, [Math]::Min(10, $script:tunnelAttempts - 1)))
  try {
    $arguments = '-N -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ConnectTimeout=15 -R "127.0.0.1:' + $RemotePort + ':127.0.0.1:' + $LocalPort + '" "' + $SshTarget + '"'
    $script:tunnel = Start-Process -FilePath $ssh -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $script:tunnelStarted = $Now
    Write-Phase 'tunnel-started'
  } catch { Write-Phase 'tunnel-start-failed' }
}
try {
  # Use the actual Node workspace identity (realpath handling matches the bridge).
  $identityJson = Invoke-BoundedProcess $node ('"' + $cli + '" workspace --workspace "' + $WorkspacePath + '" --json') $StateDirectory $CliTimeoutSeconds
  if (-not $identityJson) { throw 'workspace-identity-unavailable' }
  $workspaceInfo = $identityJson | ConvertFrom-Json
  $WorkspacePath = $workspaceInfo.root
  $config.Workspace = $WorkspacePath; $config.WorkspaceId = $workspaceInfo.workspaceId
  $key = Get-SupervisorKey $WorkspacePath $LocalPort
  $lock = Enter-SupervisorLock $key
  if (-not $lock) { return }
  $log = Join-Path $logDir ('startup-' + $key + '.log')
  $adapters = @{
    Runtime = { Read-Runtime }; Listener = { Read-Listener }; Health = { Read-Health }; Status = { Read-Status }
    Process = { param($ProcessId) Read-Process $ProcessId }; Stop = { param($ProcessId, $Identity) Stop-OwnedBridge $ProcessId $Identity }
    Backup = { [void](Backup-BridgeState $StateDirectory $config.WorkspaceId) }; Start = { Start-Bridge }
    Log = { param($Phase) Write-Phase $Phase }; Ssh = { param($Now) Ensure-Tunnel $Now }
  }
  Write-Phase 'supervisor-started'
  while ($true) {
    try { [void](Invoke-SupervisorTick $config $state $adapters ([datetime]::UtcNow.Ticks / 10000000)) } catch { Write-Phase 'probe-unavailable' }
    Start-Sleep -Seconds $PollSeconds
  }
} finally {
  # Only our SSH child is stopped on exit. A healthy bridge survives supervisor replacement.
  if ($tunnel -and -not $tunnel.HasExited) { $tunnel.Kill(); $tunnel.Dispose() }
  if ($lock) { $lock.ReleaseMutex(); $lock.Dispose() }
}
