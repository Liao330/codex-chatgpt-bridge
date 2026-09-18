$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$vendor = Join-Path $root "vendor\codex-with-chatgpt"
$env:PYTHONPATH = "$root\src"
python -m ccw c2c detect
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Push-Location $vendor
try {
    corepack pnpm test
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
