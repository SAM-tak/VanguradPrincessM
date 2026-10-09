# Download the pinned release binaries without requiring an engine checkout.
param(
    [string]$Destination = (Join-Path (Split-Path $PSScriptRoot -Parent) 'build/release-engine'),
    [string]$Platform
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'engine-platform.ps1')
if (-not $Platform) { $Platform = Get-EnginePlatform }
$release = Get-Content -Raw (Join-Path $PSScriptRoot 'engine-release.json') | ConvertFrom-Json
$assets = $release.platforms.$Platform
if (-not $assets) { throw "No engine release is pinned for $Platform" }
if (Test-Path -LiteralPath $Destination) { throw "Destination must be new: $Destination" }
New-Item -ItemType Directory -Path $Destination | Out-Null
foreach ($kind in 'compiler', 'runtime') {
    $asset = $assets.$kind
    $archive = Join-Path $Destination $asset.asset
    $url = "https://github.com/$($release.repository)/releases/download/$($release.tag)/$($asset.asset)"
    Write-Host "Downloading $url"
    Invoke-WebRequest -Uri $url -OutFile $archive
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ine $asset.sha256) {
        throw "SHA256 mismatch: $($asset.asset)"
    }
    $target = Join-Path $Destination $kind
    if ($asset.asset.EndsWith('.zip')) {
        Expand-Archive -LiteralPath $archive -DestinationPath $target
    } else {
        # tar keeps the executable bits and the signed .app bundle intact.
        New-Item -ItemType Directory -Path $target | Out-Null
        & tar -xzf $archive -C $target --strip-components=1
        if ($LASTEXITCODE -ne 0) { throw "Could not extract $($asset.asset)" }
    }
}
$required = @(
    Get-EngineExecutable (Join-Path $Destination 'compiler') -Compiler
    Get-EngineExecutable (Join-Path $Destination 'runtime')
    if ($IsWindows) { Join-Path $Destination 'runtime/love.dll' }
)
foreach ($file in $required) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Missing release binary: $file"
    }
}
