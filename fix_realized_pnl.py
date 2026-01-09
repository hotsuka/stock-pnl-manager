import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.services.transaction_service import TransactionService

app = create_app()

def fix_all_realized_pnl():
    with app.app_context():
        print("Starting recalculation of all holdings and realized P&L...")
        TransactionService.recalculate_all_holdings()
        print("Recalculation complete. Database updated with correct JPY P&L.")

if __name__ == "__main__":
    fix_all_realized_pnl()
