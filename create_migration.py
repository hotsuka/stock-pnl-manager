#!/usr/bin/env python
"""Create initial database migration"""
import os
import sys
from pathlib import Path

# Set environment variables
os.environ['FLASK_APP'] = 'run.py'
os.environ['FLASK_ENV'] = 'development'

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import create_app, db

def create_migration():
    """Create initial migration file"""
    print("="*60)
    print("Creating Initial Database Migration")
    print("="*60)

    app = create_app('development')

    with app.app_context():
        # Import all models
        from app.models import (
            Transaction, Holding, Dividend,
            StockPrice, RealizedPnl, StockMetrics
        )

        print("\nImported models:")
        print(f"  - Transaction: {Transaction.__tablename__}")
        print(f"  - Holding: {Holding.__tablename__}")
        print(f"  - Dividend: {Dividend.__tablename__}")
        print(f"  - StockPrice: {StockPrice.__tablename__}")
        print(f"  - RealizedPnl: {RealizedPnl.__tablename__}")
        print(f"  - StockMetrics: {StockMetrics.__tablename__}")

        # Ensure versions directory exists
        versions_dir = project_root / 'migrations' / 'versions'
        versions_dir.mkdir(parents=True, exist_ok=True)
        print(f"\nVersions directory: {versions_dir}")

        # Use Flask-Migrate to create migration
        from flask_migrate import migrate as create_migration_command

        print("\nGenerating migration file...")
        try:
            create_migration_command(message="Initial migration with all models")
            print("Migration file created successfully!")
            return True
        except Exception as e:
            print(f"Error creating migration: {e}")
            import traceback
            traceback.print_exc()

            # Try alternative method - create migration manually
            print("\nTrying alternative method...")
            return create_manual_migration()

def create_manual_migration():
    """Create migration file manually if automatic generation fails"""
    from datetime import datetime
    import hashlib

    # Generate revision ID
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    revision = hashlib.md5(timestamp.encode()).hexdigest()[:12]

    migration_content = '''"""Initial migration with all models

Revision ID: {revision}
Revises:
Create Date: {date}

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '{revision}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create transactions table
    op.create_table('transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('security_name', sa.String(length=200), nullable=True),
        sa.Column('transaction_type', sa.String(length=20), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('exchange_rate', sa.Float(), nullable=True),
        sa.Column('amount_jpy', sa.Float(), nullable=True),
        sa.Column('settlement_amount', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_transactions_date', 'transactions', ['date'], unique=False)
    op.create_index('idx_transactions_ticker', 'transactions', ['ticker'], unique=False)
    op.create_index('idx_transactions_type', 'transactions', ['transaction_type'], unique=False)

    # Create holdings table
    op.create_table('holdings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('security_name', sa.String(length=200), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('average_cost', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('current_price', sa.Float(), nullable=True),
        sa.Column('market_value', sa.Float(), nullable=True),
        sa.Column('unrealized_pnl', sa.Float(), nullable=True),
        sa.Column('unrealized_pnl_pct', sa.Float(), nullable=True),
        sa.Column('previous_close', sa.Float(), nullable=True),
        sa.Column('day_change_pct', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker')
    )
    op.create_index('idx_holdings_ticker', 'holdings', ['ticker'], unique=False)

    # Create dividends table
    op.create_table('dividends',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('security_name', sa.String(length=200), nullable=True),
        sa.Column('ex_date', sa.Date(), nullable=False),
        sa.Column('pay_date', sa.Date(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('exchange_rate', sa.Float(), nullable=True),
        sa.Column('amount_jpy', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_dividends_date', 'dividends', ['ex_date'], unique=False)
    op.create_index('idx_dividends_ticker', 'dividends', ['ticker'], unique=False)

    # Create stock_prices table
    op.create_table('stock_prices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('previous_close', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_stock_prices_date', 'stock_prices', ['date'], unique=False)
    op.create_index('idx_stock_prices_ticker', 'stock_prices', ['ticker'], unique=False)

    # Create realized_pnl table
    op.create_table('realized_pnl',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('security_name', sa.String(length=200), nullable=True),
        sa.Column('sale_date', sa.Date(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('average_cost', sa.Float(), nullable=False),
        sa.Column('sale_price', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=False),
        sa.Column('pnl_pct', sa.Float(), nullable=False),
        sa.Column('exchange_rate', sa.Float(), nullable=True),
        sa.Column('settlement_amount', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_realized_pnl_date', 'realized_pnl', ['sale_date'], unique=False)
    op.create_index('idx_realized_pnl_ticker', 'realized_pnl', ['ticker'], unique=False)

    # Create stock_metrics table
    op.create_table('stock_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('market_cap', sa.Float(), nullable=True),
        sa.Column('pe_ratio', sa.Float(), nullable=True),
        sa.Column('pb_ratio', sa.Float(), nullable=True),
        sa.Column('dividend_yield', sa.Float(), nullable=True),
        sa.Column('roe', sa.Float(), nullable=True),
        sa.Column('roa', sa.Float(), nullable=True),
        sa.Column('current_ratio', sa.Float(), nullable=True),
        sa.Column('debt_to_equity', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_stock_metrics_date', 'stock_metrics', ['date'], unique=False)
    op.create_index('idx_stock_metrics_ticker', 'stock_metrics', ['ticker'], unique=False)


def downgrade():
    op.drop_index('idx_stock_metrics_ticker', table_name='stock_metrics')
    op.drop_index('idx_stock_metrics_date', table_name='stock_metrics')
    op.drop_table('stock_metrics')

    op.drop_index('idx_realized_pnl_ticker', table_name='realized_pnl')
    op.drop_index('idx_realized_pnl_date', table_name='realized_pnl')
    op.drop_table('realized_pnl')

    op.drop_index('idx_stock_prices_ticker', table_name='stock_prices')
    op.drop_index('idx_stock_prices_date', table_name='stock_prices')
    op.drop_table('stock_prices')

    op.drop_index('idx_dividends_ticker', table_name='dividends')
    op.drop_index('idx_dividends_date', table_name='dividends')
    op.drop_table('dividends')

    op.drop_index('idx_holdings_ticker', table_name='holdings')
    op.drop_table('holdings')

    op.drop_index('idx_transactions_type', table_name='transactions')
    op.drop_index('idx_transactions_ticker', table_name='transactions')
    op.drop_index('idx_transactions_date', table_name='transactions')
    op.drop_table('transactions')
'''.format(
        revision=revision,
        date=datetime.utcnow().isoformat()
    )

    # Write migration file
    versions_dir = project_root / 'migrations' / 'versions'
    versions_dir.mkdir(parents=True, exist_ok=True)

    migration_file = versions_dir / f'{revision}_initial_migration.py'

    with open(migration_file, 'w', encoding='utf-8') as f:
        f.write(migration_content)

    print(f"Created migration file: {migration_file}")
    return True

if __name__ == '__main__':
    try:
        success = create_migration()
        if success:
            print("\n" + "="*60)
            print("Migration created successfully!")
            print("Run 'flask db upgrade' to apply the migration")
            print("="*60)
            sys.exit(0)
        else:
            print("\n" + "="*60)
            print("Failed to create migration")
            print("="*60)
            sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
