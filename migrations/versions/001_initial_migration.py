"""Initial migration with all models

Revision ID: 001_initial
Revises:
Create Date: 2026-01-09 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### Create transactions table ###
    op.create_table('transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('ticker_symbol', sa.String(length=20), nullable=False),
        sa.Column('security_name', sa.String(length=200), nullable=True),
        sa.Column('transaction_type', sa.String(length=10), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('commission', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('settlement_amount', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('exchange_rate', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('settlement_currency', sa.String(length=3), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_transactions_ticker_symbol', 'transactions', ['ticker_symbol'], unique=False)
    op.create_index('ix_transactions_transaction_date', 'transactions', ['transaction_date'], unique=False)

    # ### Create holdings table ###
    op.create_table('holdings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker_symbol', sa.String(length=20), nullable=False),
        sa.Column('security_name', sa.String(length=200), nullable=True),
        sa.Column('total_quantity', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('average_cost', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('total_cost', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('current_price', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('previous_close', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('day_change_pct', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('current_value', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('unrealized_pnl', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('unrealized_pnl_pct', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker_symbol')
    )
    op.create_index('ix_holdings_ticker_symbol', 'holdings', ['ticker_symbol'], unique=False)

    # ### Create dividends table ###
    op.create_table('dividends',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker_symbol', sa.String(length=20), nullable=False),
        sa.Column('ex_dividend_date', sa.Date(), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=True),
        sa.Column('dividend_amount', sa.Numeric(precision=15, scale=6), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('total_dividend', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('quantity_held', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_dividends_ex_dividend_date', 'dividends', ['ex_dividend_date'], unique=False)
    op.create_index('ix_dividends_ticker_symbol', 'dividends', ['ticker_symbol'], unique=False)

    # ### Create stock_prices table ###
    op.create_table('stock_prices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker_symbol', sa.String(length=20), nullable=False),
        sa.Column('price_date', sa.Date(), nullable=False),
        sa.Column('close_price', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker_symbol', 'price_date', name='uix_ticker_date')
    )
    op.create_index('ix_stock_prices_price_date', 'stock_prices', ['price_date'], unique=False)
    op.create_index('ix_stock_prices_ticker_symbol', 'stock_prices', ['ticker_symbol'], unique=False)

    # ### Create realized_pnl table ###
    op.create_table('realized_pnl',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker_symbol', sa.String(length=20), nullable=False),
        sa.Column('sell_date', sa.Date(), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('average_cost', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('sell_price', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('realized_pnl', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('realized_pnl_pct', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('commission', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_realized_pnl_sell_date', 'realized_pnl', ['sell_date'], unique=False)
    op.create_index('ix_realized_pnl_ticker_symbol', 'realized_pnl', ['ticker_symbol'], unique=False)

    # ### Create stock_metrics table (Phase 10) ###
    op.create_table('stock_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker_symbol', sa.String(length=20), nullable=False),
        sa.Column('market_cap', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('beta', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('pe_ratio', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('eps', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('pb_ratio', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('ev_to_revenue', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('ev_to_ebitda', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('revenue', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('profit_margin', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('fifty_two_week_low', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('fifty_two_week_high', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('ytd_return', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('one_year_return', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker_symbol')
    )
    op.create_index('ix_stock_metrics_ticker_symbol', 'stock_metrics', ['ticker_symbol'], unique=False)


def downgrade():
    # Drop stock_metrics table
    op.drop_index('ix_stock_metrics_ticker_symbol', table_name='stock_metrics')
    op.drop_table('stock_metrics')

    # Drop realized_pnl table
    op.drop_index('ix_realized_pnl_ticker_symbol', table_name='realized_pnl')
    op.drop_index('ix_realized_pnl_sell_date', table_name='realized_pnl')
    op.drop_table('realized_pnl')

    # Drop stock_prices table
    op.drop_index('ix_stock_prices_ticker_symbol', table_name='stock_prices')
    op.drop_index('ix_stock_prices_price_date', table_name='stock_prices')
    op.drop_table('stock_prices')

    # Drop dividends table
    op.drop_index('ix_dividends_ticker_symbol', table_name='dividends')
    op.drop_index('ix_dividends_ex_dividend_date', table_name='dividends')
    op.drop_table('dividends')

    # Drop holdings table
    op.drop_index('ix_holdings_ticker_symbol', table_name='holdings')
    op.drop_table('holdings')

    # Drop transactions table
    op.drop_index('ix_transactions_transaction_date', table_name='transactions')
    op.drop_index('ix_transactions_ticker_symbol', table_name='transactions')
    op.drop_table('transactions')
