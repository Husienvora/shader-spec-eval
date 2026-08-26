param(
    [Parameter(Mandatory = $true)]
    [string]$Manifest,
    [Parameter(Mandatory = $true)]
    [string]$OutputDir,
    [int]$ExpectedCells = 1065,
    [double]$CostCeiling = 5.0
)

$ErrorActionPreference = 'Stop'

if (-not $env:OPENROUTER_API_KEY) {
    throw 'OPENROUTER_API_KEY is not available to the watchdog process.'
}

function Get-RunState {
    $cellsPath = Join-Path $OutputDir 'shader-cells.json'
    if (-not (Test-Path -LiteralPath $cellsPath)) {
        return [pscustomobject]@{ Count = 0; Spend = 0.0 }
    }
    $cells = Get-Content -LiteralPath $cellsPath -Raw | ConvertFrom-Json
    $hosted = $cells | Where-Object { $_.model -like 'openrouter:*' }
    $spend = ($hosted | Measure-Object -Property cost_usd -Sum).Sum
    return [pscustomobject]@{
        Count = $cells.Count
        Spend = if ($null -eq $spend) { 0.0 } else { [double]$spend }
    }
}

$noProgressExits = 0
while ($true) {
    $before = Get-RunState
    if ($before.Count -ge $ExpectedCells) {
        Write-Output "Study complete: $($before.Count) cells, `$$($before.Spend)."
        exit 0
    }
    if ($before.Spend -ge $CostCeiling) {
        Write-Error "Cost ceiling reached: `$$($before.Spend)."
        exit 2
    }

    Write-Output "Starting/resuming at $($before.Count)/$ExpectedCells cells; spend `$$($before.Spend)."
    & python -m shader_spec_eval.cli openrouter-study `
        --manifest $Manifest `
        --execute `
        --no-open `
        --output-dir $OutputDir
    $runnerExit = $LASTEXITCODE

    $after = Get-RunState
    if ($after.Count -ge $ExpectedCells) {
        Write-Output "Study complete: $($after.Count) cells, `$$($after.Spend)."
        exit 0
    }
    if ($after.Spend -ge $CostCeiling) {
        Write-Error "Cost ceiling reached: `$$($after.Spend)."
        exit 2
    }

    if ($after.Count -le $before.Count) {
        $noProgressExits += 1
    } else {
        $noProgressExits = 0
    }
    if ($noProgressExits -ge 3) {
        Write-Error "Runner exited three times without checkpoint progress (last exit $runnerExit)."
        exit 3
    }

    Write-Warning "Runner exited with code $runnerExit at $($after.Count) cells; resuming in 10 seconds."
    Start-Sleep -Seconds 10
}
