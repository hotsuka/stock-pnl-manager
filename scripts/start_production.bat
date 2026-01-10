@echo off
REM Stock P&L Manager - Production Startup Script (Windows)

setlocal enabledelayedexpansion

echo ======================================
echo Stock P&L Manager - Production Startup
echo ======================================
echo.

REM Get script directory
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..

REM Change to project directory
cd /d "%PROJECT_DIR%"

REM Check if .env file exists
if not exist ".env" (
    echo [ERROR] .env file not found
    echo Please create .env file from .env.example
    echo   copy .env.example .env
    pause
    exit /b 1
)

REM Load environment variables from .env
echo [INFO] Loading environment variables...
for /f "usebackq tokens=* delims=" %%a in (".env") do (
    set "line=%%a"
    REM Skip comments and empty lines
    if not "!line:~0,1!"=="#" if not "!line!"=="" (
        set %%a
    )
)

REM Check if SECRET_KEY is set
if "%SECRET_KEY%"=="" (
    echo [ERROR] SECRET_KEY is not set in .env file
    echo Please generate a secure SECRET_KEY:
    echo   python -c "import secrets; print(secrets.token_hex(32))"
    pause
    exit /b 1
)

if "%SECRET_KEY%"=="dev-secret-key-please-change-in-production" (
    echo [ERROR] SECRET_KEY is using default value
    echo Please generate a secure SECRET_KEY:
    echo   python -c "import secrets; print(secrets.token_hex(32))"
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo [INFO] Virtual environment not found. Creating...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install dependencies
echo [INFO] Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

REM Create necessary directories
echo [INFO] Creating necessary directories...
if not exist "data\uploads" mkdir data\uploads
if not exist "logs" mkdir logs
if not exist "backups" mkdir backups

REM Run database migrations
echo [INFO] Running database migrations...
flask db upgrade
if errorlevel 1 (
    echo [ERROR] Database migration failed
    pause
    exit /b 1
)

REM Check if waitress is installed
python -c "import waitress" 2>nul
if errorlevel 1 (
    echo [INFO] Waitress not found. Installing...
    pip install waitress
)

REM Configuration
if "%WORKERS%"=="" set WORKERS=4
if "%PORT%"=="" set PORT=8000
if "%TIMEOUT%"=="" set TIMEOUT=120
if "%LOG_FILE%"=="" set LOG_FILE=logs\waitress.log

echo.
echo ======================================
echo Configuration:
echo   Workers: %WORKERS%
echo   Port: %PORT%
echo   Timeout: %TIMEOUT%s
echo   Log file: %LOG_FILE%
echo ======================================
echo.

REM Start waitress
echo [INFO] Starting Stock P&L Manager...
echo.

waitress-serve ^
    --host=0.0.0.0 ^
    --port=%PORT% ^
    --threads=%WORKERS% ^
    --channel-timeout=%TIMEOUT% ^
    --call app:create_app

REM If waitress exits, show error
if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with error
    pause
    exit /b 1
)

endlocal
