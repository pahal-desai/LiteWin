@echo off
setlocal EnableDelayedExpansion

title LiteWin - Windows, without the baggage

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."

echo ====================================================
echo  LiteWin - Windows, without the baggage.
echo  Automated Launcher
echo ====================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set PY_CMD=python
    goto :PY_FOUND
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set PY_CMD=py -3
    goto :PY_FOUND
)

echo [LiteWin] Python 3 was not detected on your system.
echo [LiteWin] Automatically installing Python 3...
echo.

where winget >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [LiteWin] Installing Python 3 via Windows Package Manager (winget)...
    winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    if %ERRORLEVEL% equ 0 (
        set PY_CMD=python
        goto :PY_FOUND
    )
)

echo [LiteWin] Downloading official Python installer from python.org...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$url = 'https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe'; " ^
    "$dest = '$env:TEMP\python_setup.exe'; " ^
    "Write-Host '[LiteWin] Downloading...'; " ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; " ^
    "(New-Object System.Net.WebClient).DownloadFile($url, $dest); " ^
    "Write-Host '[LiteWin] Running silent installation...'; " ^
    "Start-Process -FilePath $dest -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_test=0' -Wait; " ^
    "Remove-Item -Path $dest -Force -ErrorAction SilentlyContinue"

set PY_CMD=python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
        set PY_CMD="%LocalAppData%\Programs\Python\Python312\python.exe"
    )
)

:PY_FOUND
echo [LiteWin] Python environment ready (%PY_CMD%).

REM Setup and activate virtual environment (.venv)
if not exist ".venv" (
    echo [LiteWin] Creating dedicated virtual environment in .venv...
    %PY_CMD% -m venv .venv
)

echo [LiteWin] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [LiteWin] Checking and installing dependencies...
pip install -e . --quiet

echo [LiteWin] Launching LiteWin Graphical User Interface...
python -m litewin.cli gui %*

endlocal
