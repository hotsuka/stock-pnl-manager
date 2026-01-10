"""ベンチマーク指数取得サービス"""
import ssl
import os
from datetime import datetime, date, timedelta
from decimal import Decimal
import yfinance as yf
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.benchmark_price import BenchmarkPrice
from app.services.exchange_rate_fetcher import ExchangeRateFetcher
from app.utils.logger import get_logger, log_external_api_call

# SSL証明書検証の無効化（日本語ユーザー名パス問題対策）
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''

logger = get_logger(__name__)


class BenchmarkFetcher:
    """ベンチマーク指数取得サービス"""

    BENCHMARKS = {
        'TOPIX': {
            'ticker': '^N225',  # TOPIXが利用不可のため日経平均を使用
            'name': '日経平均225',
            'currency': 'JPY',
            'country': 'Japan'
        },
        'SP500': {
            'ticker': '^GSPC',
            'name': 'S&P 500',
            'currency': 'USD',
            'country': 'USA'
        },
        'N225': {
            'ticker': '^N225',
            'name': '日経平均225',
            'currency': 'JPY',
            'country': 'Japan'
        }
    }

    @staticmethod
    def get_benchmark_price(benchmark_key, use_cache=True):
        """
        ベンチマーク指数の現在価格を取得

        Args:
            benchmark_key: 'TOPIX', 'SP500', 'N225'
            use_cache: キャッシュ使用フラグ

        Returns:
            {'price': float, 'currency': str, 'timestamp': datetime,
             'previous_close': float} または None
        """
        benchmark = BenchmarkFetcher.BENCHMARKS.get(benchmark_key)
        if not benchmark:
            logger.error(f"Unknown benchmark key: {benchmark_key}")
            return None

        ticker_symbol = benchmark['ticker']

        # キャッシュチェック
        if use_cache:
            today = datetime.now().date()
            cached = BenchmarkPrice.query.filter_by(
                benchmark_key=benchmark_key,
                price_date=today
            ).first()

            if cached:
                logger.info(f"Benchmark price loaded from cache: {benchmark_key}")
                return {
                    'benchmark_key': benchmark_key,
                    'ticker': ticker_symbol,
                    'name': benchmark['name'],
                    'price': float(cached.close_price),
                    'currency': cached.currency,
                    'previous_close': float(cached.previous_close) if cached.previous_close else None,
                    'timestamp': cached.created_at
                }

        # yfinanceで取得
        try:
            logger.info(f"Fetching benchmark price from yfinance: {ticker_symbol}")
            ticker = yf.Ticker(ticker_symbol)

            # info取得を試行
            price = None
            previous_close = None

            try:
                info = ticker.info
                price = info.get('currentPrice') or info.get('regularMarketPrice')
                previous_close = info.get('previousClose')
            except Exception as info_error:
                logger.warning(f"Info fetch failed for {ticker_symbol}, fallback to history: {info_error}")

            # history フォールバック
            if price is None:
                hist = ticker.history(period='5d')
                if hist.empty:
                    log_external_api_call(logger, 'yfinance', f'get_benchmark/{ticker_symbol}',
                                        success=False, error='履歴データが空')
                    return None

                price = float(hist['Close'].iloc[-1])
                if len(hist) >= 2:
                    previous_close = float(hist['Close'].iloc[-2])

            if price is None:
                log_external_api_call(logger, 'yfinance', f'get_benchmark/{ticker_symbol}',
                                    success=False, error='価格データが取得できませんでした')
                return None

            log_external_api_call(logger, 'yfinance', f'get_benchmark/{ticker_symbol}',
                                success=True)

            # キャッシュに保存
            BenchmarkFetcher._cache_benchmark(
                benchmark_key,
                price,
                benchmark['currency'],
                previous_close
            )

            return {
                'benchmark_key': benchmark_key,
                'ticker': ticker_symbol,
                'name': benchmark['name'],
                'price': float(price),
                'currency': benchmark['currency'],
                'previous_close': float(previous_close) if previous_close else None,
                'timestamp': datetime.now()
            }

        except Exception as e:
            logger.error(f"Error fetching benchmark price ({benchmark_key}): {str(e)}")
            log_external_api_call(logger, 'yfinance', f'get_benchmark/{ticker_symbol}',
                                success=False, error=str(e))
            return None

    @staticmethod
    def get_historical_benchmark(benchmark_key, start_date, end_date):
        """
        ベンチマーク指数の履歴データ取得

        Args:
            benchmark_key: 'TOPIX', 'SP500', 'N225'
            start_date: 開始日 (date object)
            end_date: 終了日 (date object)

        Returns:
            [{'date': date, 'close': float, 'previous_close': float}]
        """
        benchmark = BenchmarkFetcher.BENCHMARKS.get(benchmark_key)
        if not benchmark:
            logger.error(f"Unknown benchmark key: {benchmark_key}")
            return []

        ticker_symbol = benchmark['ticker']

        # キャッシュから取得を試みる
        cached_data = BenchmarkPrice.query.filter(
            BenchmarkPrice.benchmark_key == benchmark_key,
            BenchmarkPrice.price_date >= start_date,
            BenchmarkPrice.price_date <= end_date
        ).order_by(BenchmarkPrice.price_date).all()

        # キャッシュが十分にあるかチェック（期待日数の80%以上）
        expected_days = (end_date - start_date).days + 1
        if len(cached_data) >= expected_days * 0.8:
            logger.info(f"Benchmark historical data loaded from cache: {benchmark_key} ({len(cached_data)} days)")
            result = []
            for i, item in enumerate(cached_data):
                result.append({
                    'date': item.price_date,
                    'close': float(item.close_price),
                    'previous_close': float(item.previous_close) if item.previous_close else (
                        float(cached_data[i-1].close_price) if i > 0 else None
                    )
                })
            return result

        # yfinanceで取得
        try:
            logger.info(f"Fetching benchmark historical data from yfinance: {ticker_symbol} ({start_date} to {end_date})")
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(start=start_date, end=end_date + timedelta(days=1))

            if hist.empty:
                log_external_api_call(logger, 'yfinance', f'get_benchmark_history/{ticker_symbol}',
                                    params={'start': str(start_date), 'end': str(end_date)},
                                    success=False, error='履歴データが空')
                return []

            log_external_api_call(logger, 'yfinance', f'get_benchmark_history/{ticker_symbol}',
                                params={'start': str(start_date), 'end': str(end_date)},
                                success=True)

            # データを処理してキャッシュ保存
            result = []
            previous_close_value = None

            for idx, (date_timestamp, row) in enumerate(hist.iterrows()):
                price_date = date_timestamp.date()
                close_price = float(row['Close'])

                # キャッシュに保存
                BenchmarkFetcher._cache_benchmark(
                    benchmark_key,
                    close_price,
                    benchmark['currency'],
                    previous_close_value,
                    price_date
                )

                result.append({
                    'date': price_date,
                    'close': close_price,
                    'previous_close': previous_close_value
                })

                previous_close_value = close_price

            logger.info(f"Benchmark historical data fetched: {benchmark_key} ({len(result)} days)")
            return result

        except Exception as e:
            logger.error(f"Error fetching benchmark historical data ({benchmark_key}): {str(e)}")
            log_external_api_call(logger, 'yfinance', f'get_benchmark_history/{ticker_symbol}',
                                params={'start': str(start_date), 'end': str(end_date)},
                                success=False, error=str(e))
            return []

    @staticmethod
    def get_multiple_benchmarks(benchmark_keys, start_date, end_date):
        """
        複数ベンチマークの履歴を一括取得

        Args:
            benchmark_keys: ['TOPIX', 'SP500'] など
            start_date: 開始日
            end_date: 終了日

        Returns:
            {
                'TOPIX': [{'date': date, 'close': float, 'previous_close': float}],
                'SP500': [...]
            }
        """
        result = {}

        for key in benchmark_keys:
            data = BenchmarkFetcher.get_historical_benchmark(key, start_date, end_date)
            result[key] = data

        return result

    @staticmethod
    def _cache_benchmark(benchmark_key, price, currency, previous_close=None, price_date=None):
        """
        ベンチマーク指数をキャッシュに保存

        Args:
            benchmark_key: 'TOPIX', 'SP500', etc.
            price: 終値
            currency: 通貨
            previous_close: 前日終値
            price_date: 価格の日付（デフォルト: 今日）
        """
        if price_date is None:
            price_date = datetime.now().date()

        try:
            existing = BenchmarkPrice.query.filter_by(
                benchmark_key=benchmark_key,
                price_date=price_date
            ).first()

            if existing:
                # 既存レコードを更新
                existing.close_price = Decimal(str(price))
                if previous_close is not None:
                    existing.previous_close = Decimal(str(previous_close))
            else:
                # 新規レコードを作成
                bp = BenchmarkPrice(
                    benchmark_key=benchmark_key,
                    price_date=price_date,
                    close_price=Decimal(str(price)),
                    currency=currency,
                    previous_close=Decimal(str(previous_close)) if previous_close is not None else None
                )
                db.session.add(bp)

            db.session.commit()

        except IntegrityError as e:
            db.session.rollback()
            logger.debug(f"Benchmark price already cached (race condition): {benchmark_key} {price_date}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error caching benchmark price: {e}")
