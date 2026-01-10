#!/usr/bin/env python
"""
全データ更新スクリプト

Usage:
    python scripts/update_all_data.py [options]

Options:
    --skip-prices       株価更新をスキップ
    --skip-dividends    配当更新をスキップ
    --skip-metrics      評価指標更新をスキップ
    --skip-benchmarks   ベンチマーク更新をスキップ
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

from app import create_app, db
from app.models import Holding
from app.services import (
    StockPriceFetcher,
    DividendFetcher,
    StockMetricsFetcher
)
from app.services.benchmark_fetcher import BenchmarkFetcher


def update_stock_prices():
    """全保有銘柄の株価を更新"""
    print()
    print("=" * 60)
    print("株価更新")
    print("=" * 60)

    holdings = Holding.query.all()

    if not holdings:
        print("[INFO] 保有銘柄がありません")
        return {'success': 0, 'failed': 0}

    print(f"[INFO] {len(holdings)}銘柄の株価を更新します...")

    success_count = 0
    failed_count = 0

    for holding in holdings:
        try:
            print(f"[INFO] {holding.ticker_symbol} ({holding.security_name}) 更新中...")

            # 株価取得
            price_data = StockPriceFetcher.get_current_price(
                holding.ticker_symbol,
                use_cache=False
            )

            if price_data:
                # 為替レート（外国株の場合）
                exchange_rate = 1.0
                if holding.currency == 'USD':
                    from app.services.exchange_rate_fetcher import ExchangeRateFetcher
                    rate_data = ExchangeRateFetcher.get_rate('USD', 'JPY')
                    if rate_data:
                        exchange_rate = rate_data.get('rate', 1.0)

                # 保有銘柄の株価を更新
                holding.update_current_price(
                    price_data.get('current_price'),
                    exchange_rate=exchange_rate,
                    previous_close=price_data.get('previous_close')
                )

                db.session.commit()

                print(f"[SUCCESS] {holding.ticker_symbol}: ¥{holding.current_price:,.2f}")
                success_count += 1
            else:
                print(f"[WARNING] {holding.ticker_symbol}: 株価取得失敗")
                failed_count += 1

        except Exception as e:
            print(f"[ERROR] {holding.ticker_symbol}: {str(e)}")
            failed_count += 1
            db.session.rollback()

    print()
    print(f"[INFO] 株価更新完了: 成功={success_count}, 失敗={failed_count}")

    return {'success': success_count, 'failed': failed_count}


def update_dividends():
    """全保有銘柄の配当データを更新"""
    print()
    print("=" * 60)
    print("配当データ更新")
    print("=" * 60)

    holdings = Holding.query.all()

    if not holdings:
        print("[INFO] 保有銘柄がありません")
        return {'success': 0, 'failed': 0}

    print(f"[INFO] {len(holdings)}銘柄の配当データを更新します...")

    success_count = 0
    failed_count = 0

    for holding in holdings:
        try:
            print(f"[INFO] {holding.ticker_symbol} 配当データ取得中...")

            dividends = DividendFetcher.fetch_dividends(holding.ticker_symbol)

            if dividends:
                print(f"[SUCCESS] {holding.ticker_symbol}: {len(dividends)}件の配当データ")
                success_count += 1
            else:
                print(f"[INFO] {holding.ticker_symbol}: 配当データなし")

        except Exception as e:
            print(f"[ERROR] {holding.ticker_symbol}: {str(e)}")
            failed_count += 1

    print()
    print(f"[INFO] 配当データ更新完了: 成功={success_count}, 失敗={failed_count}")

    return {'success': success_count, 'failed': failed_count}


def update_stock_metrics():
    """全保有銘柄の評価指標を更新"""
    print()
    print("=" * 60)
    print("評価指標更新")
    print("=" * 60)

    try:
        results = StockMetricsFetcher.update_all_holdings_metrics()

        print()
        print(f"[INFO] 評価指標更新完了: 成功={results['success']}, 失敗={results['failed']}")

        return results

    except Exception as e:
        print(f"[ERROR] 評価指標更新エラー: {str(e)}")
        return {'success': 0, 'failed': 0}


def update_benchmarks():
    """ベンチマーク価格を更新"""
    print()
    print("=" * 60)
    print("ベンチマーク価格更新")
    print("=" * 60)

    benchmarks = [
        ('^N225', '日経平均株価'),
        ('^GSPC', 'S&P 500')
    ]

    success_count = 0
    failed_count = 0

    for ticker, name in benchmarks:
        try:
            print(f"[INFO] {name} ({ticker}) 更新中...")

            price_data = BenchmarkFetcher.get_current_price(ticker)

            if price_data:
                # データベースに保存
                BenchmarkFetcher.save_price(ticker, price_data)

                print(f"[SUCCESS] {name}: {price_data.get('current_price'):,.2f}")
                success_count += 1
            else:
                print(f"[WARNING] {name}: 価格取得失敗")
                failed_count += 1

        except Exception as e:
            print(f"[ERROR] {name}: {str(e)}")
            failed_count += 1

    print()
    print(f"[INFO] ベンチマーク更新完了: 成功={success_count}, 失敗={failed_count}")

    return {'success': success_count, 'failed': failed_count}


def main():
    parser = argparse.ArgumentParser(
        description='Stock P&L Manager 全データ更新ツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
    # 全データ更新
    python scripts/update_all_data.py

    # 株価のみ更新
    python scripts/update_all_data.py --skip-dividends --skip-metrics --skip-benchmarks

    # 配当と評価指標を更新
    python scripts/update_all_data.py --skip-prices --skip-benchmarks
        """
    )

    parser.add_argument(
        '--skip-prices',
        action='store_true',
        help='株価更新をスキップ'
    )

    parser.add_argument(
        '--skip-dividends',
        action='store_true',
        help='配当更新をスキップ'
    )

    parser.add_argument(
        '--skip-metrics',
        action='store_true',
        help='評価指標更新をスキップ'
    )

    parser.add_argument(
        '--skip-benchmarks',
        action='store_true',
        help='ベンチマーク更新をスキップ'
    )

    args = parser.parse_args()

    # Flaskアプリケーションコンテキストを作成
    app = create_app(os.getenv('FLASK_ENV', 'development'))

    with app.app_context():
        print("=" * 60)
        print("Stock P&L Manager - 全データ更新")
        print("=" * 60)
        print(f"[INFO] 開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        results = {}

        # 株価更新
        if not args.skip_prices:
            results['prices'] = update_stock_prices()

        # 配当更新
        if not args.skip_dividends:
            results['dividends'] = update_dividends()

        # 評価指標更新
        if not args.skip_metrics:
            results['metrics'] = update_stock_metrics()

        # ベンチマーク更新
        if not args.skip_benchmarks:
            results['benchmarks'] = update_benchmarks()

        # 結果サマリー
        print()
        print("=" * 60)
        print("更新結果サマリー")
        print("=" * 60)

        total_success = sum(r.get('success', 0) for r in results.values())
        total_failed = sum(r.get('failed', 0) for r in results.values())

        for key, result in results.items():
            if result:
                print(f"{key:15s}: 成功={result.get('success', 0):3d}, 失敗={result.get('failed', 0):3d}")

        print("-" * 60)
        print(f"{'合計':15s}: 成功={total_success:3d}, 失敗={total_failed:3d}")
        print()
        print(f"[INFO] 完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        if total_failed > 0:
            sys.exit(1)


if __name__ == '__main__':
    main()
