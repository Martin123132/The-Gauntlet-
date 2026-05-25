@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "REPO_DIR=%CD%"
set "VENV_DIR=%REPO_DIR%\.venv"
set "LOG_DIR=%REPO_DIR%\.gauntlet\logs"
set "LAUNCHER_LOG=%LOG_DIR%\Start-Gauntlet.log"
set "STREAMLIT_URL=http://localhost:8501"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>nul
> "%LAUNCHER_LOG%" echo The Gauntlet launcher log
if errorlevel 1 (
    echo Warning: launcher log could not be created at %LAUNCHER_LOG%
    set "LAUNCHER_LOG=NUL"
) else (
    >> "%LAUNCHER_LOG%" echo Started: %DATE% %TIME%
    >> "%LAUNCHER_LOG%" echo Repo: %REPO_DIR%
    >> "%LAUNCHER_LOG%" echo Venv: %VENV_DIR%
)

echo.
echo ======================================
echo   The Gauntlet - Local Paper Checker
echo ======================================
echo.
echo This launcher installs only the local, non-AI checker.
echo No API key is needed for the default paper analysis.
echo.
echo Repo folder: %REPO_DIR%
echo Venv folder: %VENV_DIR%
echo Launcher log: %LAUNCHER_LOG%
echo Browser URL: %STREAMLIT_URL%
echo.

echo [1/5] Checking for Python 3.10 or newer...
>> "%LAUNCHER_LOG%" echo [1/5] Checking for Python 3.10 or newer...
where py >> "%LAUNCHER_LOG%" 2>&1
if %errorlevel%==0 (
    set "PYTHON=py -3"
) else (
    where python >> "%LAUNCHER_LOG%" 2>&1
    if errorlevel 1 (
        echo.
        echo Python 3.10 or newer was not found.
        echo Install Python from https://www.python.org/downloads/ and try again.
        echo.
        echo Troubleshooting log: %LAUNCHER_LOG%
        >> "%LAUNCHER_LOG%" echo ERROR: Python was not found on PATH.
        pause
        exit /b 1
    )
    set "PYTHON=python"
)

%PYTHON% --version
%PYTHON% --version >> "%LAUNCHER_LOG%" 2>&1
%PYTHON% -c "import sys; print('Python executable:', sys.executable)" >> "%LAUNCHER_LOG%" 2>&1
%PYTHON% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo.
    echo The Gauntlet needs Python 3.10 or newer.
    echo Found:
    %PYTHON% --version
    echo.
    echo Install a newer Python from https://www.python.org/downloads/ and try again.
    echo Troubleshooting log: %LAUNCHER_LOG%
    >> "%LAUNCHER_LOG%" echo ERROR: Python version is older than 3.10.
    pause
    exit /b 1
)

echo.
echo [2/5] Preparing local Python environment...
>> "%LAUNCHER_LOG%" echo [2/5] Preparing local Python environment...
if not exist ".venv\Scripts\python.exe" (
    echo Creating local Python environment in .venv...
    %PYTHON% -m venv .venv >> "%LAUNCHER_LOG%" 2>&1
    if errorlevel 1 (
        echo.
        echo Failed to create .venv.
        echo Try reinstalling Python 3.10+ and make sure the Python launcher can create virtual environments.
        echo Troubleshooting log: %LAUNCHER_LOG%
        >> "%LAUNCHER_LOG%" echo ERROR: venv creation failed.
        pause
        exit /b 1
    )
) else (
    echo Existing .venv found.
    >> "%LAUNCHER_LOG%" echo Existing .venv found.
)

echo.
echo [3/5] Upgrading pip inside .venv...
>> "%LAUNCHER_LOG%" echo [3/5] Upgrading pip inside .venv...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip >> "%LAUNCHER_LOG%" 2>&1
if errorlevel 1 (
    echo.
    echo Failed to upgrade pip.
    echo Check the launcher log, then try deleting .venv and running this file again.
    echo Troubleshooting log: %LAUNCHER_LOG%
    >> "%LAUNCHER_LOG%" echo ERROR: pip upgrade failed.
    pause
    exit /b 1
)

echo.
echo [4/5] Installing local non-AI requirements...
echo This can take a minute on the first run.
>> "%LAUNCHER_LOG%" echo [4/5] Installing local non-AI requirements...
".venv\Scripts\python.exe" -m pip install -r requirements.txt >> "%LAUNCHER_LOG%" 2>&1
if errorlevel 1 (
    echo.
    echo Failed to install local requirements.
    echo Check your internet connection, antivirus prompts, and the launcher log, then try again.
    echo Troubleshooting log: %LAUNCHER_LOG%
    >> "%LAUNCHER_LOG%" echo ERROR: requirements.txt install failed.
    pause
    exit /b 1
)

echo.
echo Optional AI refinement is not installed by default.
echo To enable Gemini, OpenAI, or Anthropic later, install requirements-ai.txt manually.
echo.
echo [5/5] Starting The Gauntlet...
echo Browser URL: %STREAMLIT_URL%
echo Close this window to stop the local app.
echo Troubleshooting log: %LAUNCHER_LOG%
echo.
>> "%LAUNCHER_LOG%" echo [5/5] Starting Streamlit at %STREAMLIT_URL%
".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501 >> "%LAUNCHER_LOG%" 2>&1
if errorlevel 1 (
    echo.
    echo Streamlit stopped before The Gauntlet could open.
    echo Check the launcher log for the last error message.
    echo Troubleshooting log: %LAUNCHER_LOG%
    >> "%LAUNCHER_LOG%" echo ERROR: Streamlit exited with an error.
    pause
    exit /b 1
)

pause
