#!/usr/bin/env python
"""
既存データの通貨と評価額を修正するスクリプト

問題:
1. 外貨建て銘柄の currency が JPY になっている
2. current_value が為替換算されていない

修正内容:
1. ティッカーシンボルから正しい通貨を判定
2. holdingsとtransactionsの通貨を更新
3. 正しい為替レートで評価額を再計算
"""
import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent / 'venv' / 'Lib' / 'site-packages'))
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app
from app.models import Holding, Transaction
from app.services.csv_parser import CSVParser
from app.services.stock_price_fetcher import StockPriceFetcher
from app.services.exchange_rate_fetcher import ExchangeRateFetcher
from app import db


def detect_currency(ticker_symbol):
    """ティッカーシンボルから通貨を判定"""
    return CSVParser._detect_currency_from_ticker(ticker_symbol)


def fix_currencies():
    """データベース内の通貨情報を修正"""
    print("=" * 60)
    print("通貨情報の修正")
    print("=" * 60)

    app = create_app('development')

    with app.app_context():
        # 1. Transactionsの通貨を修正
        print("\n1. Transactionsテーブルの通貨を修正中...")
        transactions = Transaction.query.all()
        tx_updated = 0

        for tx in transactions:
            correct_currency = detect_currency(tx.ticker_symbol)
            if tx.currency != correct_currency:
                print(f"  修正: {tx.ticker_symbol} {tx.currency} → {correct_currency}")
                tx.currency = correct_currency
                tx.settlement_currency = correct_currency
                tx_updated += 1

        db.session.commit()
        print(f"  Transactions更新: {tx_updated}/{len(transactions)}件")

        # 2. Holdingsの通貨を修正
        print("\n2. Holdingsテーブルの通貨を修正中...")
        holdings = Holding.query.all()
        holding_updated = 0

        for holding in holdings:
            correct_currency = detect_currency(holding.ticker_symbol)
            if holding.currency != correct_currency:
                print(f"  修正: {holding.ticker_symbol} {holding.currency} → {correct_currency}")
                holding.currency = correct_currency
                holding_updated += 1

        db.session.commit()
        print(f"  Holdings更新: {holding_updated}/{len(holdings)}件")

        # 3. 評価額を再計算
        print("\n3. 株価と評価額を再計算中...")
        print("  これには数分かかる場合があります...\n")

        results = StockPriceFetcher.update_all_holdings_prices()

        print("\n" + "=" * 60)
        print("結果")
        print("=" * 60)
        print(f"株価更新成功: {results['success']}/{len(holdings)}件")
        print(f"株価更新失敗: {results['failed']}件")

        if results['failed'] > 0:
            print("\n失敗した銘柄:")
            for error in results['errors']:
                print(f"  ✗ {error.get('ticker', '不明')}: {error.get('error', '不明なエラー')}")

        # 4. 修正後のサンプルデータを表示
        print("\n" + "=" * 60)
        print("修正後のサンプルデータ")
        print("=" * 60)

        # 外貨建て銘柄のサンプルを表示
        foreign_holdings = Holding.query.filter(Holding.currency != 'JPY').limit(5).all()

        if foreign_holdings:
            print("\n外貨建て銘柄:")
            for h in foreign_holdings:
                print(f"\n{h.ticker_symbol} ({h.security_name})")
                print(f"  通貨: {h.currency}")
                print(f"  数量: {float(h.total_quantity)}")
                print(f"  現在価格: {float(h.current_price)} {h.currency}")
                print(f"  評価額: ¥{float(h.current_value):,.0f}")
                print(f"  取得コスト: ¥{float(h.total_cost):,.0f}")
                print(f"  損益: ¥{float(h.unrealized_pnl):,.0f} ({float(h.unrealized_pnl_pct):.2f}%)")

        # 日本株のサンプルを表示
        jpy_holdings = Holding.query.filter(Holding.currency == 'JPY').limit(3).all()

        if jpy_holdings:
            print("\n日本株:")
            for h in jpy_holdings:
                print(f"\n{h.ticker_symbol} ({h.security_name})")
                print(f"  通貨: {h.currency}")
                print(f"  数量: {float(h.total_quantity)}")
                print(f"  現在価格: ¥{float(h.current_price):,.0f}")
                print(f"  評価額: ¥{float(h.current_value):,.0f}")
                print(f"  取得コスト: ¥{float(h.total_cost):,.0f}")


if __name__ == '__main__':
    try:
        fix_currencies()
        print("\n" + "=" * 60)
        print("完了!")
        print("=" * 60)
        print("\nブラウザで http://localhost:5000/holdings にアクセスして、")
        print("「基本情報」タブで評価額が正しく表示されることを確認してください。")
    except KeyboardInterrupt:
        print("\n\n処理を中断しました")
    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()
