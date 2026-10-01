param(
  [Parameter(Mandatory = $true)][string]$WorkspacePath,
  [string]$StateDirectory = (Join-Path $env:LOCALAPPDATA 'codex-with-chatgpt'),
  [string]$SshTarget = 'c2c-relay',
  [int]$RemotePort = 8081,
  [int]$LocalPort = 48765
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$supervisor = Join-Path $repo 'scripts\startup.ps1'
. (Join-Path $repo 'scripts\bridge-supervisor.ps1')
$WorkspacePath = (Resolve-Path -LiteralPath $WorkspacePath).ProviderPath
$StateDirectory = [IO.Path]::GetFullPath($StateDirectory)
foreach ($value in @($WorkspacePath, $StateDirectory, $SshTarget, $supervisor)) {
  if ($value -match '["\r\n]') { throw 'Unsupported characters in installer option.' }
}
if ($SshTarget.StartsWith('-') -or $LocalPort -lt 1 -or $LocalPort -gt 65535 -or $RemotePort -lt 1 -or $RemotePort -gt 65535) { throw 'Invalid installer options.' }
foreach ($tool in @('node', 'python', 'ssh')) {
  if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "$tool is not on PATH" }
}
$ssh = (Get-Command ssh).Source
$probe = Invoke-BoundedProcess $ssh ('-o BatchMode=yes -o ConnectTimeout=10 "' + $SshTarget + '" "echo relay-ok"') '' 15
if (-not $probe -or $probe.Trim() -ne 'relay-ok') { throw 'Relay key-authentication probe failed.' }
$node = (Get-Command node).Source
$cli = Join-Path $repo 'vendor\codex-with-chatgpt\dist\cli\index.js'
$identity = Invoke-BoundedProcess $node ('"' + $cli + '" workspace --workspace "' + $WorkspacePath + '" --json') $StateDirectory 10
if (-not $identity) { throw 'Workspace identity unavailable; build the bridge first.' }
$WorkspacePath = ($identity | ConvertFrom-Json).root
$arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $supervisor + '" -WorkspacePath "' + $WorkspacePath + '" -StateDirectory "' + $StateDirectory + '" -SshTarget "' + $SshTarget + '" -RemotePort ' + $RemotePort + ' -LocalPort ' + $LocalPort
$startupDir = [Environment]::GetFolderPath('Startup')
$vbsPath = Join-Path $startupDir 'codex-chatgpt-bridge.vbs'
$vbs = 'Set sh = CreateObject("WScript.Shell")' + "`r`n" + 'sh.Run "powershell.exe ' + $arguments.Replace('"', '""') + '", 0, False' + "`r`n"
Set-Content -LiteralPath $vbsPath -Value $vbs -Encoding Unicode
# Require the exact launcher invocation, including repo, workspace and state directory.
$expected = 'powershell.exe ' + $arguments
$running = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object {
  $_.CommandLine -eq $expected -or $_.CommandLine -eq ('"' + (Get-Command powershell.exe).Source + '" ' + $arguments)
})
if ($running.Count -eq 0) {
  $child = Start-Process -FilePath 'powershell.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
  Write-Host ('Supervisor launched (pid {0}). Check its phase log for healthy or untrusted-state.' -f $child.Id)
} else { Write-Host 'Matching supervisor already running.' }
Write-Host 'Logon entry installed with explicit StateDirectory. Existing uncertain supervisors are never terminated by this installer.'
Write-Host ('For CLI operations use this same state directory in that CLI session: ' + $StateDirectory)
Write-Host 'Keep the existing ChatGPT connector and project binding. Reconnect only if its authorization has expired or was revoked.'
