#!/bin/bash
# テスト実行スクリプト（Unix/Linux/Mac用）

echo "========================================"
echo "Stock P&L Manager - Test Suite"
echo "========================================"
echo ""

# 仮想環境のアクティベート（存在する場合）
if [ -f "venv/bin/activate" ]; then
    echo "仮想環境をアクティベート中..."
    source venv/bin/activate
else
    echo "警告: 仮想環境が見つかりません"
fi

echo ""
echo "テストを実行中..."
echo ""

# pytestを実行
python -m pytest

echo ""
echo "========================================"
echo "テスト完了"
echo "========================================"
echo ""
echo "カバレッジレポートは htmlcov/index.html で確認できます"
echo ""
