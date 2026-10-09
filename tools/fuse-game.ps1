# Make a compiled .love runnable with the VM-only engine and print the launcher.
# Windows and Linux append the archive to the engine executable (fused).
# macOS keeps the signed engine bundle untouched, since appending would break
# its signature, and a launcher starts it with --fused on the archive instead.
# Either way the game's source base is OutputDirectory, so external assets go
# next to the launcher.
param(
    [Parameter(Mandatory)][string]$ShippingDirectory,
    [Parameter(Mandatory)][string]$Archive,
    [Parameter(Mandatory)][string]$OutputDirectory,
    [string]$Name = 'VanguardPrincess'
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'engine-platform.ps1')
$vm = Get-EngineExecutable $ShippingDirectory
New-Item -ItemType Directory -Force $OutputDirectory | Out-Null

function Join-Files([string[]]$Parts, [string]$Target) {
    $fs = [IO.File]::Create($Target)
    try {
        foreach ($part in $Parts) {
            $in = [IO.File]::OpenRead($part)
            try { $in.CopyTo($fs) } finally { $in.Dispose() }
        }
    } finally { $fs.Dispose() }
}
# Replace an engine directory from a previous run instead of nesting into it.
function Copy-EngineDirectory([string]$Source) {
    $target = Join-Path $OutputDirectory (Split-Path $Source -Leaf)
    if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
    # cp/ditto keep executable bits, and ditto the bundle's signature layout.
    if ($IsMacOS) { & ditto $Source $target } else { & cp -Rp $Source $target }
    if ($LASTEXITCODE -ne 0) { throw "Could not copy $Source" }
}

if ($IsWindows) {
    $launcher = Join-Path $OutputDirectory "$Name.exe"
    Join-Files @($vm, $Archive) $launcher
    Copy-Item (Join-Path $ShippingDirectory '*.dll') $OutputDirectory
} elseif ($IsLinux) {
    # The package's RPATH is $ORIGIN/../lib; the game keeps lib/ beside itself.
    $engine = Join-Path $OutputDirectory "$Name.engine.tmp"
    Copy-Item -LiteralPath $vm -Destination $engine -Force
    try {
        & patchelf --set-rpath '$ORIGIN/lib' $engine
        if ($LASTEXITCODE -ne 0) { throw 'patchelf failed (install the patchelf package)' }
        $launcher = Join-Path $OutputDirectory $Name
        Join-Files @($engine, $Archive) $launcher
    } finally { Remove-Item -LiteralPath $engine -Force -ErrorAction SilentlyContinue }
    & chmod 755 $launcher
    if ($LASTEXITCODE -ne 0) { throw "chmod failed: $launcher" }
    Copy-EngineDirectory (Join-Path $ShippingDirectory 'lib')
} else {
    Copy-EngineDirectory (Join-Path $ShippingDirectory 'lhat-love.app')
    Copy-Item -LiteralPath $Archive -Destination (Join-Path $OutputDirectory "$Name.love") -Force
    $launcher = Join-Path $OutputDirectory "$Name.command"
    $script = @(
        '#!/bin/sh'
        "# Starts $Name.love with the bundled engine. Keep assets/ in this folder."
        'here=$(cd "$(dirname "$0")" && pwd)'
        "exec `"`$here/lhat-love.app/Contents/MacOS/love`" --fused `"`$here/$Name.love`" `"`$@`""
    ) -join "`n"
    [IO.File]::WriteAllText($launcher, $script + "`n")
    & chmod 755 $launcher
    if ($LASTEXITCODE -ne 0) { throw "chmod failed: $launcher" }
}
$launcher
