"""
パフォーマンス最適化のためのインデックスをデータベースに適用するスクリプト
"""
import sqlite3
import sys
from pathlib import Path

# データベースファイルのパス
DB_PATH = Path(__file__).parent / 'data' / 'stock_pnl.db'

# 追加するインデックスのSQL
INDEXES = [
    # 取引履歴テーブルのインデックス
    ("idx_transactions_ticker_date",
     "CREATE INDEX IF NOT EXISTS idx_transactions_ticker_date ON transactions(ticker_symbol, transaction_date DESC)"),

    ("idx_transactions_type",
     "CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type)"),

    # 株価履歴テーブルのインデックス
    ("idx_stock_prices_ticker_date",
     "CREATE INDEX IF NOT EXISTS idx_stock_prices_ticker_date ON stock_prices(ticker_symbol, price_date DESC)"),

    # 実現損益テーブルのインデックス
    ("idx_realized_pnl_sell_date",
     "CREATE INDEX IF NOT EXISTS idx_realized_pnl_sell_date ON realized_pnl(sell_date DESC)"),

    ("idx_realized_pnl_ticker",
     "CREATE INDEX IF NOT EXISTS idx_realized_pnl_ticker ON realized_pnl(ticker_symbol)"),

    # 配当履歴テーブルのインデックス
    ("idx_dividends_ex_date",
     "CREATE INDEX IF NOT EXISTS idx_dividends_ex_date ON dividends(ex_dividend_date DESC)"),

    ("idx_dividends_ticker",
     "CREATE INDEX IF NOT EXISTS idx_dividends_ticker ON dividends(ticker_symbol)"),

    # 保有銘柄テーブルのインデックス
    ("idx_holdings_last_updated",
     "CREATE INDEX IF NOT EXISTS idx_holdings_last_updated ON holdings(last_updated DESC)"),
]


def apply_indexes():
    """インデックスをデータベースに適用"""
    if not DB_PATH.exists():
        print(f"エラー: データベースファイルが見つかりません: {DB_PATH}")
        return False

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print("=" * 60)
        print("パフォーマンス最適化: インデックス追加開始")
        print("=" * 60)
        print()

        success_count = 0
        for index_name, sql in INDEXES:
            try:
                print(f"インデックスを作成中: {index_name}...", end=" ")
                cursor.execute(sql)
                success_count += 1
                print("[OK]")
            except Exception as e:
                print(f"[ERROR]: {e}")

        conn.commit()

        print()
        print("=" * 60)
        print(f"インデックス追加完了: {success_count}/{len(INDEXES)} 成功")
        print("=" * 60)
        print()

        # 作成されたインデックスの確認
        print("作成されたインデックス一覧:")
        print("-" * 60)
        cursor.execute("""
            SELECT name, tbl_name
            FROM sqlite_master
            WHERE type = 'index'
              AND name LIKE 'idx_%'
            ORDER BY tbl_name, name
        """)

        for row in cursor.fetchall():
            print(f"  {row[1]:20s} -> {row[0]}")

        print()

        # インデックスのサイズ情報
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();")
        db_size = cursor.fetchone()[0]
        print(f"データベースサイズ: {db_size:,} bytes ({db_size/1024/1024:.2f} MB)")

        conn.close()
        return True

    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        return False


if __name__ == '__main__':
    success = apply_indexes()
    sys.exit(0 if success else 1)
