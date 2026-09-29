param([string]$PythonPath = 'python')
$ErrorActionPreference = 'Stop'
$localPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if ($PythonPath -eq 'python' -and (Test-Path -LiteralPath $localPython)) { $PythonPath = $localPython }
$meta = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'examples/metadata.json') | ConvertFrom-Json
$period = $meta.period.ToString([System.Globalization.CultureInfo]::InvariantCulture)
foreach ($modelName in @('timdr_lda', 'classical_rf')) {
    & $PythonPath (Join-Path $PSScriptRoot 'predict.py') (Join-Path $PSScriptRoot 'examples/ogle_test_curve.csv') --period $period --model $modelName --output (Join-Path $PSScriptRoot "examples/prediction_$modelName.json")
    if ($LASTEXITCODE -ne 0) { throw "Model failed: $modelName" }
}
