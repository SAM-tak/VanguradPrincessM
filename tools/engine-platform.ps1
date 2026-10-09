# Release platform names and executable locations inside lhat-love packages.
# Dot-source from the build scripts. Unix packages are extracted without their
# top-level directory, so both kinds of package root look alike.

function Get-EnginePlatform {
    $os = if ($IsWindows) { 'windows' } elseif ($IsLinux) { 'linux' } elseif ($IsMacOS) { 'macos' } else { throw 'Unsupported OS' }
    $cpu = switch ([Runtime.InteropServices.RuntimeInformation]::OSArchitecture) {
        'X64' { 'x64' }
        'Arm64' { 'arm64' }
        default { throw "Unsupported CPU: $_" }
    }
    "$os-$cpu"
}

# The full engine (compiler) or the VM-only runtime inside a package root.
function Get-EngineExecutable([string]$Directory, [switch]$Compiler) {
    $relative = if ($IsWindows) { if ($Compiler) { 'lovec.exe' } else { 'love.exe' } }
        elseif ($IsMacOS) { 'lhat-love.app/Contents/MacOS/love' }
        else { 'bin/love' }
    Join-Path $Directory $relative
}
