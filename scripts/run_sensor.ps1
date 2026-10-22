param(
    [int]$Camera = 0,
    [int]$Width = 960,
    [int]$Height = 540
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw "Falta .venv. Ejecute primero .\scripts\setup.ps1"
}

Push-Location $ProjectRoot
try {
    & $VenvPython -m sensor.app --camera $Camera --width $Width --height $Height
}
finally {
    Pop-Location
}
