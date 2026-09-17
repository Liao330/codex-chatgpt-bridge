$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = "$root\src"
python -m compileall -q "$root\src"
python -m unittest discover -s "$root\tests" -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python "$root\scripts\run_upstream_tests.py"
exit $LASTEXITCODE
