param(
    [Parameter(Mandatory = $true)][string]$FromDir,
    [Parameter(Mandatory = $true)][string]$ToDir,
    [Parameter(Mandatory = $true)][string]$FromVersion,
    [Parameter(Mandatory = $true)][string]$ToVersion,
    [Parameter(Mandatory = $false)][string]$Out = "patches/patch_${FromVersion}_to_${ToVersion}.zip"
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $py = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path $py)) {
        $py = 'python'
    }

    & $py tools/make_patch.py --from-dir $FromDir --to-dir $ToDir --from-version $FromVersion --to-version $ToVersion --out $Out
}
finally {
    Pop-Location
}
