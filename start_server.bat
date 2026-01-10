@echo off
REM Stock P&L Manager - 簡易起動スクリプト

echo ======================================
echo Stock P&L Manager - 本番サーバー起動
echo ======================================
echo.

REM プロジェクトディレクトリに移動
cd /d "%~dp0"

REM 環境変数の確認
if not exist ".env" (
    echo [エラー] .envファイルが見つかりません
    echo .env.exampleをコピーして.envを作成してください
    pause
    exit /b 1
)

REM 必要なディレクトリを作成
if not exist "logs" mkdir logs
if not exist "backups" mkdir backups
if not exist "data\uploads" mkdir data\uploads

echo [情報] サーバーを起動しています...
echo.
echo アクセスURL: http://localhost:8000
echo 停止方法: Ctrl+C を押してください
echo.

REM Waitressでサーバー起動
python -m waitress --host=0.0.0.0 --port=8000 --threads=4 wsgi:app

pause
