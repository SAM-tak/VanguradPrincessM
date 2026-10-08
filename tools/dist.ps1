# Builds a fused, source-free distribution: the game compiled by the full
# lovec, zipped into a .love and appended to the VM-only shipping love.exe.
#
#   pwsh tools/dist.ps1 [-Love <lhat-love repo>] [-Jobs <count>] [-RebuildEngine] [-Run] [-IncludeAssets]
# Assets stay external by default. IncludeAssets is for private local builds.
#
# The VM-only engine only reads units written by the same build of lhat, so
# it is rebuilt when it is older than the full lovec (or with -RebuildEngine).
# It cannot parse text LTON either; --compile-game compiles every .lton.
#
# Output: dist/VanguardPrincess/ (exe + the engine's DLLs). Work files go to build/.
param(
    [string]$Love = "C:\Users\Owner\source\repos\lhat-love",
    [switch]$RebuildEngine,
    [switch]$Run,
    [switch]$IncludeAssets,
    [ValidateRange(0, 256)][int]$Jobs = 0 # 0: physical cores; 1: serial compilation
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

# Exercise the exact compiler and VM pair before copying assets or deleting
# the previous output. DLL timestamps alone cannot detect stale signatures.
& (Join-Path $PSScriptRoot "check.ps1") -Love $Love

$build = Join-Path $root "build"
$work = Join-Path $build "package"
$zip = Join-Path $build "VanguardPrincess.love"
$out = Join-Path $root "dist\VanguardPrincess"
# Validate the exact cleanup targets before recursively removing generated files.
function Clear-GeneratedDirectory([string]$Path, [string]$Parent) {
    $resolved = [IO.Path]::GetFullPath($Path)
    $expectedParent = [IO.Path]::GetFullPath($Parent).TrimEnd('\', '/')
    if ((Split-Path $resolved -Parent) -ine $expectedParent) { throw "Unsafe cleanup target: $resolved" }
    if (Test-Path -LiteralPath $resolved) {
        if ((Get-Item -LiteralPath $resolved -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Refusing to clean a linked directory: $resolved"
        }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
Clear-GeneratedDirectory $work $build
& (Join-Path $PSScriptRoot "package-game.ps1") -SourceRoot $root -Lovec $lovec -WorkDirectory $work -Archive $zip -Jobs $Jobs -IncludeAssets:$IncludeAssets

# Keep the previous distribution until compilation and archive creation succeed.
# Preserve user-extracted media across rebuilds. Clean only generated siblings.
if (Test-Path -LiteralPath $out) {
    $resolvedOut = [IO.Path]::GetFullPath($out)
    if ((Split-Path $resolvedOut -Parent) -ine [IO.Path]::GetFullPath((Join-Path $root 'dist'))) { throw 'Unsafe output directory' }
    if ((Get-Item -LiteralPath $out -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked output directory' }
    foreach ($item in Get-ChildItem -LiteralPath $out -Force) {
        if ($item.Name -eq 'assets') { continue }
        if ($item.PSIsContainer) { Clear-GeneratedDirectory $item.FullName $out }
        else { Remove-Item -LiteralPath $item.FullName -Force }
    }
}
New-Item -ItemType Directory -Force $out | Out-Null

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

# Portable media builder: no original game media or FM2K definitions included.
$builder = Join-Path $out 'asset-builder'
New-Item -ItemType Directory -Force "$builder/patches", "$builder/licenses" | Out-Null
$converter = Join-Path $root 'tools/fm2k_convert'
foreach ($file in 'build_assets.py', 'extract_original.py', 'raw_media.py', 'convert.py', 'share_assets.py', 'layout.py', 'names.py', 'assets-recipe.json', 'requirements.txt', 'ASSETS.md', 'patches/__init__.py', 'licenses/fm2ndparser.txt') {
    Copy-Item -LiteralPath (Join-Path $converter $file) -Destination (Join-Path $builder $file)
}
Copy-Item -LiteralPath (Join-Path $converter 'ASSETS.md') -Destination (Join-Path $out 'ASSETS.md')

$size = (Get-Item $exe).Length / 1MB
Write-Host ("done: {0} ({1:N1} MB)" -f $exe, $size)
if ($Run) { & $exe }
