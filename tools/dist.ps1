# Builds a fused, source-free distribution: the game compiled by the full
# lovec, zipped into a .love and appended to the VM-only shipping love.exe.
#
#   pwsh tools/dist.ps1 [-Love <lhat-love repo>] [-Jobs <count>] [-RebuildEngine] [-Run]
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
& (Join-Path $PSScriptRoot "package-game.ps1") -SourceRoot $root -Lovec $lovec -WorkDirectory $work -Archive $zip -Jobs $Jobs

# Keep the previous distribution until compilation and archive creation succeed.
Clear-GeneratedDirectory $out (Join-Path $root 'dist')
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

$size = (Get-Item $exe).Length / 1MB
Write-Host ("done: {0} ({1:N1} MB)" -f $exe, $size)
if ($Run) { & $exe }
