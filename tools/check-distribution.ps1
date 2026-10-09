# Validate the public, media-free archive and exercise the frozen builder.
param([string]$DistributionDirectory)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::OpenRead((Join-Path $root 'build/VanguardPrincess.love'))
try {
    foreach ($entry in $archive.Entries) {
        if ($entry.FullName -match '(^assets/|(^|/)(_conversion|skills)/|(^|/)(data|support-source)\.lton$|NotoSansMonoCJKjp-Regular\.otf$)') {
            throw "Unexpected distribution entry: $($entry.FullName)"
        }
    }
} finally { $archive.Dispose() }
$out = if ($DistributionDirectory) { $DistributionDirectory } else { Join-Path $root 'dist/VanguardPrincess' }
if (Test-Path -LiteralPath (Join-Path $out 'assets')) { throw 'Public distribution contains external assets' }
foreach ($name in 'VanguardPrincess.exe', 'BuildAssets.exe', 'ASSETS.md', 'LICENSE', 'lhat-love-license.txt') {
    if (-not (Test-Path -LiteralPath (Join-Path $out $name) -PathType Leaf)) { throw "Missing distribution file: $name" }
}
$savedPath = $env:PATH
$savedPythonPath = $env:PYTHONPATH
try {
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $env:PYTHONPATH = ''
    & (Join-Path $out 'BuildAssets.exe') --help
    if ($LASTEXITCODE -ne 0) { throw 'Standalone builder failed' }
} finally {
    $env:PATH = $savedPath
    $env:PYTHONPATH = $savedPythonPath
}
Write-Host 'Distribution check passed'
