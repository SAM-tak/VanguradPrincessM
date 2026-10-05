# Builds a fused, source-free distribution: the game compiled by the full
# lovec, zipped into a .love and appended to the VM-only shipping love.exe.
#
#   pwsh tools/dist.ps1 [-Love <lhat-love repo>] [-RebuildEngine] [-Run]
#
# The VM-only engine only reads units written by the same build of lhat, so
# it is rebuilt when it is older than the full lovec (or with -RebuildEngine).
# It cannot parse text LTON either; --compile-game compiles every .lton.
#
# Output: dist/VanguardPrincess/ (exe + the engine's DLLs). Work files go to build/.
param(
    [string]$Love = "C:\Users\Owner\source\repos\lhat-love",
    [switch]$RebuildEngine,
    [switch]$Run
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$lovec = Join-Path $Love "build\love\Release\lovec.exe"
$vm = Join-Path $Love "build-vmonly-shipping\love\Release"
if (-not (Test-Path $lovec)) { throw "missing $lovec" }
$vmDll = Join-Path $vm "love.dll"
$fullDll = Join-Path (Split-Path $lovec) "love.dll"
if ($RebuildEngine -or -not (Test-Path $vmDll) -or
    (Get-Item $vmDll).LastWriteTime -lt (Get-Item $fullDll).LastWriteTime) {
    Write-Host "building the VM-only shipping engine"
    & (Join-Path $Love "scripts\build.ps1") -VmOnly -Shipping
    if ($LASTEXITCODE -ne 0) { throw "engine build failed ($LASTEXITCODE)" }
}

$build = Join-Path $root "build"
$stage = Join-Path $build "stage"
$game = Join-Path $build "game"
$zip = Join-Path $build "VanguardPrincess.love"
$out = Join-Path $root "dist\VanguardPrincess"
foreach ($d in $stage, $game, $out) {
    if (Test-Path $d) { Remove-Item $d -Recurse -Force }
}
New-Item -ItemType Directory -Force $stage, $out | Out-Null

# Only what the game reads: leave out tools/, the donor and the docs, and the
# converter's intermediate data (old skills/, data/_conversion/, data.lton), which
# the game never opens and which --compile-game would spend minutes on.
Write-Host "staging"
foreach ($item in "main.lh", "conf.lton") {
    Copy-Item (Join-Path $root $item) $stage
}
foreach ($item in "src", "assets", "data") {
    # Numbered skill exports and normalized conversion inputs are not runtime assets.
    robocopy (Join-Path $root $item) (Join-Path $stage $item) /E /XD skills _conversion /XF data.lton support-source.lton /NFL /NDL /NJH /NJS /NP /MT:16 | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "copying $item failed ($LASTEXITCODE)" }
}

Write-Host "compiling"
& $lovec --compile-game $game $stage
if ($LASTEXITCODE -ne 0) { throw "--compile-game failed ($LASTEXITCODE)" }

Write-Host "zipping"
if (Test-Path $zip) { Remove-Item $zip -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($game, $zip)

Write-Host "fusing"
$exe = Join-Path $out "VanguardPrincess.exe"
$fs = [System.IO.File]::Create($exe)
try {
    foreach ($part in (Join-Path $vm "love.exe"), $zip) {
        $in = [System.IO.File]::OpenRead($part)
        try { $in.CopyTo($fs) } finally { $in.Dispose() }
    }
} finally { $fs.Dispose() }
Copy-Item (Join-Path $vm "*.dll") $out

$size = (Get-Item $exe).Length / 1MB
Write-Host ("done: {0} ({1:N1} MB)" -f $exe, $size)
if ($Run) { & $exe }
