$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = "$root\src"
python -m compileall -q "$root\src"
python -m unittest discover -s "$root\tests" -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python "$root\scripts\run_upstream_tests.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($env:OS -eq 'Windows_NT') {
  powershell -NoProfile -ExecutionPolicy Bypass -File "$root\scripts\test-supervisor.ps1"
  exit $LASTEXITCODE
}
Write-Host 'SKIP: Windows supervisor checks require Windows.'
exit 0
