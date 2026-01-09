@echo off
echo ========================================
echo Database Setup Script
echo ========================================
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Set Flask app
set FLASK_APP=run.py
set FLASK_ENV=development

echo.
echo Checking current database state...
python -c "import sqlite3; conn = sqlite3.connect('data/stock_pnl.db'); cursor = conn.cursor(); cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name NOT LIKE \"sqlite_%%\"'); tables = [t[0] for t in cursor.fetchall()]; print(f'Current tables: {tables}'); conn.close()"

echo.
echo Creating migrations directory structure...
if not exist "migrations\versions" mkdir "migrations\versions"

echo.
echo ========================================
echo Step 1: Creating initial migration
echo ========================================
flask db migrate -m "Initial migration with all models"

echo.
echo ========================================
echo Step 2: Applying migration to database
echo ========================================
flask db upgrade

echo.
echo ========================================
echo Verification
echo ========================================
python -c "import sqlite3; conn = sqlite3.connect('data/stock_pnl.db'); cursor = conn.cursor(); cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name NOT LIKE \"sqlite_%%\"'); tables = [t[0] for t in cursor.fetchall()]; print(f'\nTables in database: {len(tables)}'); [print(f'  - {t}') for t in sorted(tables)]; conn.close()"

echo.
echo ========================================
echo Database setup complete!
echo ========================================
pause
