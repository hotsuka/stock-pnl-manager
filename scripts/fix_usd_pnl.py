"""USD外国株（INTC・GD・COHR）の確定損益を再計算するスクリプト"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "development")

from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
os.environ.setdefault(
    "DATABASE_URL", f"sqlite:///{(base_dir / 'data' / 'stock_pnl.db').as_posix()}"
)

from dotenv import load_dotenv

load_dotenv(base_dir / ".env")

from app import create_app
from app.services.transaction_service import TransactionService
from app.models.realized_pnl import RealizedPnl
from app.models.holding import Holding

app = create_app(os.getenv("FLASK_ENV", "development"))

USD_TICKERS = ["INTC", "GD", "COHR"]

with app.app_context():
    print("=" * 60)
    print("USD外国株の確定損益を再計算します（日本株は対象外）")
    print("=" * 60)

    for ticker in USD_TICKERS:
        print(f"\n[{ticker}] 再計算前:")
        h = Holding.query.filter_by(ticker_symbol=ticker).first()
        pnl_list = RealizedPnl.query.filter_by(ticker_symbol=ticker).all()
        if h:
            print(f"  average_cost: {h.average_cost}")
        for r in pnl_list:
            print(f"  realized_pnl: {r.realized_pnl:.2f} JPY  ({r.sell_date})")

        try:
            TransactionService.recalculate_holding(ticker)
            print(f"  → 再計算完了")
        except Exception as e:
            print(f"  → エラー: {e}")
            continue

        print(f"[{ticker}] 再計算後:")
        h = Holding.query.filter_by(ticker_symbol=ticker).first()
        pnl_list = RealizedPnl.query.filter_by(ticker_symbol=ticker).all()
        if h:
            print(f"  average_cost: {h.average_cost}")
        for r in pnl_list:
            print(f"  realized_pnl: {r.realized_pnl:.2f} JPY  ({r.sell_date})")

    print("\n" + "=" * 60)
    print("完了。ブラウザをリフレッシュして確認してください。")
    print("=" * 60)
