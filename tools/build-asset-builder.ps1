# Build in an isolated environment; Python is required only on the build machine.
param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$venv = Join-Path $root 'build/asset-builder-venv'
$interpreter = Join-Path $venv 'Scripts/python.exe'
if (-not (Test-Path -LiteralPath $interpreter)) {
    & $Python -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create asset builder environment' }
}
& $interpreter -m pip install -r (Join-Path $root 'tools/fm2k_convert/requirements-build.txt')
if ($LASTEXITCODE -ne 0) { throw 'Failed to install asset builder dependencies' }
& $interpreter (Join-Path $root 'tools/fm2k_convert/freeze_builder.py')
if ($LASTEXITCODE -ne 0) { throw 'Failed to freeze asset builder' }
