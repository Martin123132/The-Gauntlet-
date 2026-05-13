@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON=py -3"
) else (
    set "PYTHON=python"
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating local Python environment...
    %PYTHON% -m venv .venv
    if errorlevel 1 (
        echo Failed to create .venv. Install Python 3.10 or newer and try again.
        pause
        exit /b 1
    )
)

echo Installing local requirements...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install requirements.
    pause
    exit /b 1
)

echo Starting The Gauntlet...
".venv\Scripts\python.exe" -m streamlit run app.py

pause
