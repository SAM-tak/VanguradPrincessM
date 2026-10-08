# Compile a tiny game with the full engine, then run it with the shipping VM.
# Run before staging assets or replacing an existing distribution.
param(
    [string]$Love = "C:\Users\Owner\source\repos\lhat-love",
    [ValidateRange(1, 600)][int]$TimeoutSeconds = 30
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$lovec = Join-Path $Love "build\love\Release\lovec.exe"
$vm = Join-Path $Love "build-vmonly-shipping\love\Release\love.exe"
foreach ($exe in $lovec, $vm) {
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Engine check: missing $exe" }
}
$work = Join-Path $root ("build\engine-check\" + [guid]::NewGuid().ToString("N"))
$source = Join-Path $work "source"
$compiled = Join-Path $work "compiled"
New-Item -ItemType Directory -Path $source -Force | Out-Null
$marker = "ENGINE_CHECK_OK_" + [guid]::NewGuid().ToString("N")
@"
module^enginecheck
import^love.event
public^let^load = p^{ print("$marker") love.event.quit() }
public^let^draw = p^{}
"@ | Set-Content -LiteralPath (Join-Path $source "main.lh") -Encoding utf8
@'
identity = "vanguard-engine-check",
window = { title = "Engine check", width = 64, height = 64, visible = false^ },
'@ | Set-Content -LiteralPath (Join-Path $source "conf.lton") -Encoding utf8

function Invoke-CheckProcess {
    param([string]$Exe, [string[]]$Arguments, [string]$Label)
    $info = [System.Diagnostics.ProcessStartInfo]::new()
    $info.FileName = (Resolve-Path -LiteralPath $Exe).Path
    $info.WorkingDirectory = $root
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    foreach ($argument in $Arguments) { $info.ArgumentList.Add($argument) }
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $info
    try {
        if (-not $process.Start()) { throw "Could not start $Exe" }
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        $timedOut = -not $process.WaitForExit($TimeoutSeconds * 1000)
        if ($timedOut) { $process.Kill($true); $process.WaitForExit() }
        $output = $stdout.GetAwaiter().GetResult()
        $errors = $stderr.GetAwaiter().GetResult()
        $output | Set-Content -LiteralPath (Join-Path $work "$Label.stdout.log") -Encoding utf8
        $errors | Set-Content -LiteralPath (Join-Path $work "$Label.stderr.log") -Encoding utf8
        if ($timedOut -or $process.ExitCode -ne 0) {
            if ($output) { Write-Host $output }
            if ($errors) { Write-Host $errors }
            $reason = if ($timedOut) { "timeout (${TimeoutSeconds}s)" } else { "exit $($process.ExitCode)" }
            throw "$Label failed: $reason"
        }
        return $output
    } finally {
        $process.Dispose()
    }
}

Write-Host "checking compiler / shipping VM compatibility"
try {
    $null = Invoke-CheckProcess $lovec @("--no-error-screen", "--compile-game", $compiled, $source) "compile"
    $output = Invoke-CheckProcess $vm @("--no-error-screen", $compiled) "vm"
    if (-not ($output -split '\r?\n' -contains $marker)) {
        throw "VM exited without the game's success marker"
    }
} catch {
    throw @"
Engine compatibility check failed: $($_.Exception.Message)
Logs: $work
If signatures or compiled units are incompatible, rebuild the full engine, run
  & '$Love\scripts\regen-generated.ps1' -Lovec '$lovec'
then rebuild the VM-only shipping engine:
  & '$Love\scripts\build.ps1' -VmOnly -Shipping
Distribution staging has not started.
"@
}
Write-Host "engine check passed (logs: $work)"
