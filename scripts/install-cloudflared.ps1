$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$bin = Join-Path $root "vendor\bin"
New-Item -ItemType Directory -Force -Path $bin | Out-Null
$target = Join-Path $bin "cloudflared.exe"
$url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
Write-Host "Downloading cloudflared to $target"
Invoke-WebRequest -Uri $url -OutFile $target
Write-Host "Installed $target"
