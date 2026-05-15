@echo off
setlocal

cd /d "%~dp0"

echo.
echo ======================================
echo   The Gauntlet - Local Paper Checker
echo ======================================
echo.
echo This launcher installs only the local, non-AI checker.
echo No API key is needed for the default paper analysis.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python 3.10 or newer was not found.
        echo Install Python from https://www.python.org/downloads/ and try again.
        pause
        exit /b 1
    )
    set "PYTHON=python"
)

%PYTHON% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo The Gauntlet needs Python 3.10 or newer.
    echo Found:
    %PYTHON% --version
    echo.
    echo Install a newer Python from https://www.python.org/downloads/ and try again.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating local Python environment in .venv...
    %PYTHON% -m venv .venv
    if errorlevel 1 (
        echo Failed to create .venv. Install Python 3.10 or newer and try again.
        pause
        exit /b 1
    )
)

echo.
echo Installing local non-AI requirements...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install local requirements.
    echo Check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo Optional AI refinement is not installed by default.
echo To enable Gemini, OpenAI, or Anthropic later, install requirements-ai.txt manually.
echo.
echo Starting The Gauntlet...
echo Browser URL: http://localhost:8501
echo Close this window to stop the local app.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501

pause
