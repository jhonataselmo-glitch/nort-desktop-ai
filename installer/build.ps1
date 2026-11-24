$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if ($env:OS -ne "Windows_NT") { throw "Compile o instalador no Windows." }
function Check-Exit { if ($LASTEXITCODE -ne 0) { throw "Comando falhou: $LASTEXITCODE" } }
py -3.11 -m venv .venv
Check-Exit
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Check-Exit
$env:NORT_BROWSER_TESTS = "1"
& .\.venv\Scripts\python.exe -m pytest -q
Check-Exit
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --name NORT-Desktop-AI --collect-all playwright --hidden-import keyring.backends.Windows --hidden-import pywinauto --hidden-import comtypes --paths . launch.py
Check-Exit
$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($iscc) { $compiler = $iscc.Source }
else { $compiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
if (!(Test-Path $compiler)) { throw "Instale Inno Setup 6 para gerar o Setup.exe. O executavel portatil esta em dist." }
& $compiler installer\nort.iss
Check-Exit
Write-Host "Instalador: dist\NORT-Desktop-AI-Setup.exe"
