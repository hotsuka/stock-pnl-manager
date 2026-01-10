"""
Dividend Data Fetcher Service

Fetches dividend data from multiple sources:
1. Yahoo Finance (primary)
2. TradingView (fallback - requires scraping)
3. Investing.com (fallback - requires scraping)
4. Manual entry

For initial implementation, we'll focus on Yahoo Finance
"""

import ssl
import yfinance as yf
from datetime import datetime, timedelta
from app import db
from app.models.dividend import Dividend
from app.models.holding import Holding

# Disable SSL verification to work around Japanese username path issue
import os
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context


class DividendFetcher:
    """Fetch dividend data from various sources"""

    @staticmethod
    def _calculate_quantity_at_date(ticker_symbol, target_date):
        """
        Calculate quantity held at a specific date

        Args:
            ticker_symbol: Stock ticker symbol
            target_date: Target date (datetime.date)

        Returns:
            float: Quantity held at that date
        """
        from app.models.transaction import Transaction
        from decimal import Decimal

        # Get all transactions up to and including the target date
        transactions = Transaction.query.filter(
            Transaction.ticker_symbol == ticker_symbol,
            Transaction.transaction_date <= target_date
        ).order_by(Transaction.transaction_date).all()

        quantity = Decimal('0')
        for tx in transactions:
            if tx.transaction_type == 'BUY':
                quantity += Decimal(str(tx.quantity))
            elif tx.transaction_type == 'SELL':
                quantity -= Decimal(str(tx.quantity))

        return float(quantity)

    @staticmethod
    def fetch_dividends_yahoo(ticker_symbol, start_date=None, end_date=None):
        """
        Fetch dividend data from Yahoo Finance

        Args:
            ticker_symbol: Stock ticker symbol
            start_date: Start date for dividend history (default: 5 years ago)
            end_date: End date for dividend history (default: today)

        Returns:
            list: [{'ex_date': datetime, 'amount': float, 'currency': str}]
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365 * 5)  # 過去5年分
        if end_date is None:
            end_date = datetime.now()

        try:
            # Format ticker for Yahoo Finance
            yf_ticker = DividendFetcher._format_ticker(ticker_symbol)
            stock = yf.Ticker(yf_ticker)

            # Get dividend history
            dividends = stock.dividends

            if dividends.empty:
                return []

            # Filter by date range - make sure dates are timezone-aware if dividends.index is
            import pandas as pd
            if hasattr(dividends.index, 'tz') and dividends.index.tz is not None:
                # dividends.index is timezone-aware, so convert our dates
                start_date_tz = pd.Timestamp(start_date).tz_localize(dividends.index.tz)
                end_date_tz = pd.Timestamp(end_date).tz_localize(dividends.index.tz)
                dividends = dividends[(dividends.index >= start_date_tz) & (dividends.index <= end_date_tz)]
            else:
                # dividends.index is timezone-naive
                dividends = dividends[(dividends.index >= start_date) & (dividends.index <= end_date)]

            # Get currency
            currency = stock.info.get('currency', 'USD') if hasattr(stock, 'info') else 'USD'

            # Convert to list of dicts
            dividend_list = []
            for date, amount in dividends.items():
                dividend_list.append({
                    'ex_date': date.date(),
                    'amount': float(amount),
                    'currency': currency,
                    'source': 'yahoo_finance'
                })

            return dividend_list

        except Exception as e:
            print(f"Error fetching dividends for {ticker_symbol}: {e}")
            return []

    @staticmethod
    def save_dividends_to_db(ticker_symbol, security_name=None):
        """
        Fetch dividends and save to database

        Args:
            ticker_symbol: Stock ticker symbol
            security_name: Optional security name

        Returns:
            dict: Summary of saved dividends
        """
        # Fetch from Yahoo Finance
        dividends = DividendFetcher.fetch_dividends_yahoo(ticker_symbol)

        results = {
            'ticker': ticker_symbol,
            'total': len(dividends),
            'new': 0,
            'existing': 0,
            'errors': []
        }

        for div_data in dividends:
            try:
                # Check if dividend already exists
                existing = Dividend.query.filter_by(
                    ticker_symbol=ticker_symbol,
                    ex_dividend_date=div_data['ex_date']
                ).first()

                if existing:
                    # Update existing dividend - recalculate quantity at ex-dividend date
                    quantity_held = DividendFetcher._calculate_quantity_at_date(
                        ticker_symbol,
                        div_data['ex_date']
                    )
                    existing.dividend_amount = div_data['amount']
                    existing.currency = div_data['currency']
                    existing.source = div_data['source']
                    existing.quantity_held = quantity_held
                    existing.total_dividend = float(div_data['amount']) * quantity_held
                    results['existing'] += 1
                else:
                    # Calculate quantity held at ex-dividend date
                    quantity_held = DividendFetcher._calculate_quantity_at_date(
                        ticker_symbol,
                        div_data['ex_date']
                    )

                    # Create new dividend record
                    dividend = Dividend(
                        ticker_symbol=ticker_symbol,
                        ex_dividend_date=div_data['ex_date'],
                        dividend_amount=div_data['amount'],
                        currency=div_data['currency'],
                        quantity_held=quantity_held,
                        total_dividend=float(div_data['amount']) * quantity_held,
                        source=div_data['source']
                    )
                    db.session.add(dividend)
                    results['new'] += 1

            except Exception as e:
                results['errors'].append({
                    'date': div_data['ex_date'],
                    'error': str(e)
                })

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            results['errors'].append({'error': f'Database commit failed: {str(e)}'})

        return results

    @staticmethod
    def update_all_holdings_dividends():
        """
        Fetch and save dividends for all holdings (including past holdings)

        Returns:
            dict: Summary of updates
        """
        from app.models.transaction import Transaction

        # Get all unique tickers from both current holdings and past transactions
        holdings = Holding.query.all()
        transactions = Transaction.query.all()

        # Build a map of ticker -> security_name
        ticker_info = {}

        # Add from holdings (current securities)
        for h in holdings:
            ticker_info[h.ticker_symbol] = h.security_name

        # Add from transactions (including sold securities)
        for t in transactions:
            if t.ticker_symbol not in ticker_info:
                ticker_info[t.ticker_symbol] = t.security_name

        results = {
            'total_holdings': len(ticker_info),
            'success': 0,
            'failed': 0,
            'details': []
        }

        for ticker_symbol, security_name in ticker_info.items():
            div_result = DividendFetcher.save_dividends_to_db(
                ticker_symbol,
                security_name
            )

            if div_result['errors']:
                results['failed'] += 1
            else:
                results['success'] += 1

            results['details'].append(div_result)

        return results

    @staticmethod
    def calculate_total_dividends(ticker_symbol=None, start_date=None, end_date=None):
        """
        Calculate total dividends received

        Args:
            ticker_symbol: Optional filter by ticker
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            dict: {'total_jpy': float, 'by_currency': {}, 'by_ticker': {}}
        """
        query = Dividend.query

        if ticker_symbol:
            query = query.filter_by(ticker_symbol=ticker_symbol)

        if start_date:
            query = query.filter(Dividend.ex_dividend_date >= start_date)

        if end_date:
            query = query.filter(Dividend.ex_dividend_date <= end_date)

        dividends = query.all()

        results = {
            'total_count': len(dividends),
            'by_currency': {},
            'by_ticker': {}
        }

        for div in dividends:
            # Sum by currency
            currency = div.currency or 'USD'
            if currency not in results['by_currency']:
                results['by_currency'][currency] = 0
            results['by_currency'][currency] += float(div.total_dividend or 0)

            # Sum by ticker
            if div.ticker_symbol not in results['by_ticker']:
                results['by_ticker'][div.ticker_symbol] = {
                    'total': 0,
                    'currency': currency,
                    'count': 0
                }
            results['by_ticker'][div.ticker_symbol]['total'] += float(div.total_dividend or 0)
            results['by_ticker'][div.ticker_symbol]['count'] += 1

        return results

    @staticmethod
    def _format_ticker(ticker_symbol):
        """
        Format ticker symbol for Yahoo Finance
        Japanese stocks need .T suffix
        """
        if ticker_symbol.isdigit():
            return f"{ticker_symbol}.T"
        return ticker_symbol

    @staticmethod
    def fetch_from_tradingview(ticker_symbol):
        """
        Fetch dividends from TradingView (future implementation)
        Requires web scraping

        Returns:
            list: Dividend data
        """
        # TODO: Implement TradingView scraping
        print("TradingView fetching not yet implemented")
        return []

    @staticmethod
    def fetch_from_investing_com(ticker_symbol):
        """
        Fetch dividends from Investing.com (future implementation)
        Requires web scraping

        Returns:
            list: Dividend data
        """
        # TODO: Implement Investing.com scraping
        print("Investing.com fetching not yet implemented")
        return []
