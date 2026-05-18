@echo off
setlocal

cd /d "%~dp0"

echo.
echo ======================================
echo   The Gauntlet - Analyze One Paper
echo ======================================
echo.
echo Drag a .pdf, .docx, .txt, .md file, or a folder onto this batch file,
echo or paste a paper/folder path when prompted.
echo.

set "TARGET=%~1"
if "%TARGET%"=="" (
    set /p "TARGET=Paper or folder path: "
)
set "TARGET=%TARGET:"=%"

if "%TARGET%"=="" (
    echo No paper path was provided.
    pause
    exit /b 1
)

if not exist "%TARGET%" (
    echo That file was not found:
    echo %TARGET%
    pause
    exit /b 1
)

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
echo Running local analysis...
".venv\Scripts\python.exe" -m gauntlet_core.cli "%TARGET%" --out gauntlet-reports --format all
if errorlevel 1 (
    echo.
    echo Analysis failed. Check the message above and try another file.
    pause
    exit /b 1
)

echo.
echo Done. Reports were written to the gauntlet-reports folder.
echo Optional AI refinement is not installed or used by this launcher.
pause
