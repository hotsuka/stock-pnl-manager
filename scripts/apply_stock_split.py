"""株式分割を適用するスクリプト

使用方法:
    python scripts/apply_stock_split.py --ticker 3110.T --ratio 5 --date 2026-06-27
"""

import argparse
import os
import sys
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "development")

from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
os.environ.setdefault(
    "DATABASE_URL", f"sqlite:///{(base_dir / 'data' / 'stock_pnl.db').as_posix()}"
)

from app import create_app, db
from app.models.dividend import Dividend
from app.models.holding import Holding
from app.models.stock_price import StockPrice
from app.models.stock_split import StockSplit


def apply_stock_split(ticker_symbol, ratio, effective_date):
    """株式分割を適用"""
    ratio_dec = Decimal(str(ratio))

    # 重複チェック
    existing = StockSplit.query.filter_by(
        ticker_symbol=ticker_symbol,
        effective_date=effective_date,
    ).first()
    if existing:
        print(f"ERROR: この分割は既に適用済みです: {existing}")
        return False

    # 現在の保有情報を表示
    holding = Holding.query.filter_by(ticker_symbol=ticker_symbol).first()
    if holding:
        print(f"現在の保有情報:")
        print(f"  銘柄: {holding.ticker_symbol} ({holding.security_name})")
        print(f"  数量: {float(holding.total_quantity):.0f}株")
        print(f"  平均取得単価: {float(holding.average_cost):,.0f}円")
        print(f"  総取得コスト: {float(holding.total_cost):,.0f}円")
        print()

    # 分割レコードを記録
    split_record = StockSplit(
        ticker_symbol=ticker_symbol,
        effective_date=effective_date,
        ratio=ratio_dec,
    )
    db.session.add(split_record)

    # 保有銘柄を直接更新
    if holding:
        old_qty = float(holding.total_quantity)
        old_avg = float(holding.average_cost)

        holding.total_quantity = Decimal(str(old_qty)) * ratio_dec
        holding.average_cost = Decimal(str(old_avg)) / ratio_dec

        print(f"分割適用後:")
        print(f"  数量: {float(holding.total_quantity):.0f}株")
        print(f"  平均取得単価: {float(holding.average_cost):,.0f}円")
        print(f"  総取得コスト: {float(holding.total_cost):,.0f}円 (変更なし)")
        print()
    else:
        print(f"注意: {ticker_symbol} の保有レコードが見つかりません（分割記録のみ保存）")

    # stock_prices キャッシュを削除
    deleted_prices = StockPrice.query.filter_by(ticker_symbol=ticker_symbol).delete()
    print(f"stock_prices キャッシュ削除: {deleted_prices}件")

    # 配当金額を調整（分割前の履歴配当）
    dividends = Dividend.query.filter_by(ticker_symbol=ticker_symbol).all()
    adjusted_divs = 0
    for div in dividends:
        if div.dividend_amount:
            div.dividend_amount = Decimal(str(float(div.dividend_amount))) / ratio_dec
            adjusted_divs += 1
    if adjusted_divs:
        print(f"配当金額調整: {adjusted_divs}件 (÷{ratio})")

    db.session.commit()
    print(f"\n分割適用完了: {ticker_symbol} 1:{ratio} ({effective_date})")
    return True


def main():
    parser = argparse.ArgumentParser(description="株式分割を適用")
    parser.add_argument("--ticker", required=True, help="銘柄コード (例: 3110.T)")
    parser.add_argument(
        "--ratio", required=True, type=float, help="分割比率 (例: 5 = 1:5分割)"
    )
    parser.add_argument("--date", required=True, help="効力発生日 (YYYY-MM-DD)")
    args = parser.parse_args()

    effective_date = datetime.strptime(args.date, "%Y-%m-%d").date()

    app = create_app()
    with app.app_context():
        print("=" * 60)
        print(f"株式分割適用: {args.ticker} 1:{args.ratio} ({args.date})")
        print("=" * 60)
        print()
        apply_stock_split(args.ticker, args.ratio, effective_date)


if __name__ == "__main__":
    main()
