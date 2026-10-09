# Download the pinned release binaries without requiring an engine checkout.
param([string]$Destination = (Join-Path (Split-Path $PSScriptRoot -Parent) 'build/release-engine'))
$ErrorActionPreference = 'Stop'
$release = Get-Content -Raw (Join-Path $PSScriptRoot 'engine-release.json') | ConvertFrom-Json
if (Test-Path -LiteralPath $Destination) { throw "Destination must be new: $Destination" }
New-Item -ItemType Directory -Path $Destination | Out-Null
foreach ($kind in 'compiler', 'runtime') {
    $asset = $release.windows.$kind
    $zip = Join-Path $Destination $asset.asset
    $url = "https://github.com/$($release.repository)/releases/download/$($release.tag)/$($asset.asset)"
    Write-Host "Downloading $url"
    Invoke-WebRequest -Uri $url -OutFile $zip
    if ((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash -ine $asset.sha256) {
        throw "SHA256 mismatch: $($asset.asset)"
    }
    Expand-Archive -LiteralPath $zip -DestinationPath (Join-Path $Destination $kind)
}
foreach ($file in 'compiler/lovec.exe', 'runtime/love.exe', 'runtime/love.dll') {
    if (-not (Test-Path -LiteralPath (Join-Path $Destination $file) -PathType Leaf)) {
        throw "Missing release binary: $file"
    }
}
