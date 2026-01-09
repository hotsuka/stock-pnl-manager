@echo off
REM テスト実行スクリプト（Windows用）

echo ========================================
echo Stock P&L Manager - Test Suite
echo ========================================
echo.

REM 仮想環境のアクティベート（存在する場合）
if exist venv\Scripts\activate.bat (
    echo 仮想環境をアクティベート中...
    call venv\Scripts\activate.bat
) else (
    echo 警告: 仮想環境が見つかりません
)

echo.
echo テストを実行中...
echo.

REM pytestを実行
python -m pytest

echo.
echo ========================================
echo テスト完了
echo ========================================
echo.
echo カバレッジレポートは htmlcov/index.html で確認できます
echo.

pause
