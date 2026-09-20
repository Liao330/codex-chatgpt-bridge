<#
.SYNOPSIS
  Install the bridge skills into the Codex home so every Codex session can use them.
.DESCRIPTION
  Copies skills/* into <CodexHome>\skills and rewrites the repo-relative
  ".\ccw.cmd" references to this checkout, because global skills run from
  arbitrary repositories. Idempotent.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File deploy\install-codex-skills.ps1
#>
param([string]$CodexHome = "$env:USERPROFILE\.codex")

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$src = Join-Path $repo "skills"
$cli = Join-Path $repo "ccw.cmd"
if (-not (Test-Path $src)) { throw "skills folder not found: $src" }

foreach ($dir in Get-ChildItem $src -Directory) {
  $skill = Join-Path $dir.FullName "SKILL.md"
  if (-not (Test-Path $skill)) { continue }
  $dst = Join-Path $CodexHome ("skills\" + $dir.Name)
  New-Item -ItemType Directory -Force -Path $dst | Out-Null
  (Get-Content $skill -Raw).Replace(".\ccw.cmd", $cli) | Set-Content (Join-Path $dst "SKILL.md") -Encoding UTF8
  Get-ChildItem $dir.FullName -File | Where-Object { $_.Name -ne "SKILL.md" } | ForEach-Object {
    Copy-Item $_.FullName $dst -Force
  }
  Write-Host "[ok] $($dir.Name) -> $dst"
}
Write-Host ""
Write-Host "Next: add the trigger policy to $CodexHome\AGENTS.md (see docs/deployment.md)."
