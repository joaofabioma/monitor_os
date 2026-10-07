@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

set "VENV_DIR=.venv"
set "PYTHON_BIN=%VENV_DIR%\Scripts\python.exe"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py -3"
) else (
    set "PYTHON_CMD=python"
)

if not exist "%PYTHON_BIN%" (
    echo Criando ambiente virtual em %VENV_DIR%...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
)

if not exist "%PYTHON_BIN%" (
    echo Erro: Python virtual environment foi criada incorretamente.
    exit /b 1
)

echo Instalando dependências com pip...
"%PYTHON_BIN%" -m pip install --upgrade pip
"%PYTHON_BIN%" -m pip install -r requirements.txt

echo Iniciando aplicação em produção com Waitress...
"%PYTHON_BIN%" -m waitress --host 0.0.0.0 --port 94 app:app

endlocal
