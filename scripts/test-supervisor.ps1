# Isolated policy tests and real Windows primitive checks; never uses production state or ports.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'bridge-supervisor.ps1')
$script:count = 0
function Check([bool]$Condition, [string]$Name) {
  if (-not $Condition) { throw ('FAIL: ' + $Name) }
  $script:count++; Write-Host ('PASS: ' + $Name)
}
$config = @{ Workspace = 'C:\isolated workspace'; WorkspaceId = 'isolated'; LocalPort = 32123; CliEntry = 'C:\isolated repo\dist\cli\index.js'; FailureThreshold = 3; InitialBackoffSeconds = 10; MaxBackoffSeconds = 300 }
function Reset-Fixture {
  $script:fixture = @{
    runtime = @{ pid = 54321; port = 32123; workspaceRoot = $config.Workspace; workspaceId = 'isolated'; startedAt = '2026-10-02T01:00:01Z' }
    process = [pscustomobject]@{ ProcessId = 54321; CreationDate = [datetime]'2026-10-02T01:00:00Z'; CommandLine = '"C:\node.exe" "C:\isolated repo\dist\cli\index.js" serve --workspace "C:\isolated workspace"' }
    listener = @(54321); health = @{ status = 'ok'; workspaceId = 'isolated' }
    status = @{ ok = $true; running = $true; pid = 54321; port = 32123; workspaceId = 'isolated'; workspaceRoot = $config.Workspace }
    starts = 0; stops = 0; backups = 0; ssh = 0; changed = $false; failBackup = $false
  }
  $script:adapters = @{
    Runtime = { $fixture.runtime }; Listener = { $fixture.listener }; Health = { $fixture.health }; Status = { $fixture.status }
    Process = { param($ProcessId)
      if ($fixture.changed) { $copy = $fixture.process.PSObject.Copy(); $copy.CreationDate = $copy.CreationDate.AddSeconds(1); return $copy }
      $fixture.process
    }
    Backup = { $fixture.backups++; if ($fixture.failBackup) { throw 'backup-failed' } }
    Stop = { param($ProcessId, $Identity) $fixture.stops++; $fixture.listener = @(); $fixture.process = $null }
    Start = { $fixture.starts++ }; Ssh = { param($Now) $fixture.ssh++ }; Log = { param($Reason) }
  }
  $script:state = New-SupervisorState
}
function Tick([double]$Now = 0) { Invoke-SupervisorTick $config $state $adapters $Now }
Reset-Fixture
Check ((Tick) -eq 'healthy' -and $state.Owned -and $fixture.starts -eq 0) 'healthy repo daemon adopted only with admin, listener and runtime agreement'
$fixture.runtime = $null; $fixture.process = $null; $fixture.listener = @(); $fixture.health = $null; $fixture.status = $null
[void](Tick 1); [void](Tick 2); [void](Tick 3)
Check ($fixture.starts -eq 1 -and $fixture.ssh -eq 4) 'bridge crash recovered while SSH remains alive'
Reset-Fixture
[void](Tick); $fixture.status = $null; [void](Tick 1); $fixture.status = @{ ok = $true; running = $true; pid = 54321; port = 32123; workspaceId = 'isolated'; workspaceRoot = $config.Workspace }; [void](Tick 2)
Check ($fixture.stops -eq 0 -and $fixture.starts -eq 0) 'single transient admin failure tolerated'
Reset-Fixture
$fixture.status = $null
[void](Tick); [void](Tick 1); [void](Tick 2)
Check ($fixture.stops -eq 0 -and $fixture.starts -eq 0) 'admin 404 or timeout without prior ownership fails closed'
Reset-Fixture
$fixture.process.CommandLine = 'node.exe C:\other\index.js serve --workspace C:\isolated'
[void](Tick); [void](Tick 1); [void](Tick 2)
Check ($fixture.stops -eq 0 -and $fixture.starts -eq 0) 'foreign listener never killed or replaced'
Reset-Fixture
[void](Tick); $fixture.status = $null; [void](Tick 1); [void](Tick 2); [void](Tick 3)
Check ($fixture.stops -eq 1 -and $fixture.starts -eq 1 -and $fixture.backups -eq 1) 'previously proven identity recovers after sustained admin failure'
Reset-Fixture
[void](Tick); $fixture.status = $null; $fixture.changed = $true; [void](Tick 1); [void](Tick 2); [void](Tick 3)
Check ($fixture.stops -eq 0 -and $fixture.starts -eq 0) 'PID reuse with new creation time never authorizes stop'
Reset-Fixture
[void](Tick); $fixture.status = $null
$adapters.Backup = { $fixture.backups++; $fixture.changed = $true }
[void](Tick 1); [void](Tick 2); [void](Tick 3)
Check ($fixture.stops -eq 0 -and $fixture.starts -eq 0) 'identity checked again after backup before stop'
Reset-Fixture
$fixture.runtime.port = 12345; [void](Tick); [void](Tick 1); [void](Tick 2)
Check ($fixture.stops -eq 0 -and $fixture.starts -eq 0 -and $state.LastReason -eq 'port-mismatch') 'mismatched runtime port rejected'
Reset-Fixture
[void](Tick); $fixture.status = $null; $fixture.failBackup = $true; [void](Tick 1); [void](Tick 2); [void](Tick 3)
Check ($fixture.stops -eq 0 -and $fixture.starts -eq 0) 'backup failure leaves owned bridge intact'
Reset-Fixture
$fixture.runtime = $null; $fixture.process = $null; $fixture.listener = @(); $fixture.health = $null; $fixture.status = $null
[void](Tick 0); [void](Tick 1); [void](Tick 2); [void](Tick 3); [void](Tick 11)
Check ($fixture.starts -eq 1 -and $state.NextAttempt -eq 12) 'failed recovery respects initial backoff'
[void](Tick 12); [void](Tick 13); [void](Tick 31)
Check ($fixture.starts -eq 2 -and $state.NextAttempt -eq 32) 'repeated failure increases backoff'
[void](Tick 32)
Check ($fixture.starts -eq 3 -and $state.NextAttempt -eq 72) 'restart attempts remain bounded by exponential backoff'
Reset-Fixture
$adapters.Listener = { throw 'listener-query-unavailable' }
$caught = $false; try { [void](Tick) } catch { $caught = $true }
Check ($caught -and $fixture.starts -eq 0 -and $fixture.stops -eq 0 -and $fixture.ssh -eq 1) 'listener query uncertainty fails closed and still checks SSH'
Reset-Fixture
$fixture.process.CommandLine += '-different-root'
Check (-not (Test-BridgeCommand $fixture.process $config)) 'workspace substring cannot adopt foreign root'
Reset-Fixture
$fixture.process.CommandLine += ' --port 32123'
Check (Test-BridgeCommand $fixture.process $config) 'explicit matching serve port accepted'
$fixture.process.CommandLine = $fixture.process.CommandLine.Replace('32123', '32124')
Check (-not (Test-BridgeCommand $fixture.process $config)) 'wrong serve port rejected'
Reset-Fixture
$fixture.runtime.startedAt = '2026-10-01T01:00:01Z'; [void](Tick)
Check (-not $state.Owned) 'stale runtime timestamp cannot authorize PID adoption'
Reset-Fixture
$child = [pscustomobject]@{ Id = 54321; HasExited = $false }
$childAdapters = $adapters.Clone(); $childAdapters.Delay = { }
$fixture.runtime.port = 44444
$caught = $false; try { Wait-SupervisedChild $child (Get-BridgeIdentity $fixture.process) $config $childAdapters 1 } catch { $caught = $true }
Check ($caught -and $fixture.stops -eq 1) 'fresh child random-port fallback is stopped using its exact identity'
Reset-Fixture
$childAdapters = $adapters.Clone(); $childAdapters.Delay = { }; $fixture.runtime.port = 44444
$oldIdentity = Get-BridgeIdentity $fixture.process; $fixture.changed = $true
$caught = $false; try { Wait-SupervisedChild $child $oldIdentity $config $childAdapters 1 } catch { $caught = $true }
Check ($caught -and $fixture.stops -eq 0) 'startup failure cleanup also refuses a reused child PID'
Reset-Fixture
$childAdapters = $adapters.Clone(); $childAdapters.Delay = { }
Wait-SupervisedChild $child (Get-BridgeIdentity $fixture.process) $config $childAdapters 1
Check ($fixture.stops -eq 0) 'port-confirmed child stays running'
# Real primitives operate only on isolated temporary data and short-lived subprocesses.
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('c2c-supervisor-test-' + [guid]::NewGuid().ToString('N'))
[void](New-Item -ItemType Directory -Path $tempRoot)
try {
  $helper = Join-Path $PSScriptRoot 'bridge-supervisor.ps1'
  $key = Get-SupervisorKey $tempRoot 32123
  $held = Enter-SupervisorLock $key
  try {
    $command = '. ''' + $helper.Replace("'", "''") + '''; $lock = Enter-SupervisorLock ''' + $key + '''; if ($lock) { $lock.ReleaseMutex(); $lock.Dispose(); Write-Output ''duplicate'' } else { Write-Output ''blocked'' }'
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
    $result = Invoke-BoundedProcess (Get-Command powershell.exe).Source ('-NoProfile -EncodedCommand ' + $encoded) '' 10
    Check ($held -and $result.Trim() -eq 'blocked') 'second process cannot acquire same workspace-port supervisor lock'
  } finally { if ($held) { $held.ReleaseMutex(); $held.Dispose() } }
  $held = Enter-SupervisorLock $key
  Check ($null -ne $held) 'supervisor lock released for replacement'
  $held.ReleaseMutex(); $held.Dispose()
  $before = $env:C2C_STATE_DIR
  $timer = [Diagnostics.Stopwatch]::StartNew()
  $result = Invoke-BoundedProcess (Get-Command powershell.exe).Source '-NoProfile -Command "Start-Sleep -Seconds 10"' $tempRoot 1
  Check ($null -eq $result -and $timer.Elapsed.TotalSeconds -lt 5 -and $env:C2C_STATE_DIR -eq $before) 'CLI timeout bounded and child environment does not mutate parent state'
  foreach ($kind in @('auth', 'runtime')) {
    [void](New-Item -ItemType Directory -Path (Join-Path $tempRoot $kind))
    Set-Content -LiteralPath (Join-Path $tempRoot ($kind + '\isolated.json')) -Value '{"test":"preserved"}'
  }
  $original = (Get-FileHash -LiteralPath (Join-Path $tempRoot 'auth\isolated.json')).Hash
  $backup = Backup-BridgeState $tempRoot 'isolated'
  Check ((Get-FileHash -LiteralPath (Join-Path $backup 'auth.json')).Hash -eq $original -and (Get-FileHash -LiteralPath (Join-Path $tempRoot 'auth\isolated.json')).Hash -eq $original) 'secure backup copies authorization without modifying source'
  $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
  foreach ($path in @($backup, (Join-Path $backup 'auth.json'), (Join-Path $backup 'runtime.json'))) {
    $acl = Get-Acl -LiteralPath $path
    $rules = @($acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]))
    Check ($acl.AreAccessRulesProtected -and $rules.Count -eq 1 -and $rules[0].IdentityReference.Value -eq $sid) 'backup ACL grants only current user'
  }
} finally {
  # The target is a generated, verified direct child of the system temporary directory.
  $resolved = [IO.Path]::GetFullPath($tempRoot)
  $parent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
  if ((Split-Path -Parent $resolved) -eq $parent -and (Split-Path -Leaf $resolved) -like 'c2c-supervisor-test-*') { Remove-Item -LiteralPath $resolved -Recurse -Force }
}
Write-Host ('Supervisor checks passed: ' + $script:count)
