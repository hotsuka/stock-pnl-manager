#!/usr/bin/env python
"""Quick migration script that uses direct SQL execution"""
import sqlite3
from pathlib import Path
from datetime import datetime

# Database path
db_path = Path(__file__).parent / 'data' / 'stock_pnl.db'

def execute_migration():
    """Execute migration SQL directly"""
    print("="*60)
    print("Quick Database Migration")
    print("="*60)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Check current tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        current_tables = [row[0] for row in cursor.fetchall()]
        print(f"\nCurrent tables: {current_tables}")

        # If tables already exist (except alembic_version), skip creation
        if len(current_tables) > 1:
            print("\n[OK] Tables already exist! Checking structure...")
        else:
            print("\n[INFO] Creating tables...")

            # Create transactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_date DATE NOT NULL,
                    ticker_symbol VARCHAR(20) NOT NULL,
                    security_name VARCHAR(200),
                    transaction_type VARCHAR(10) NOT NULL,
                    currency VARCHAR(3) NOT NULL,
                    quantity NUMERIC(15,4) NOT NULL,
                    unit_price NUMERIC(15,4) NOT NULL,
                    commission NUMERIC(15,4),
                    settlement_amount NUMERIC(15,4),
                    exchange_rate NUMERIC(10,4),
                    settlement_currency VARCHAR(3),
                    created_at DATETIME,
                    updated_at DATETIME
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS ix_transactions_ticker_symbol ON transactions(ticker_symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS ix_transactions_transaction_date ON transactions(transaction_date)')
            print("  [OK] transactions table created")

            # Create holdings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker_symbol VARCHAR(20) NOT NULL UNIQUE,
                    security_name VARCHAR(200),
                    total_quantity NUMERIC(15,4) NOT NULL,
                    average_cost NUMERIC(15,4) NOT NULL,
                    currency VARCHAR(3) NOT NULL,
                    total_cost NUMERIC(15,4) NOT NULL,
                    current_price NUMERIC(15,4),
                    previous_close NUMERIC(15,4),
                    day_change_pct NUMERIC(10,4),
                    current_value NUMERIC(15,4),
                    unrealized_pnl NUMERIC(15,4),
                    unrealized_pnl_pct NUMERIC(10,4),
                    last_updated DATETIME,
                    created_at DATETIME
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS ix_holdings_ticker_symbol ON holdings(ticker_symbol)')
            print("  [OK] holdings table created")

            # Create dividends table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dividends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker_symbol VARCHAR(20) NOT NULL,
                    ex_dividend_date DATE NOT NULL,
                    payment_date DATE,
                    dividend_amount NUMERIC(15,6),
                    currency VARCHAR(3),
                    total_dividend NUMERIC(15,4),
                    quantity_held NUMERIC(15,4),
                    source VARCHAR(50),
                    created_at DATETIME
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS ix_dividends_ticker_symbol ON dividends(ticker_symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS ix_dividends_ex_dividend_date ON dividends(ex_dividend_date)')
            print("  [OK] dividends table created")

            # Create stock_prices table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker_symbol VARCHAR(20) NOT NULL,
                    price_date DATE NOT NULL,
                    close_price NUMERIC(15,4) NOT NULL,
                    currency VARCHAR(3),
                    created_at DATETIME,
                    UNIQUE(ticker_symbol, price_date)
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS ix_stock_prices_ticker_symbol ON stock_prices(ticker_symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS ix_stock_prices_price_date ON stock_prices(price_date)')
            print("  [OK] stock_prices table created")

            # Create realized_pnl table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS realized_pnl (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker_symbol VARCHAR(20) NOT NULL,
                    sell_date DATE NOT NULL,
                    quantity NUMERIC(15,4) NOT NULL,
                    average_cost NUMERIC(15,4) NOT NULL,
                    sell_price NUMERIC(15,4) NOT NULL,
                    realized_pnl NUMERIC(15,4) NOT NULL,
                    realized_pnl_pct NUMERIC(10,4),
                    commission NUMERIC(15,4),
                    currency VARCHAR(3),
                    created_at DATETIME
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS ix_realized_pnl_ticker_symbol ON realized_pnl(ticker_symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS ix_realized_pnl_sell_date ON realized_pnl(sell_date)')
            print("  [OK] realized_pnl table created")

            # Create stock_metrics table (Phase 10)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker_symbol VARCHAR(20) NOT NULL UNIQUE,
                    market_cap NUMERIC(20,2),
                    beta NUMERIC(10,4),
                    pe_ratio NUMERIC(10,2),
                    eps NUMERIC(15,4),
                    pb_ratio NUMERIC(10,2),
                    ev_to_revenue NUMERIC(10,2),
                    ev_to_ebitda NUMERIC(10,2),
                    revenue NUMERIC(20,2),
                    profit_margin NUMERIC(10,4),
                    fifty_two_week_low NUMERIC(15,4),
                    fifty_two_week_high NUMERIC(15,4),
                    ytd_return NUMERIC(10,4),
                    one_year_return NUMERIC(10,4),
                    currency VARCHAR(3),
                    last_updated DATETIME,
                    created_at DATETIME
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS ix_stock_metrics_ticker_symbol ON stock_metrics(ticker_symbol)')
            print("  [OK] stock_metrics table created")

        # Update alembic_version
        cursor.execute("DELETE FROM alembic_version")
        cursor.execute("INSERT INTO alembic_version (version_num) VALUES ('001_initial')")
        print("\n[OK] Migration version set to: 001_initial")

        # Commit changes
        conn.commit()

        # Verify tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        final_tables = [row[0] for row in cursor.fetchall()]
        print(f"\nFinal tables ({len(final_tables)}):")
        for table in sorted(final_tables):
            print(f"  [OK] {table}")

        # Check version
        cursor.execute("SELECT version_num FROM alembic_version")
        version = cursor.fetchone()
        print(f"\n[OK] Migration version: {version[0] if version else 'None'}")

        return True

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False

    finally:
        conn.close()

if __name__ == '__main__':
    print(f"Database: {db_path}")
    print(f"Exists: {db_path.exists()}\n")

    success = execute_migration()

    if success:
        print("\n" + "="*60)
        print("[SUCCESS] Migration completed successfully!")
        print("="*60)
        print("\nYou can now start the application:")
        print("  python run.py")
        exit(0)
    else:
        print("\n" + "="*60)
        print("[FAILED] Migration failed!")
        print("="*60)
        exit(1)
