@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3.11 -m venv .venv
  if errorlevel 1 (
    echo Instale Python 3.11 para Windows em python.org e execute novamente.
    pause
    exit /b 1
  )
)
.venv\Scripts\python.exe -m pip install -e .
if errorlevel 1 (
  echo Falha ao instalar dependencias. Verifique sua conexao.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m nort
if errorlevel 1 pause
