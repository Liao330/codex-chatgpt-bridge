<#
.SYNOPSIS
  Build distributable plugin packages for ChatGPT and Codex.
.DESCRIPTION
  Produces two layouts from the same sources:

    portable (recommended)  plugin.json + mcp.json + skills\ + assets\
    codex (compatibility)   .codex-plugin\plugin.json + .mcp.json + skills\ + assets\

  The root mcp.json and plugin.json are validated against the published Agent
  Plugins schemas, so a package that would be rejected on upload never leaves
  the machine. Only plugin payload is packed: no source, vendored packages,
  tests, docs or private state, and no credentials are ever written into a
  package.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\pack-plugin.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\pack-plugin.ps1 -McpUrl https://relay.example.ts.net/mcp
#>
param(
  [string]$McpUrl,
  [string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $repo 'dist' }
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$manifest = [IO.File]::ReadAllText((Join-Path $repo '.codex-plugin\plugin.json')) | ConvertFrom-Json
$name = $manifest.name
$version = $manifest.version
if (-not $name -or -not $version) { throw 'the manifest needs a name and a version' }

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
  & $python.Source (Join-Path $repo 'scripts\validate_plugin.py') $repo
  if ($LASTEXITCODE -ne 0) { throw 'plugin validation failed; fix the issues above before packing' }
}

# Cache the published schemas so later runs validate offline.
$schemaDir = Join-Path $OutputDirectory '_schema'
New-Item -ItemType Directory -Force -Path $schemaDir | Out-Null
foreach ($kind in @('plugin', 'mcp')) {
  $schemaPath = Join-Path $schemaDir ($kind + '.schema.json')
  if (-not (Test-Path $schemaPath)) {
    Invoke-WebRequest -Uri "https://agent-plugins.org/schemas/1.0.0/$kind.schema.json" -OutFile $schemaPath -UseBasicParsing
  }
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

function New-Staging([string]$Layout, [string[]]$Items) {
  $staging = Join-Path $OutputDirectory ('.staging-' + $Layout)
  if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
  New-Item -ItemType Directory -Force -Path $staging | Out-Null
  foreach ($item in $Items) {
    $source = Join-Path $repo $item
    if (-not (Test-Path $source)) { throw "the $Layout layout needs $item" }
    Copy-Item -Recurse -Force $source (Join-Path $staging $item)
  }
  return $staging
}

function Set-McpEndpoint([string]$Staging, [string]$ConfigName) {
  $configPath = Join-Path $Staging $ConfigName
  $config = [IO.File]::ReadAllText($configPath) | ConvertFrom-Json
  $servers = @($config.mcpServers.PSObject.Properties.Name)
  if ($servers.Count -ne 1) { throw "a plugin may declare exactly one MCP server; found $($servers.Count)" }
  if ($McpUrl) { $config.mcpServers.($servers[0]).url = $McpUrl }
  $url = $config.mcpServers.($servers[0]).url
  if ($url -notmatch '^https://[^\s]+/mcp$') { throw "the MCP url must be a public HTTPS endpoint ending in /mcp: $url" }
  [IO.File]::WriteAllText($configPath, ($config | ConvertTo-Json -Depth 10))
  return $url
}

function New-Zip([string]$Staging, [string]$Target) {
  # Windows PowerShell 5.1's Compress-Archive writes backslash separators, which
  # violates the ZIP specification (APPNOTE 4.4.17.1) and is rejected on upload.
  if (Test-Path $Target) { Remove-Item -Force $Target }
  $stream = [IO.File]::Open($Target, [IO.FileMode]::Create)
  $archive = New-Object IO.Compression.ZipArchive($stream, [IO.Compression.ZipArchiveMode]::Create)
  try {
    foreach ($file in (Get-ChildItem -LiteralPath $Staging -Recurse -File -Force | Sort-Object FullName)) {
      $entryName = $file.FullName.Substring($Staging.Length + 1).Replace('\', '/')
      $entry = $archive.CreateEntry($entryName, [IO.Compression.CompressionLevel]::Optimal)
      $entryStream = $entry.Open()
      $sourceStream = [IO.File]::OpenRead($file.FullName)
      try { $sourceStream.CopyTo($entryStream) } finally { $sourceStream.Dispose(); $entryStream.Dispose() }
    }
  } finally { $archive.Dispose(); $stream.Dispose() }
}

$packages = @()

# ---- portable: plugin.json + mcp.json + skills + assets --------------------
$portable = New-Staging 'portable' @('plugin.json', 'mcp.json', 'skills', 'assets')
$mcpUrl = Set-McpEndpoint $portable 'mcp.json'
if ($python) {
  & $python.Source (Join-Path $repo 'scripts\validate_package.py') $portable $schemaDir
  if ($LASTEXITCODE -ne 0) { throw 'the portable package failed schema validation' }
}
$portableZip = Join-Path $OutputDirectory ("$name-$version.zip")
New-Zip $portable $portableZip
$packages += $portableZip
$tar = Get-Command tar -ErrorAction SilentlyContinue
if ($tar) {
  $portableTar = Join-Path $OutputDirectory ("$name-$version.tar.gz")
  if (Test-Path $portableTar) { Remove-Item -Force $portableTar }
  & $tar.Source -czf $portableTar -C $portable 'plugin.json' 'mcp.json' 'skills' 'assets'
  if ($LASTEXITCODE -ne 0) { throw 'tar packaging failed' }
  $packages += $portableTar
}
Remove-Item -Recurse -Force $portable

# ---- codex compatibility: .codex-plugin + .mcp.json + skills + assets ------
$compat = New-Staging 'codex' @('.codex-plugin', '.mcp.json', 'skills', 'assets')
[void](Set-McpEndpoint $compat '.mcp.json')
$compatZip = Join-Path $OutputDirectory ("$name-$version-codex.zip")
New-Zip $compat $compatZip
$packages += $compatZip
Remove-Item -Recurse -Force $compat

Write-Host ""
Write-Host "Plugin     : $name $version"
Write-Host "MCP server : $mcpUrl"
Write-Host "Packages"
foreach ($file in $packages) { Write-Host ("  " + $file) }
