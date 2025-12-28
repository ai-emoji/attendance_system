param(
    [Parameter(Mandatory = $true)][string]$Patch,
    [Parameter(Mandatory = $true)][string]$TargetDir,
    [Parameter(Mandatory = $false)][switch]$DryRun,
    [Parameter(Mandatory = $false)][switch]$Force
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $py = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path $py)) {
        $py = 'python'
    }

    $cliArgs = @('tools/apply_patch.py', '--patch', $Patch, '--target-dir', $TargetDir)
    if ($DryRun) { $cliArgs += '--dry-run' }
    if ($Force) { $cliArgs += '--force' }

    & $py @cliArgs
}
finally {
    Pop-Location
}
