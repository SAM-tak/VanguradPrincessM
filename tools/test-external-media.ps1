param([string]$Love = 'C:/Users/Owner/source/repos/lhat-love')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$work = Join-Path $root ('build/external-media-test/' + [guid]::NewGuid().ToString('N'))
$source = Join-Path $work 'source'
$run = Join-Path $work 'run'
New-Item -ItemType Directory -Force "$source/src", "$source/data/_conversion", "$source/data/skills", "$source/assets", $run | Out-Null
Copy-Item -LiteralPath "$root/src/media.lh" -Destination "$source/src/media.lh"
@'
module^externalmediatest
import^love.event
import^love.filesystem
require^"src/media.lh"
public^let^load = p^{
 vp.media.prepare()
 vp.media.prepare()
 let^media = love.filesystem.read("assets/probe.txt")
 if^media != "media" { panic^"Wrong media" }
 if^love.filesystem.read("data/probe.txt") != "internal" { panic^"External data replaced internal data" }
 if^love.filesystem.getInfo("outside.txt") != nil^ { panic^"Executable directory mount leaked" }
 print("EXTERNAL_MEDIA_OK") love.event.quit()
}
public^let^draw = p^{}
'@ | Set-Content -LiteralPath "$source/main.lh" -Encoding utf8
'window = { visible = false^ },' | Set-Content -LiteralPath "$source/conf.lton"
[IO.File]::WriteAllText("$source/data/probe.txt", 'internal')
[IO.File]::WriteAllText("$source/assets/probe.txt", 'media')
foreach ($f in 'data/_conversion/excluded.txt', 'data/skills/excluded.txt', 'data/data.lton', 'data/support-source.lton') {
 [IO.File]::WriteAllText("$source/$f", 'excluded')
}
Copy-Item "$Love/build-vmonly-shipping/love/Release/*.dll" $run
function Package([bool]$Include) {
 $name = if ($Include) { 'embedded' } else { 'external' }
 $archive = "$work/$name.love"
 & "$root/tools/package-game.ps1" -SourceRoot $source -Lovec "$Love/build/love/Release/lovec.exe" -WorkDirectory "$work/$name" -Archive $archive -IncludeAssets:$Include
 $zip = [IO.Compression.ZipFile]::OpenRead($archive)
 try {
  foreach ($e in $zip.Entries) {
   if ($e.FullName -match '(^|/)(_conversion|skills)/|(^|/)(data|support-source)\.lton$') { throw "Excluded file packaged: $($e.FullName)" }
   if (!$Include -and $e.FullName.StartsWith('assets/')) { throw 'Assets bundled by default' }
  }
 } finally { $zip.Dispose() }
 $stream = [IO.File]::Create("$run/game.exe")
 try { foreach ($part in "$Love/build-vmonly-shipping/love/Release/love.exe", $archive) {
  $inputStream = [IO.File]::OpenRead($part)
  try { $inputStream.CopyTo($stream) } finally { $inputStream.Dispose() }
 } } finally { $stream.Dispose() }
}
function Run([string]$Expected) {
 $info = [Diagnostics.ProcessStartInfo]::new()
 $info.FileName = "$run/game.exe"
 $info.WorkingDirectory = $root
 $info.UseShellExecute = $false
 $info.CreateNoWindow = $true
 $info.WindowStyle = [Diagnostics.ProcessWindowStyle]::Hidden
 $info.RedirectStandardOutput = $true
 $info.RedirectStandardError = $true
 $info.ArgumentList.Add('--no-error-screen')
 $process = [Diagnostics.Process]::Start($info)
 try {
  $stdout = $process.StandardOutput.ReadToEndAsync()
  $stderr = $process.StandardError.ReadToEndAsync()
  if (!$process.WaitForExit(30000)) { $process.Kill($true); throw 'Test timed out' }
  $text = $stdout.GetAwaiter().GetResult() + $stderr.GetAwaiter().GetResult()
  if (!$text.Contains($Expected)) { throw "Unexpected result: $text" }
  if ($Expected -eq 'EXTERNAL_MEDIA_OK' -and $process.ExitCode -ne 0) { throw $text }
  Write-Host "PASS: $Expected"
 } finally { $process.Dispose() }
}
Package $false
Run 'assets folder is missing beside the executable'
New-Item -ItemType Directory -Force "$run/assets", "$run/data" | Out-Null
[IO.File]::WriteAllText("$run/assets/probe.txt", 'media')
[IO.File]::WriteAllText("$run/data/probe.txt", 'external')
[IO.File]::WriteAllText("$run/outside.txt", 'must not be exposed')
Run 'EXTERNAL_MEDIA_OK'
Package $true
[IO.File]::WriteAllText("$run/assets/probe.txt", 'must not override embedded assets')
Run 'EXTERNAL_MEDIA_OK'
Write-Host "PASS: default exclusion, fused external assets, missing assets, internal data precedence, embedded option ($work)"
