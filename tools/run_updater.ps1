param(
    [Parameter(Mandatory = $true)][string]$UpdateJson,
    [Parameter(Mandatory = $true)][string]$TargetDir,
    [Parameter(Mandatory = $false)][switch]$Force,
    [Parameter(Mandatory = $false)][switch]$NoLaunch
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $py = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path $py)) {
        $py = 'python'
    }

    $cliArgs = @('tools/updater.py', '--update-json', $UpdateJson, '--target-dir', $TargetDir)
    if ($Force) { $cliArgs += '--force' }
    if ($NoLaunch) { $cliArgs += '--no-launch' }

    & $py @cliArgs
}
finally {
    Pop-Location
}
