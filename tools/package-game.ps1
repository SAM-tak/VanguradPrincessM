# Compile scripts/data; optionally stream media for private local builds.
# WorkDirectory must be new so stale compiled files cannot enter the package.
param(
    [Parameter(Mandatory)][string]$SourceRoot,
    [Parameter(Mandatory)][string]$Lovec,
    [Parameter(Mandatory)][string]$WorkDirectory,
    [Parameter(Mandatory)][string]$Archive,
    [ValidateRange(0, 256)][int]$Jobs = 0,
    [switch]$IncludeAssets
)
$ErrorActionPreference = 'Stop'
$SourceRoot = (Resolve-Path -LiteralPath $SourceRoot).Path
$Lovec = (Resolve-Path -LiteralPath $Lovec).Path
$WorkDirectory = [IO.Path]::GetFullPath($WorkDirectory)
$Archive = [IO.Path]::GetFullPath($Archive)
if (Test-Path -LiteralPath $WorkDirectory) { throw "Package work directory already exists: $WorkDirectory" }
$stage = Join-Path $WorkDirectory 'source'
$compiled = Join-Path $WorkDirectory 'compiled'
# Keep the same selection as dist.ps1's former robocopy /XD and /XF rules.
function Get-PackageFiles([string]$Directory) {
    $included = 0
    foreach ($item in Get-ChildItem -LiteralPath $Directory -Force) {
        if ($item.PSIsContainer) {
            if ($item.Name -notin @('skills', '_conversion')) {
                $included++
                Get-PackageFiles $item.FullName
            }
        } elseif ($item.Name -notin @('data.lton', 'support-source.lton')) {
            $included++
            $item
        }
    }
    # Preserve empty directories, including parents left empty by exclusions.
    if ($included -eq 0) { Get-Item -LiteralPath $Directory }
}
$files = @(
    Get-Item -LiteralPath (Join-Path $SourceRoot 'main.lh'), (Join-Path $SourceRoot 'conf.lton')
    foreach ($folder in 'src', 'data') { Get-PackageFiles (Join-Path $SourceRoot $folder) }
    if ($IncludeAssets) { Get-PackageFiles (Join-Path $SourceRoot 'assets') }
)
$entries = @($files | ForEach-Object {
    [pscustomobject]@{
        File = $_.FullName
        Name = [IO.Path]::GetRelativePath($SourceRoot, $_.FullName).Replace('\', '/') + $(if ($_.PSIsContainer) { '/' })
        Directory = $_.PSIsContainer
        Compile = -not $_.PSIsContainer -and $_.Extension -cin @('.lh', '.lton')
    }
})
$timer = [Diagnostics.Stopwatch]::StartNew()
New-Item -ItemType Directory -Path $stage -Force | Out-Null
foreach ($entry in $entries | Where-Object Compile) {
    $target = Join-Path $stage $entry.Name
    New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
    Copy-Item -LiteralPath $entry.File -Destination $target
}
Write-Host ("staged scripts/data only: {0:N2}s" -f $timer.Elapsed.TotalSeconds)
$timer.Restart()
& $Lovec --no-error-screen --compile-game $compiled --jobs $Jobs $stage
if ($LASTEXITCODE -ne 0) { throw "--compile-game failed ($LASTEXITCODE)" }
Write-Host ("compiled: {0:N2}s" -f $timer.Elapsed.TotalSeconds)

# Every source must have a compiled replacement; never fall back to source text.
foreach ($entry in $entries | Where-Object Compile) {
    $entry.File = Join-Path $compiled $entry.Name
    if (-not (Test-Path -LiteralPath $entry.File -PathType Leaf)) {
        throw "Missing compiled file: $($entry.Name)"
    }
}
$timer.Restart()
Add-Type -AssemblyName System.IO.Compression.FileSystem
New-Item -ItemType Directory -Path (Split-Path $Archive) -Force | Out-Null
$temporary = $Archive + '.' + [guid]::NewGuid().ToString('N') + '.tmp'
try {
    $zip = [IO.Compression.ZipFile]::Open($temporary, [IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($entry in $entries) {
            if ($entry.Directory) { $zip.CreateEntry($entry.Name) | Out-Null; continue }
            [IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $zip, $entry.File, $entry.Name, [IO.Compression.CompressionLevel]::Optimal) | Out-Null
        }
    } finally { $zip.Dispose() }
    Move-Item -LiteralPath $temporary -Destination $Archive -Force
} finally {
    if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
}
Write-Host ("archived {0} entries directly: {1:N2}s" -f $entries.Count, $timer.Elapsed.TotalSeconds)
