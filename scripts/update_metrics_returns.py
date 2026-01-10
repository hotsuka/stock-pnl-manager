#!/usr/bin/env python
"""評価指標のリターンを再計算するスクリプト"""
import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent / 'venv' / 'Lib' / 'site-packages'))
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app
from app.services import StockMetricsFetcher
from app.models import Holding

def update_returns():
    """リターン指標を再計算"""
    print("="*60)
    print("評価指標のリターン再計算")
    print("="*60)

    app = create_app('development')

    with app.app_context():
        holdings = Holding.query.all()
        ticker_symbols = [h.ticker_symbol for h in holdings]

        print(f"\n対象銘柄数: {len(ticker_symbols)}")
        print(f"銘柄: {', '.join(ticker_symbols[:10])}{'...' if len(ticker_symbols) > 10 else ''}")

        print("\n評価指標を再取得します（キャッシュを使用せず）...")
        print("これには数分かかる場合があります。\n")

        results = StockMetricsFetcher.update_all_holdings_metrics()

        print("\n" + "="*60)
        print("結果")
        print("="*60)
        print(f"成功: {results['success']}件")
        print(f"失敗: {results['failed']}件")

        # 成功した銘柄の詳細を表示
        if results['success'] > 0:
            print("\n成功した銘柄:")
            for detail in results['details']:
                if detail['status'] == 'success':
                    print(f"  ✓ {detail['ticker']}")

        # 失敗した銘柄の詳細を表示
        if results['failed'] > 0:
            print("\n失敗した銘柄:")
            for detail in results['details']:
                if detail['status'] == 'failed':
                    reason = detail.get('reason', '不明')
                    print(f"  ✗ {detail['ticker']}: {reason}")

        # サンプルデータを確認
        if results['success'] > 0:
            print("\n" + "="*60)
            print("サンプルデータ確認（最初の3件）")
            print("="*60)

            from app.models import StockMetrics
            sample_metrics = StockMetrics.query.limit(3).all()

            for m in sample_metrics:
                print(f"\n{m.ticker_symbol}:")
                print(f"  YTDリターン: {float(m.ytd_return) if m.ytd_return else 'データなし'}")
                print(f"  1年リターン: {float(m.one_year_return) if m.one_year_return else 'データなし'}")
                if m.ytd_return:
                    print(f"  YTD%: {float(m.ytd_return) * 100:.2f}%")
                if m.one_year_return:
                    print(f"  1年%: {float(m.one_year_return) * 100:.2f}%")

if __name__ == '__main__':
    try:
        update_returns()
        print("\n" + "="*60)
        print("完了!")
        print("="*60)
        print("\nブラウザで http://localhost:5000/holdings にアクセスして、")
        print("「評価指標」タブを開いて確認してください。")
    except KeyboardInterrupt:
        print("\n\n処理を中断しました")
    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()
