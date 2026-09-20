<#
.SYNOPSIS
  One-click setup for codex-chatgpt-bridge on a machine that runs a bridge.
.DESCRIPTION
  Runs the two installers in order:
    deploy\install-client.ps1        bridge + logon supervisor + relay check
    deploy\install-codex-plugin.ps1  Codex plugin (five skills) + marketplace wiring
  Both are idempotent, so re-running is safe.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File deploy\install.ps1 -WorkspacePath E:\github_code
#>
param(
  [Parameter(Mandatory = $true)][string]$WorkspacePath,
  [string]$SshTarget = "c2c-relay",
  [int]$RemotePort = 8081,
  [int]$LocalPort = 48765
)
$ErrorActionPreference = "Stop"

Write-Host "=== 1/2  bridge, supervisor and relay tunnel ===" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "install-client.ps1") -WorkspacePath $WorkspacePath -SshTarget $SshTarget -RemotePort $RemotePort -LocalPort $LocalPort

Write-Host ""
Write-Host "=== 2/2  Codex plugin (five skills) ===" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "install-codex-plugin.ps1")

Write-Host ""
Write-Host "Done. Remaining manual steps (once per ChatGPT account):" -ForegroundColor Cyan
Write-Host "  1. create the connector: https://chatgpt.com/plugins#settings/Connectors?create-connector=true&redirectAfter=%2Fplugins"
Write-Host "     name: Codex with ChatGPT - <workspace name> | Server URL: https://<relay>.<tailnet>.ts.net/mcp | Auth: OAuth"
Write-Host "  2. press Connect, then run: ccw.cmd c2c exec -- pair -w <workspace> --json  (type the code on the page)"
Write-Host "  3. bind a Project: ccw.cmd c2c exec -- session set -w <workspace> --connector-name <name> --mode project --project-url <project url>"
Write-Host "  4. restart the Codex app so it picks up the plugin."
