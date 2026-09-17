$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = "$root\src;$env:PYTHONPATH"
python -m ccw @args
exit $LASTEXITCODE
