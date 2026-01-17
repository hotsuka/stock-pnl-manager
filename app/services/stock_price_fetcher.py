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
from app.services.exchange_rate_fetcher import ExchangeRateFetcher
from app.models.holding import Holding
from sqlalchemy.exc import IntegrityError
from app.utils.logger import get_logger, log_external_api_call

logger = get_logger("stock_price_fetcher")

# Disable SSL verification to work around Japanese username path issue
import os

os.environ["PYTHONHTTPSVERIFY"] = "0"
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
os.environ["SSL_CERT_FILE"] = ""
ssl._create_default_https_context = ssl._create_unverified_context

# Force yfinance to use requests instead of curl_cffi
import yfinance as yf_module

yf_module.utils.get_yf_logger().setLevel("CRITICAL")


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
                ticker_symbol=ticker_symbol, price_date=today
            ).first()

            if cached:
                return {
                    "price": float(cached.close_price),
                    "currency": cached.currency,
                    "timestamp": cached.created_at,
                    "source": "cache",
                }

        # Fetch from Yahoo Finance
        try:
            # Add market suffix for Japanese stocks
            yf_ticker = StockPriceFetcher._format_ticker(ticker_symbol)
            log_external_api_call(
                logger, "yfinance", f"get_price/{yf_ticker}", success=True
            )

            stock = yf.Ticker(yf_ticker)

            # Get fast info for current price
            try:
                price = stock.info.get("currentPrice") or stock.info.get(
                    "regularMarketPrice"
                )
                currency = stock.info.get("currency", "USD")
            except Exception as e:
                logger.warning(
                    f"Info取得失敗 ({ticker_symbol}), 履歴データにフォールバック: {str(e)}"
                )
                # Fallback to history if info fails
                hist = stock.history(period="1d")
                if hist.empty:
                    log_external_api_call(
                        logger,
                        "yfinance",
                        f"get_price/{yf_ticker}",
                        success=False,
                        error="履歴データが空",
                    )
                    return None
                price = float(hist["Close"].iloc[-1])
                currency = (
                    stock.info.get("currency", "USD")
                    if hasattr(stock, "info")
                    else "USD"
                )

            if price is None:
                log_external_api_call(
                    logger,
                    "yfinance",
                    f"get_price/{yf_ticker}",
                    success=False,
                    error="価格がNull",
                )
                return None

            # Cache the price
            StockPriceFetcher._cache_price(ticker_symbol, price, currency)

            # Get previous close
            previous_close = stock.info.get("previousClose")
            if previous_close is None:
                # Try to get from history if info is missing
                # We already fetched history if logic fell through, but let's be sure
                if "hist" not in locals() or hist.empty:
                    hist = stock.history(period="5d")  # fetch a bit more to be safe

                if not hist.empty and len(hist) >= 2:
                    previous_close = float(hist["Close"].iloc[-2])

            result = {
                "price": float(price),
                "currency": currency,
                "timestamp": datetime.now(),
                "source": "yahoo_finance",
            }

            if previous_close:
                result["previous_close"] = float(previous_close)

            logger.info(f"株価取得成功: {ticker_symbol} = {price} {currency}")
            return result

        except Exception as e:
            logger.error(f"株価取得エラー ({ticker_symbol}): {str(e)}")
            log_external_api_call(
                logger,
                "yfinance",
                f"get_price/{ticker_symbol}",
                success=False,
                error=str(e),
            )
            return None

    @staticmethod
    def get_multiple_prices(ticker_symbols, use_cache=True):
        """
        Get current prices for multiple tickers (optimized batch processing)

        Args:
            ticker_symbols: List of ticker symbols
            use_cache: Whether to use cached prices

        Returns:
            dict: {ticker: {'price': float, 'currency': str, ...}}
        """
        import yfinance as yf
        from datetime import datetime

        results = {}
        uncached_tickers = []

        # Step 1: キャッシュから取得
        if use_cache:
            today = datetime.now().date()
            for ticker in ticker_symbols:
                cached = StockPrice.query.filter_by(
                    ticker_symbol=ticker, price_date=today
                ).first()

                if cached:
                    results[ticker] = {
                        "price": float(cached.close_price),
                        "currency": cached.currency,
                        "timestamp": cached.created_at,
                        "previous_close": (
                            float(cached.open_price) if cached.open_price else None
                        ),
                        "source": "cache",
                    }
                else:
                    uncached_tickers.append(ticker)
        else:
            uncached_tickers = list(ticker_symbols)

        # Step 2: キャッシュにないものをバッチ取得
        if uncached_tickers:
            batch_size = 15  # yfinanceの推奨バッチサイズ
            for i in range(0, len(uncached_tickers), batch_size):
                batch = uncached_tickers[i : i + batch_size]

                # yfinance形式に変換
                yf_tickers = [StockPriceFetcher._format_ticker(t) for t in batch]

                try:
                    # バッチで一括取得
                    tickers_obj = yf.Tickers(" ".join(yf_tickers))

                    for original_ticker, yf_ticker in zip(batch, yf_tickers):
                        try:
                            ticker_data = tickers_obj.tickers[yf_ticker]
                            info = ticker_data.info

                            price = info.get("currentPrice") or info.get(
                                "regularMarketPrice"
                            )
                            currency = info.get("currency", "USD")
                            previous_close = info.get("previousClose")

                            if price:
                                results[original_ticker] = {
                                    "price": float(price),
                                    "currency": currency,
                                    "timestamp": datetime.now(),
                                    "previous_close": (
                                        float(previous_close)
                                        if previous_close
                                        else None
                                    ),
                                    "source": "api",
                                }

                                # キャッシュに保存
                                StockPriceFetcher._cache_price(
                                    original_ticker, price, currency
                                )
                        except Exception as e:
                            print(f"Error fetching {original_ticker}: {e}")
                            continue

                except Exception as e:
                    print(f"Batch fetch error: {e}")
                    # フォールバック: 個別取得
                    for ticker in batch:
                        price_data = StockPriceFetcher.get_current_price(
                            ticker, use_cache=False
                        )
                        if price_data:
                            results[ticker] = price_data

        return results

    @staticmethod
    def update_all_holdings_prices():
        """
        Update current prices for all holdings (optimized batch processing)

        Returns:
            dict: Summary of updates
        """
        holdings = Holding.query.all()
        results = {"success": 0, "failed": 0, "errors": []}

        if not holdings:
            return results

        # Step 1: 銘柄リストを収集
        ticker_symbols = [h.ticker_symbol for h in holdings]

        # Step 2: すべての株価を一括取得（バッチ処理で最適化）
        print(f"Fetching prices for {len(ticker_symbols)} holdings...")
        prices_data = StockPriceFetcher.get_multiple_prices(
            ticker_symbols, use_cache=False
        )

        # Step 3: 株価データから実際の通貨を収集して為替レートを一括取得
        # 保有銘柄の currency ではなく、株価データから取得した実際の通貨を使用
        currencies_needed = set()
        for ticker, price_data in prices_data.items():
            actual_currency = price_data.get("currency", "USD")
            if actual_currency and actual_currency not in ["JPY", "日本円"]:
                currencies_needed.add(actual_currency)

        exchange_rates = {"JPY": 1.0, "日本円": 1.0}
        if currencies_needed:
            print(
                f"Fetching exchange rates for {len(currencies_needed)} currencies: {currencies_needed}"
            )
            for currency in currencies_needed:
                rate_data = ExchangeRateFetcher.get_exchange_rate(currency, "JPY")
                if rate_data:
                    exchange_rates[currency] = rate_data["rate"]
                else:
                    exchange_rates[currency] = 1.0  # フォールバック

        # Step 4: 各保有銘柄を更新
        for holding in holdings:
            try:
                price_data = prices_data.get(holding.ticker_symbol)

                if price_data:
                    # 株価データから実際の通貨を取得
                    actual_currency = price_data.get("currency", "USD")

                    # 保有銘柄の通貨が間違っている場合は修正
                    if holding.currency != actual_currency:
                        logger.info(
                            f"通貨修正: {holding.ticker_symbol} {holding.currency} -> {actual_currency}"
                        )
                        holding.currency = actual_currency

                    # 実際の通貨に基づいて為替レートを取得
                    exchange_rate = exchange_rates.get(actual_currency, 1.0)

                    # Update holding with new price and exchange rate
                    previous_close = price_data.get("previous_close")
                    holding.update_current_price(
                        price_data["price"], exchange_rate, previous_close
                    )
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(
                        {
                            "ticker": holding.ticker_symbol,
                            "error": "Failed to fetch price",
                        }
                    )
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(
                    {"ticker": holding.ticker_symbol, "error": str(e)}
                )

        # Step 5: データベースに一括コミット
        try:
            db.session.commit()
            print(f"Updated {results['success']}/{len(holdings)} holdings successfully")
        except Exception as e:
            db.session.rollback()
            results["errors"].append({"error": f"Database commit failed: {str(e)}"})

        # Step 6: 評価指標の更新
        try:
            from app.services.stock_metrics_fetcher import StockMetricsFetcher

            logger.info("株価更新後の評価指標更新を開始")
            metrics_results = StockMetricsFetcher.update_all_holdings_metrics()
            results["metrics"] = metrics_results
            logger.info(
                f"評価指標更新完了: 成功={metrics_results['success']}, 失敗={metrics_results['failed']}"
            )
        except Exception as e:
            logger.warning(f"評価指標更新スキップ: {str(e)}")
            results["metrics"] = {"success": 0, "failed": 0, "error": str(e)}

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
            currency = (
                stock.info.get("currency", "USD") if hasattr(stock, "info") else "USD"
            )

            # Cache historical prices
            for date, row in hist.iterrows():
                StockPriceFetcher._cache_price(
                    ticker_symbol, float(row["Close"]), currency, date.date()
                )

            return [
                {
                    "date": date.date(),
                    "close": float(row["Close"]),
                    "currency": currency,
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
                ticker_symbol=ticker_symbol, price_date=price_date
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
                    currency=currency,
                )
                db.session.add(stock_price)

            db.session.commit()

        except IntegrityError:
            # Handle race condition
            db.session.rollback()
        except Exception as e:
            db.session.rollback()
            print(f"Error caching price: {e}")
