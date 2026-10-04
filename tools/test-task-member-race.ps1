param([string]$Lhat = 'C:/Users/Owner/source/repos/lhat/build/release/lhat.exe')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$sourcePath = Join-Path $root 'tests/task-member-race.lh'
$source = [IO.File]::ReadAllText($sourcePath)
$variants = @(
    @{ Name = 'Two workers, member access'; Text = $source; Runs = 10 },
    @{ Name = 'One worker, member access'; Text = $source.Replace('std.task.start(2)', 'std.task.start(1)'); Runs = 3 },
    @{ Name = 'Two workers, index access'; Text = $source.Replace('own.tag', 'own["tag"]'); Runs = 3 }
)
$entry = Join-Path ([IO.Path]::GetTempPath()) ('lhat-member-race-' + [guid]::NewGuid() + '.lh')
try {
    foreach ($variant in $variants) {
        Write-Output $variant.Name
        [IO.File]::WriteAllText($entry, $variant.Text)
        for ($trial = 1; $trial -le $variant.Runs; $trial++) {
            & $Lhat $entry
            Write-Output "Run $trial exit=$LASTEXITCODE"
        }
    }
} finally {
    Remove-Item -LiteralPath $entry -ErrorAction SilentlyContinue
}
