$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = "$root\src;$env:PYTHONPATH"
$pythonRuntime = Join-Path $root '.venv-http\Scripts\python.exe'
if (Test-Path -LiteralPath $pythonRuntime) { & $pythonRuntime -m ccw @args }
else { python -m ccw @args }
exit $LASTEXITCODE
