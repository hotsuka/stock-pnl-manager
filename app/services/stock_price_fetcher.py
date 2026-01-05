"""
Stock Price Fetcher Service

Fetches stock prices from Yahoo Finance using yfinance
Includes caching mechanism to reduce API calls
"""

import ssl
import certifi
import yfinance as yf
from datetime import datetime, timedelta
from app import db
from app.models.stock_price import StockPrice
from app.models.holding import Holding
from sqlalchemy.exc import IntegrityError

# Disable SSL verification to work around Japanese username path issue
import os
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context

# Force yfinance to use requests instead of curl_cffi
import yfinance as yf_module
yf_module.utils.get_yf_logger().setLevel('CRITICAL')


class StockPriceFetcher:
    """Fetch and cache stock prices from Yahoo Finance"""

    @staticmethod
    def get_current_price(ticker_symbol, use_cache=True):
        """
        Get current price for a single ticker

        Args:
            ticker_symbol: Stock ticker symbol (e.g., 'AAPL', '7203.T')
            use_cache: Whether to use cached price if available today

        Returns:
            dict: {'price': float, 'currency': str, 'timestamp': datetime}
            None: If fetch fails
        """
        # Check cache first
        if use_cache:
            today = datetime.now().date()
            cached = StockPrice.query.filter_by(
                ticker_symbol=ticker_symbol,
                price_date=today
            ).first()

            if cached:
                return {
                    'price': float(cached.close_price),
                    'currency': cached.currency,
                    'timestamp': cached.created_at,
                    'source': 'cache'
                }

        # Fetch from Yahoo Finance
        try:
            # Add market suffix for Japanese stocks
            yf_ticker = StockPriceFetcher._format_ticker(ticker_symbol)
            stock = yf.Ticker(yf_ticker)

            # Get fast info for current price
            try:
                price = stock.info.get('currentPrice') or stock.info.get('regularMarketPrice')
                currency = stock.info.get('currency', 'USD')
            except:
                # Fallback to history if info fails
                hist = stock.history(period='1d')
                if hist.empty:
                    return None
                price = float(hist['Close'].iloc[-1])
                currency = stock.info.get('currency', 'USD') if hasattr(stock, 'info') else 'USD'

            if price is None:
                return None

            # Cache the price
            StockPriceFetcher._cache_price(ticker_symbol, price, currency)

            return {
                'price': float(price),
                'currency': currency,
                'timestamp': datetime.now(),
                'source': 'yahoo_finance'
            }

        except Exception as e:
            print(f"Error fetching price for {ticker_symbol}: {e}")
            return None

    @staticmethod
    def get_multiple_prices(ticker_symbols, use_cache=True):
        """
        Get current prices for multiple tickers

        Args:
            ticker_symbols: List of ticker symbols
            use_cache: Whether to use cached prices

        Returns:
            dict: {ticker: {'price': float, 'currency': str, ...}}
        """
        results = {}
        for ticker in ticker_symbols:
            price_data = StockPriceFetcher.get_current_price(ticker, use_cache)
            if price_data:
                results[ticker] = price_data
        return results

    @staticmethod
    def update_all_holdings_prices():
        """
        Update current prices for all holdings

        Returns:
            dict: Summary of updates
        """
        holdings = Holding.query.all()
        results = {
            'success': 0,
            'failed': 0,
            'errors': []
        }

        for holding in holdings:
            price_data = StockPriceFetcher.get_current_price(holding.ticker_symbol)

            if price_data:
                # Update holding with new price
                holding.update_current_price(price_data['price'])
                results['success'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'ticker': holding.ticker_symbol,
                    'error': 'Failed to fetch price'
                })

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            results['errors'].append({'error': f'Database commit failed: {str(e)}'})

        return results

    @staticmethod
    def get_historical_prices(ticker_symbol, start_date, end_date):
        """
        Get historical prices for a ticker

        Args:
            ticker_symbol: Stock ticker symbol
            start_date: Start date (datetime or string 'YYYY-MM-DD')
            end_date: End date (datetime or string 'YYYY-MM-DD')

        Returns:
            list: [{'date': datetime, 'close': float, 'currency': str}]
        """
        try:
            yf_ticker = StockPriceFetcher._format_ticker(ticker_symbol)
            stock = yf.Ticker(yf_ticker)

            hist = stock.history(start=start_date, end=end_date)

            if hist.empty:
                return []

            # Get currency
            currency = stock.info.get('currency', 'USD') if hasattr(stock, 'info') else 'USD'

            # Cache historical prices
            for date, row in hist.iterrows():
                StockPriceFetcher._cache_price(
                    ticker_symbol,
                    float(row['Close']),
                    currency,
                    date.date()
                )

            return [
                {
                    'date': date.date(),
                    'close': float(row['Close']),
                    'currency': currency
                }
                for date, row in hist.iterrows()
            ]

        except Exception as e:
            print(f"Error fetching historical prices for {ticker_symbol}: {e}")
            return []

    @staticmethod
    def _format_ticker(ticker_symbol):
        """
        Format ticker symbol for Yahoo Finance
        Japanese stocks need .T suffix
        """
        # If ticker is numeric (Japanese stock), add .T suffix
        if ticker_symbol.isdigit():
            return f"{ticker_symbol}.T"
        return ticker_symbol

    @staticmethod
    def _cache_price(ticker_symbol, price, currency, price_date=None):
        """
        Cache price in database

        Args:
            ticker_symbol: Stock ticker
            price: Price value
            currency: Currency code
            price_date: Date for the price (default: today)
        """
        if price_date is None:
            price_date = datetime.now().date()

        try:
            # Check if already exists
            existing = StockPrice.query.filter_by(
                ticker_symbol=ticker_symbol,
                price_date=price_date
            ).first()

            if existing:
                # Update existing
                existing.close_price = price
                existing.currency = currency
            else:
                # Create new
                stock_price = StockPrice(
                    ticker_symbol=ticker_symbol,
                    price_date=price_date,
                    close_price=price,
                    currency=currency
                )
                db.session.add(stock_price)

            db.session.commit()

        except IntegrityError:
            # Handle race condition
            db.session.rollback()
        except Exception as e:
            db.session.rollback()
            print(f"Error caching price: {e}")
