<#
.SYNOPSIS
  Install codex-chatgpt-bridge as a Codex plugin through a personal marketplace.
.DESCRIPTION
  Creates <PluginParent>\codex-chatgpt-bridge as a junction to this checkout (single
  source of truth, no copy drift), adds it to the personal marketplace at
  <Home>\.agents\plugins\marketplace.json, registers that marketplace in
  <CodexHome>\config.toml and enables the plugin. Idempotent.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File deploy\install-codex-plugin.ps1
#>
param(
  [string]$CodexHome = "$env:USERPROFILE\.codex",
  [string]$PluginParent = "$env:USERPROFILE\plugins",
  [string]$MarketplaceName = "personal",
  [switch]$KeepLooseSkills
)
$ErrorActionPreference = "Stop"
$nl = [Environment]::NewLine
function Step($m) { Write-Host ""; Write-Host "== $m" -ForegroundColor Cyan }
function Ok($m) { Write-Host "  [ok] $m" -ForegroundColor Green }

$repo = Split-Path -Parent $PSScriptRoot
$pluginName = "codex-chatgpt-bridge"
if (-not (Test-Path (Join-Path $repo ".codex-plugin\plugin.json"))) { throw "no .codex-plugin/plugin.json in $repo" }

Step "Linking $pluginName into the plugin parent"
New-Item -ItemType Directory -Force -Path $PluginParent | Out-Null
$link = Join-Path $PluginParent $pluginName
if (Test-Path $link) { Ok "already present: $link" } else {
  New-Item -ItemType Junction -Path $link -Target $repo | Out-Null
  Ok "junction: $link -> $repo"
}

Step "Writing the personal marketplace entry"
$marketplaceDir = Join-Path $env:USERPROFILE ".agents\plugins"
New-Item -ItemType Directory -Force -Path $marketplaceDir | Out-Null
$marketplaceFile = Join-Path $marketplaceDir "marketplace.json"
$entry = [ordered]@{
  name = $pluginName
  source = [ordered]@{ source = "local"; path = "./plugins/$pluginName" }
  policy = [ordered]@{ installation = "AVAILABLE"; authentication = "ON_INSTALL" }
  category = "Developer Tools"
}
if (Test-Path $marketplaceFile) {
  $manifest = Get-Content $marketplaceFile -Raw | ConvertFrom-Json
  $plugins = @($manifest.plugins | Where-Object { $_.name -ne $pluginName })
  $plugins += [pscustomobject]$entry
  $manifest.plugins = $plugins
  $manifest | ConvertTo-Json -Depth 8 | Set-Content $marketplaceFile -Encoding UTF8
  Ok "merged into existing marketplace ($marketplaceFile)"
} else {
  $manifest = [ordered]@{
    name = $MarketplaceName
    interface = [ordered]@{ displayName = "Personal" }
    plugins = @([pscustomobject]$entry)
  }
  $manifest | ConvertTo-Json -Depth 8 | Set-Content $marketplaceFile -Encoding UTF8
  Ok "created $marketplaceFile"
}

Step "Registering the marketplace and enabling the plugin"
$config = Join-Path $CodexHome "config.toml"
if (-not (Test-Path $config)) { throw "config not found: $config" }
Copy-Item $config ("$config.bak-plugin-" + (Get-Date -Format yyyyMMddHHmmss)) -Force
$text = Get-Content $config -Raw
if ($text -notmatch ("\[marketplaces\." + $MarketplaceName + "\]")) {
  Add-Content $config ($nl + "[marketplaces.$MarketplaceName]" + $nl + "source_type = ""local""" + $nl + "source = '" + $env:USERPROFILE + "'" + $nl) -Encoding UTF8
  Ok "added [marketplaces.$MarketplaceName]"
} else { Ok "marketplace already registered" }
$pluginHeader = "[plugins.""$pluginName@$MarketplaceName""]"
if ($text -notmatch [regex]::Escape($pluginHeader)) {
  Add-Content $config ($nl + $pluginHeader + $nl + "enabled = true" + $nl) -Encoding UTF8
  Ok "enabled $pluginName@$MarketplaceName"
} else { Ok "plugin already enabled" }

if (-not $KeepLooseSkills) {
  Step "Retiring loose skill copies (they now ship with the plugin)"
  $skills = Join-Path $CodexHome "skills"
  $backup = Join-Path $CodexHome ("skills-backup-" + (Get-Date -Format yyyyMMddHHmmss))
  $moved = 0
  foreach ($name in @("chatgpt-web-orchestrator","chatgpt-pro-analysis","chatgpt-deep-research","chatgpt-result-compress","codex-chatgpt-loop")) {
    $src = Join-Path $skills $name
    if (Test-Path $src) {
      if ($moved -eq 0) { New-Item -ItemType Directory -Force -Path $backup | Out-Null }
      Move-Item -LiteralPath $src -Destination $backup -Force
      $moved++
    }
  }
  if ($moved -gt 0) { Ok "moved $moved loose skill folder(s) to $backup" } else { Ok "no loose skill folders found" }
}

Write-Host ""
Write-Host "Restart the Codex app so it rescans marketplaces; the plugin list should show one entry: Codex ChatGPT Bridge."
