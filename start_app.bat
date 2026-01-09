@echo off
echo ============================================================
echo Starting Stock P^&L Manager Application
echo ============================================================
echo.

REM Check if virtual environment exists
if not exist "venv\Lib\site-packages\flask" (
    echo ERROR: Virtual environment not properly configured
    echo Flask is not installed in venv
    echo.
    echo Please run: python -m venv venv
    echo Then: venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

REM Set Flask environment variables
set FLASK_APP=run.py
set FLASK_ENV=development
set PYTHONPATH=%CD%

echo Starting Flask application...
echo.
echo Application will be available at: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.

REM Use Python from venv to run the app
python run.py

pause
