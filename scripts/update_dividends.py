"""Update dividend data from Yahoo Finance"""
import ssl
import yfinance as yf
import pandas as pd
from decimal import Decimal
from datetime import datetime, timedelta
from app import create_app, db
from app.models.transaction import Transaction
from app.models.dividend import Dividend
from sqlalchemy import func

# Disable SSL verification
import os
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context

def format_ticker(ticker_symbol):
    """Format ticker symbol for Yahoo Finance"""
    if ticker_symbol.isdigit():
        return f"{ticker_symbol}.T"
    return ticker_symbol

def get_currency_from_ticker(ticker_symbol):
    """Determine currency from ticker symbol"""
    if ticker_symbol.endswith('.T'):
        return 'JPY'
    elif ticker_symbol.endswith('.KS'):
        return 'KRW'
    else:
        return 'USD'

def get_holdings_at_date(ticker_symbol, target_date):
    """Calculate holdings quantity at a specific date"""
    transactions = Transaction.query.filter(
        Transaction.ticker_symbol == ticker_symbol,
        Transaction.transaction_date <= target_date
    ).order_by(Transaction.transaction_date).all()

    total_quantity = Decimal('0')
    for t in transactions:
        if t.transaction_type == 'BUY':
            total_quantity += t.quantity
        elif t.transaction_type == 'SELL':
            total_quantity -= t.quantity

    return total_quantity

def get_exchange_rate_at_date(ticker_symbol, target_date):
    """Get exchange rate from transactions near the target date"""
    currency = get_currency_from_ticker(ticker_symbol)

    if currency == 'JPY':
        return Decimal('1')

    # Find transaction closest to the target date
    # First try within 30 days before
    date_range_start = target_date - timedelta(days=30)

    transaction = Transaction.query.filter(
        Transaction.ticker_symbol == ticker_symbol,
        Transaction.transaction_date >= date_range_start,
        Transaction.transaction_date <= target_date,
        Transaction.exchange_rate.isnot(None)
    ).order_by(Transaction.transaction_date.desc()).first()

    if transaction and transaction.exchange_rate:
        return transaction.exchange_rate

    # If not found, try within 60 days after
    date_range_end = target_date + timedelta(days=60)

    transaction = Transaction.query.filter(
        Transaction.ticker_symbol == ticker_symbol,
        Transaction.transaction_date >= target_date,
        Transaction.transaction_date <= date_range_end,
        Transaction.exchange_rate.isnot(None)
    ).order_by(Transaction.transaction_date).first()

    if transaction and transaction.exchange_rate:
        return transaction.exchange_rate

    # Default exchange rates if no transaction found
    if currency == 'USD':
        return Decimal('150')  # Default USD/JPY rate
    elif currency == 'KRW':
        return Decimal('0.11')  # Default KRW/JPY rate

    return Decimal('1')

app = create_app()

with app.app_context():
    # Get all unique ticker symbols from transactions
    tickers = db.session.query(
        Transaction.ticker_symbol,
        func.min(Transaction.transaction_date).label('first_transaction_date')
    ).group_by(Transaction.ticker_symbol).all()

    print(f"Updating dividend data for {len(tickers)} stocks...")

    for ticker_info in tickers:
        ticker_symbol = ticker_info[0]
        first_transaction_date = ticker_info[1]

        try:
            yf_ticker = format_ticker(ticker_symbol)
            stock = yf.Ticker(yf_ticker)
            currency = get_currency_from_ticker(ticker_symbol)

            # Get dividend history
            try:
                dividends = stock.dividends

                if dividends.empty:
                    print(f"  [SKIP] {ticker_symbol}: No dividend data")
                    continue

                # Convert dividend index to timezone-naive if needed
                if hasattr(dividends.index, 'tz') and dividends.index.tz is not None:
                    dividends.index = dividends.index.tz_localize(None)

                # Filter dividends after first transaction
                first_transaction_datetime = pd.Timestamp(first_transaction_date)
                dividends = dividends[dividends.index >= first_transaction_datetime]

                if dividends.empty:
                    print(f"  [SKIP] {ticker_symbol}: No dividends after first transaction")
                    continue

                new_count = 0
                updated_count = 0

                for div_date, div_amount in dividends.items():
                    # Convert pandas Timestamp to datetime.date
                    div_date_only = div_date.date()

                    # Calculate holdings at dividend date
                    quantity_held = get_holdings_at_date(ticker_symbol, div_date_only)

                    if quantity_held <= 0:
                        continue  # Skip if no holdings at this date

                    # Calculate total dividend
                    total_dividend_foreign = float(div_amount) * float(quantity_held)

                    # Get exchange rate for foreign stocks
                    exchange_rate = get_exchange_rate_at_date(ticker_symbol, div_date_only)

                    # Convert to JPY
                    if currency == 'JPY':
                        total_dividend_jpy = Decimal(str(total_dividend_foreign))
                    else:
                        total_dividend_jpy = Decimal(str(total_dividend_foreign)) * exchange_rate

                    # Check if dividend already exists
                    existing = Dividend.query.filter_by(
                        ticker_symbol=ticker_symbol,
                        ex_dividend_date=div_date_only
                    ).first()

                    if existing:
                        # Update existing record
                        existing.dividend_amount = Decimal(str(div_amount))
                        existing.quantity_held = quantity_held
                        existing.total_dividend = total_dividend_jpy
                        existing.currency = currency
                        existing.source = 'yahoo'
                        updated_count += 1
                    else:
                        # Create new record
                        new_dividend = Dividend(
                            ticker_symbol=ticker_symbol,
                            ex_dividend_date=div_date_only,
                            dividend_amount=Decimal(str(div_amount)),
                            currency=currency,
                            total_dividend=total_dividend_jpy,
                            quantity_held=quantity_held,
                            source='yahoo'
                        )
                        db.session.add(new_dividend)
                        new_count += 1

                if new_count > 0 or updated_count > 0:
                    print(f"  [OK] {ticker_symbol}: {new_count} new, {updated_count} updated")
                else:
                    print(f"  [OK] {ticker_symbol}: No changes")

            except Exception as e:
                print(f"  [ERROR] {ticker_symbol}: Failed to get dividends - {e}")
                continue

        except Exception as e:
            print(f"  [ERROR] {ticker_symbol}: {e}")
            continue

    try:
        db.session.commit()
        print("\n[SUCCESS] Dividend data updated!")
    except Exception as e:
        db.session.rollback()
        print(f"\n[ERROR] Database save failed: {e}")
