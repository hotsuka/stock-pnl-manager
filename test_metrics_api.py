#!/usr/bin/env python
"""評価指標APIのテストスクリプト"""
import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent / 'venv' / 'Lib' / 'site-packages'))
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app
from app.services import StockMetricsFetcher
from app.models import Holding, StockMetrics

def test_metrics_api():
    """評価指標APIの動作をテスト"""
    print("="*60)
    print("評価指標API テスト")
    print("="*60)

    app = create_app('development')

    with app.app_context():
        # 1. データベース内の評価指標を確認
        print("\n1. データベース内の評価指標:")
        metrics_count = StockMetrics.query.count()
        print(f"   評価指標レコード数: {metrics_count}")

        if metrics_count > 0:
            sample_metrics = StockMetrics.query.limit(3).all()
            for m in sample_metrics:
                print(f"   - {m.ticker_symbol}: PER={m.pe_ratio}, 時価総額={m.market_cap}")

        # 2. Holdingsを確認
        print("\n2. 保有銘柄:")
        holdings = Holding.query.all()
        print(f"   保有銘柄数: {len(holdings)}")
        ticker_symbols = [h.ticker_symbol for h in holdings]
        print(f"   ティッカー: {ticker_symbols[:5]}...")

        # 3. get_multiple_metricsをテスト
        print("\n3. get_multiple_metrics テスト:")
        try:
            results = StockMetricsFetcher.get_multiple_metrics(ticker_symbols, use_cache=True)
            print(f"   取得成功: {len(results)}/{len(ticker_symbols)}件")

            # サンプルデータを表示
            if results:
                first_ticker = list(results.keys())[0]
                first_data = results[first_ticker]
                print(f"\n   サンプルデータ ({first_ticker}):")
                for key, value in first_data.items():
                    print(f"     {key}: {value}")

        except Exception as e:
            print(f"   エラー: {e}")
            import traceback
            traceback.print_exc()

        # 4. APIエンドポイントをシミュレート
        print("\n4. APIエンドポイント シミュレーション:")
        try:
            from app.routes.api import bp
            with app.test_client() as client:
                response = client.get('/api/holdings/metrics')
                print(f"   ステータスコード: {response.status_code}")

                if response.status_code == 200:
                    data = response.get_json()
                    print(f"   成功: {data.get('success')}")
                    print(f"   件数: {data.get('count')}")

                    if data.get('metrics'):
                        print(f"   最初の指標: {data['metrics'][0]['ticker_symbol']}")
                else:
                    print(f"   レスポンス: {response.get_data(as_text=True)}")

        except Exception as e:
            print(f"   エラー: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_metrics_api()
