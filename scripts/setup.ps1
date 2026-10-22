$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$InstalledPython = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    if (-not (Test-Path -LiteralPath $InstalledPython)) {
        throw "No se encontro Python 3.12. Instalelo y vuelva a ejecutar este script."
    }
    & $InstalledPython -m venv (Join-Path $ProjectRoot ".venv")
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno virtual." }
}

& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "No se pudo actualizar pip." }
& $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements-dev.txt")
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias." }
& $VenvPython -m pytest (Join-Path $ProjectRoot "tests")
if ($LASTEXITCODE -ne 0) { throw "Las pruebas automaticas fallaron." }

Write-Host "Preparacion terminada. Ejecute: .\scripts\run_sensor.ps1"

