"""株式評価指標取得サービス

Yahoo Financeから財務・株価指標を取得してデータベースに保存
"""

import time
from datetime import datetime, date, timedelta
import yfinance as yf
from app import db
from app.models import StockMetrics, Holding
from app.utils.logger import get_logger

logger = get_logger("stock_metrics_fetcher")


class StockMetricsFetcher:
    """株式評価指標取得クラス

    Yahoo Financeから12種類の評価指標を取得:
    - バリュエーション指標 (時価総額、Beta、PER、EPS、PBR)
    - 企業価値指標 (EV/Revenue、EV/EBITDA)
    - 財務指標 (売上、利益率)
    - 株価レンジ (52週高値・安値)
    - リターン指標 (YTD、1年)
    """

    @staticmethod
    def get_stock_metrics(ticker_symbol, use_cache=True):
        """単一銘柄の評価指標を取得

        Args:
            ticker_symbol (str): ティッカーシンボル
            use_cache (bool): キャッシュ使用フラグ（デフォルト: True）

        Returns:
            dict: 評価指標データ、取得失敗時はNone
        """
        try:
            # キャッシュチェック（当日データがあればreturn）
            if use_cache:
                cached = StockMetrics.query.filter_by(ticker_symbol=ticker_symbol).first()
                if cached and cached.last_updated:
                    if cached.last_updated.date() == date.today():
                        logger.info(f"キャッシュから評価指標取得: {ticker_symbol}")
                        return cached.to_dict()

            logger.info(f"評価指標取得開始: {ticker_symbol}")
            stock = yf.Ticker(ticker_symbol)

            # stock.infoから基本指標を取得
            info = stock.info
            if not info or "symbol" not in info:
                logger.warning(f"評価指標取得失敗（情報なし）: {ticker_symbol}")
                return None

            # 通貨の取得
            currency = info.get("currency", "USD")

            # 評価指標の抽出
            metrics_data = {
                "ticker_symbol": ticker_symbol,
                "market_cap": info.get("marketCap"),
                "beta": info.get("beta"),
                "pe_ratio": info.get("trailingPE"),
                "eps": info.get("trailingEps"),
                "pb_ratio": info.get("priceToBook"),
                "ev_to_revenue": info.get("enterpriseToRevenue"),
                "ev_to_ebitda": info.get("enterpriseToEbitda"),
                "revenue": info.get("totalRevenue"),
                "profit_margin": info.get("profitMargins"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                "currency": currency,
                "last_updated": datetime.utcnow(),
            }

            # YTD・1年リターンの計算
            returns = StockMetricsFetcher._calculate_returns(stock)
            metrics_data["ytd_return"] = returns.get("ytd_return")
            metrics_data["one_year_return"] = returns.get("one_year_return")

            # データベースに保存
            StockMetricsFetcher._save_metrics_to_db(ticker_symbol, metrics_data)

            logger.info(f"評価指標取得成功: {ticker_symbol}")
            return metrics_data

        except Exception as e:
            logger.error(f"評価指標取得エラー ({ticker_symbol}): {str(e)}")
            return None

    @staticmethod
    def _calculate_returns(stock):
        """YTD・1年リターンを計算

        Args:
            stock: yfinance Tickerオブジェクト

        Returns:
            dict: {'ytd_return': float, 'one_year_return': float}
        """
        try:
            # 過去2年分の履歴データを取得（安全マージン）
            hist = stock.history(period="2y")
            if hist.empty:
                logger.warning("履歴データが空のためリターン計算スキップ")
                return {"ytd_return": None, "one_year_return": None}

            current_price = hist["Close"].iloc[-1]

            # YTD Return: 年初からのリターン
            ytd_return = None
            year_start = date(date.today().year, 1, 1)
            # タイムスタンプをdateに変換
            try:
                year_start_data = hist[hist.index.date >= year_start]
            except AttributeError:
                # DatetimeIndexの場合
                year_start_data = hist[[d.date() >= year_start for d in hist.index]]

            if not year_start_data.empty:
                year_start_price = year_start_data["Close"].iloc[0]
                ytd_return = (current_price - year_start_price) / year_start_price

            # 1-Year Return: 365日前からのリターン
            one_year_return = None
            one_year_ago = date.today() - timedelta(days=365)
            try:
                one_year_data = hist[hist.index.date <= one_year_ago]
            except AttributeError:
                one_year_data = hist[[d.date() <= one_year_ago for d in hist.index]]

            if not one_year_data.empty:
                one_year_price = one_year_data["Close"].iloc[-1]
                one_year_return = (current_price - one_year_price) / one_year_price

            return {"ytd_return": ytd_return, "one_year_return": one_year_return}

        except Exception as e:
            logger.error(f"リターン計算エラー: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            return {"ytd_return": None, "one_year_return": None}

    @staticmethod
    def get_multiple_metrics(ticker_symbols, use_cache=True):
        """複数銘柄の評価指標を取得

        Args:
            ticker_symbols (list): ティッカーシンボルのリスト
            use_cache (bool): キャッシュ使用フラグ

        Returns:
            dict: {ticker: metrics_dict} 形式の辞書
        """
        results = {}
        for ticker in ticker_symbols:
            metrics = StockMetricsFetcher.get_stock_metrics(ticker, use_cache=use_cache)
            if metrics:
                results[ticker] = metrics
            time.sleep(0.1)  # レート制限対策

        logger.info(f"複数銘柄の評価指標取得完了: {len(results)}/{len(ticker_symbols)}件成功")
        return results

    @staticmethod
    def update_all_holdings_metrics():
        """全保有銘柄の評価指標を更新

        Returns:
            dict: {'success': int, 'failed': int, 'details': list}
        """
        logger.info("全保有銘柄の評価指標更新開始")

        holdings = Holding.query.all()
        ticker_symbols = [h.ticker_symbol for h in holdings]

        success_count = 0
        failed_count = 0
        details = []

        for ticker in ticker_symbols:
            try:
                metrics = StockMetricsFetcher.get_stock_metrics(ticker, use_cache=False)
                if metrics:
                    success_count += 1
                    details.append({"ticker": ticker, "status": "success"})
                else:
                    failed_count += 1
                    details.append({"ticker": ticker, "status": "failed", "reason": "取得失敗"})

                time.sleep(0.1)  # レート制限対策

            except Exception as e:
                failed_count += 1
                details.append({"ticker": ticker, "status": "failed", "reason": str(e)})
                logger.error(f"評価指標更新エラー ({ticker}): {str(e)}")

        logger.info(f"全保有銘柄の評価指標更新完了: 成功={success_count}, 失敗={failed_count}")

        return {"success": success_count, "failed": failed_count, "details": details}

    @staticmethod
    def _save_metrics_to_db(ticker_symbol, metrics_data):
        """評価指標をデータベースに保存（UPSERT）

        Args:
            ticker_symbol (str): ティッカーシンボル
            metrics_data (dict): 評価指標データ
        """
        try:
            # 既存レコードを検索
            metrics = StockMetrics.query.filter_by(ticker_symbol=ticker_symbol).first()

            if metrics:
                # 更新
                for key, value in metrics_data.items():
                    if key != "ticker_symbol":
                        setattr(metrics, key, value)
                logger.info(f"評価指標を更新: {ticker_symbol}")
            else:
                # 新規作成
                metrics = StockMetrics(**metrics_data)
                db.session.add(metrics)
                logger.info(f"評価指標を新規作成: {ticker_symbol}")

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            logger.error(f"評価指標保存エラー ({ticker_symbol}): {str(e)}")
            raise
