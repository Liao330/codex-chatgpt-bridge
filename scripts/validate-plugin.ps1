$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
python "$root\scripts\validate_plugin.py" $root
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$systemValidator = Join-Path $HOME ".codex\skills\.system\plugin-creator\scripts\validate_plugin.py"
if (Test-Path $systemValidator) {
    python $systemValidator $root
}
exit $LASTEXITCODE
