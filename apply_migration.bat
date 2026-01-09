@echo off
echo ============================================================
echo Applying Database Migration
echo ============================================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Set Flask environment
set FLASK_APP=run.py
set FLASK_ENV=development

echo Checking current database state...
python -c "import sqlite3; conn = sqlite3.connect('data/stock_pnl.db'); cursor = conn.cursor(); cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name NOT LIKE \"sqlite_%%\"'); tables = [t[0] for t in cursor.fetchall()]; print(f'Current tables: {tables}'); conn.close()"

echo.
echo Applying migration using flask db upgrade...
flask db upgrade

echo.
echo ============================================================
echo Verifying database after migration
echo ============================================================
python -c "import sqlite3; conn = sqlite3.connect('data/stock_pnl.db'); cursor = conn.cursor(); cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name NOT LIKE \"sqlite_%%\"'); tables = [t[0] for t in cursor.fetchall()]; print(f'\nTables in database: {len(tables)}'); [print(f'  - {t}') for t in sorted(tables)]; conn.close()"

echo.
echo Checking migration version...
python -c "import sqlite3; conn = sqlite3.connect('data/stock_pnl.db'); cursor = conn.cursor(); cursor.execute('SELECT version_num FROM alembic_version'); version = cursor.fetchone(); print(f'Migration version: {version[0] if version else \"None\"}'); conn.close()"

echo.
echo ============================================================
echo Migration complete!
echo ============================================================
pause
