param([string]$Engine = "C:/Users/Owner/source/repos/lhat-love/build/love/Release/lovec.exe")
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$entry = Join-Path $root '.async-flow-test.lh'
if (Test-Path -LiteralPath $entry) { throw "Test entry already exists: $entry" }
# The test lives under tests/, but LOVE must mount the game root for assets.
$source = [IO.File]::ReadAllText((Join-Path $root 'tests/async-flow.lh'))
[IO.File]::WriteAllText($entry, $source.Replace('require^"../', 'require^"'))
try {
    Push-Location $root
    & $Engine --no-error-screen $entry
    $result = $LASTEXITCODE
    Write-Host "lovec exit code: $result"
} finally {
    Pop-Location
    Remove-Item -LiteralPath $entry
}
exit $result
