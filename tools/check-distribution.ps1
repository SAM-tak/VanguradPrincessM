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
$builder = if ($IsWindows) { 'BuildAssets.exe' } else { 'BuildAssets' }
$programs = @(
    $builder
    if ($IsWindows) { 'VanguardPrincess.exe' }
    elseif ($IsLinux) { 'VanguardPrincess', 'lib/liblove-12.0.so' }
    else { 'VanguardPrincess.command', 'lhat-love.app/Contents/MacOS/love' }
)
foreach ($name in @($programs) + @('ASSETS.md', 'LICENSE', 'lhat-love-license.txt') + @(if ($IsMacOS) { 'VanguardPrincess.love' })) {
    if (-not (Test-Path -LiteralPath (Join-Path $out $name) -PathType Leaf)) { throw "Missing distribution file: $name" }
}
if (-not $IsWindows) {
    foreach ($name in $programs | Where-Object { $_ -notlike 'lib/*' }) {
        $mode = [IO.File]::GetUnixFileMode((Join-Path $out $name))
        if (-not ($mode -band [IO.UnixFileMode]::UserExecute)) { throw "Not executable: $name" }
    }
}
if ($IsMacOS) {
    # The bundle must stay as signed; the game is beside it, not inside it.
    & codesign --verify --deep --strict (Join-Path $out 'lhat-love.app')
    if ($LASTEXITCODE -ne 0) { throw 'Engine bundle signature is broken' }
}
$savedPath = $env:PATH
$savedPythonPath = $env:PYTHONPATH
try {
    $env:PATH = if ($IsWindows) { "$env:SystemRoot\System32;$env:SystemRoot" } else { '/usr/bin:/bin' }
    $env:PYTHONPATH = ''
    & (Join-Path $out $builder) --help
    if ($LASTEXITCODE -ne 0) { throw 'Standalone builder failed' }
} finally {
    $env:PATH = $savedPath
    $env:PYTHONPATH = $savedPythonPath
}
Write-Host 'Distribution check passed'
