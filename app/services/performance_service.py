import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta, date
from decimal import Decimal
from collections import defaultdict
from app import db
from app.models import Transaction, RealizedPnl, Dividend, Holding
from app.services.exchange_rate_fetcher import ExchangeRateFetcher


class PerformanceService:
    @staticmethod
    def get_split_adjustment_factor(yf_ticker, from_date, to_date):
        """
        指定期間の株式分割による調整係数を取得
        from_dateの価格をto_dateの分割調整後価格と比較可能にするための係数を返す

        Returns:
            float: 調整係数（分割があった場合は1より大きい/小さい値）
                   from_date価格 / 調整係数 = 分割調整後価格
        """
        try:
            ticker = yf.Ticker(yf_ticker)
            splits = ticker.splits

            if splits.empty:
                return 1.0

            # 期間内の分割のみを抽出
            # タイムゾーンを除去してから比較
            cumulative_ratio = 1.0

            for split_idx, ratio in splits.items():
                # インデックスからdateオブジェクトを取得
                if hasattr(split_idx, "date"):
                    split_date = split_idx.date()
                elif hasattr(split_idx, "to_pydatetime"):
                    split_date = split_idx.to_pydatetime().date()
                else:
                    # 変換できない場合はスキップ
                    continue

                # 期間内の分割のみを対象
                if from_date < split_date <= to_date:
                    cumulative_ratio *= ratio

            return cumulative_ratio

        except Exception as e:
            print(f"WARNING: Failed to get split data for {yf_ticker}: {e}")
            return 1.0

    @staticmethod
    def get_all_split_factors(tickers, start_date, end_date):
        """
        複数銘柄の分割調整係数を一括取得（キャッシュ用）

        Returns:
            dict: {yf_ticker: {date: cumulative_split_ratio}}
        """
        split_data = {}

        for ticker in tickers:
            try:
                yf_t = f"{ticker}.T" if ticker.isdigit() else ticker
                t = yf.Ticker(yf_t)
                splits = t.splits

                if splits.empty:
                    split_data[yf_t] = {}
                    continue

                # 日付ごとの累積分割比率を計算
                cumulative = {}
                ratio = 1.0

                # 分割日でソート
                splits_sorted = splits.sort_index()

                for split_date, split_ratio in splits_sorted.items():
                    split_date_obj = (
                        split_date.date() if hasattr(split_date, "date") else split_date
                    )
                    if start_date <= split_date_obj <= end_date:
                        ratio *= split_ratio
                        cumulative[split_date_obj] = ratio

                split_data[yf_t] = cumulative

            except Exception as e:
                print(f"WARNING: Failed to get split data for {ticker}: {e}")
                split_data[ticker] = {}

        return split_data

    @staticmethod
    def get_performance_history(days=365):
        """
        過去N日間の日次損益推移を計算する
        """
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)

            print(f"DEBUG: get_performance_history called with days={days}")
            print(f"DEBUG: Period: {start_date} to {end_date}")

            # 1. 全取引履歴を取得
            transactions = Transaction.query.order_by(
                Transaction.transaction_date
            ).all()
            if not transactions:
                print("DEBUG: No transactions found")
                return []

            print(f"DEBUG: Found {len(transactions)} transactions")
        except Exception as e:
            print(f"ERROR in get_performance_history initialization: {e}")
            import traceback

            traceback.print_exc()
            raise

        # 2. 過去の全保有銘柄を特定
        all_tickers = sorted(list(set(t.ticker_symbol for t in transactions)))

        # 3. ヒストリカル株価と為替レートを取得
        yf_tickers = []
        for t in all_tickers:
            if t.isdigit():
                yf_tickers.append(f"{t}.T")
            else:
                yf_tickers.append(t)

        yf_tickers.extend(["USDJPY=X", "KRWJPY=X"])

        min_tx_date = transactions[0].transaction_date
        download_start = min(start_date, min_tx_date) - timedelta(days=10)

        print(
            f"DEBUG: Tickers={len(yf_tickers)}, Period={download_start} to {end_date}"
        )

        # バッチ処理で取得
        all_data_frames = []
        batch_size = 15
        for i in range(0, len(yf_tickers), batch_size):
            batch = yf_tickers[i : i + batch_size]
            try:
                print(
                    f"DEBUG: Downloading batch {i//batch_size + 1}/{(len(yf_tickers)-1)//batch_size + 1}: {len(batch)} tickers"
                )
                # auto_adjust=True を使用して、常に調整後終値を 'Close' として取得
                batch_data = yf.download(
                    batch,
                    start=download_start,
                    end=end_date + timedelta(days=2),
                    interval="1d",
                    progress=False,
                    auto_adjust=True,
                )
                if not batch_data.empty:
                    # 多銘柄の場合は MultiIndex、1銘柄の場合は単一階層
                    if isinstance(batch_data.columns, pd.MultiIndex):
                        if "Close" in batch_data.columns.get_level_values(0):
                            all_data_frames.append(batch_data["Close"])
                    else:
                        if "Close" in batch_data.columns:
                            all_data_frames.append(
                                batch_data[["Close"]].rename(
                                    columns={"Close": batch[0]}
                                )
                            )
                        elif len(batch) == 1:
                            # 1銘柄で MultiIndex でない場合、そのまま Close カラムがあるはず
                            all_data_frames.append(
                                batch_data[["Close"]].rename(
                                    columns={"Close": batch[0]}
                                )
                            )
                    print(f"DEBUG: Batch {i//batch_size + 1} completed successfully")
            except Exception as e:
                print(f"ERROR: Batch {batch} failed: {e}")
                import traceback

                traceback.print_exc()

        if not all_data_frames:
            print("DEBUG: No price data obtained.")
            return []

        # 全ての DataFrame を横に結合
        prices_df = pd.concat(all_data_frames, axis=1)
        prices_df = prices_df.loc[:, ~prices_df.columns.duplicated()]  # 重複排除
        prices_df = prices_df.ffill()  # 欠損値を埋める

        print(f"DEBUG: Prices DataFrame Shape: {prices_df.shape}")

        # 4. 日ごとの保有状況の推移を計算
        tx_by_date = defaultdict(list)
        for tx in transactions:
            tx_by_date[tx.transaction_date].append(tx)

        div_by_date = defaultdict(list)
        dividends = Dividend.query.all()
        for div in dividends:
            div_by_date[div.ex_dividend_date].append(div)

        full_history_holdings = defaultdict(lambda: defaultdict(Decimal))
        temp_qty = defaultdict(Decimal)

        iter_date = min_tx_date
        while iter_date <= end_date:
            if iter_date in tx_by_date:
                for tx in tx_by_date[iter_date]:
                    if tx.transaction_type == "BUY":
                        temp_qty[tx.ticker_symbol] += Decimal(str(tx.quantity))
                    elif tx.transaction_type == "SELL":
                        temp_qty[tx.ticker_symbol] -= Decimal(str(tx.quantity))

            if iter_date >= start_date:
                for t, q in temp_qty.items():
                    if q > 0:
                        full_history_holdings[iter_date][t] = q

            iter_date += timedelta(days=1)

        # 5. 各有効日ごとに計算
        results = []
        valid_dates = sorted(
            list(set(d.date() for d in prices_df.index if d.date() >= start_date))
        )

        for i in range(len(valid_dates)):
            d = valid_dates[i]
            # prices_df において、d 以前で最新のデータがある行を探す
            try:
                curr_ts = pd.Timestamp(d)
                # prices_df.index から curr_ts 以前の最新インデックス
                indices = prices_df.index.get_indexer([curr_ts], method="pad")
                curr_idx = indices[0]
                if curr_idx <= 0:
                    continue

                prev_idx = curr_idx - 1
            except:
                continue

            holding_pnl = 0.0
            realized_pnl = 0.0
            dividend_income = 0.0
            portfolio_value = 0.0  # ポートフォリオ評価額を計算

            holdings_at_date = full_history_holdings[d]

            for ticker, qty in holdings_at_date.items():
                if qty <= 0:
                    continue

                yf_t = f"{ticker}.T" if ticker.isdigit() else ticker
                if yf_t not in prices_df.columns:
                    continue

                curr_price = prices_df.iloc[curr_idx][yf_t]
                prev_price = prices_df.iloc[prev_idx][yf_t]

                if pd.isna(curr_price) or pd.isna(prev_price):
                    continue

                # 為替レート（yfinanceティッカーで通貨を判定）
                if yf_t.endswith(".T"):
                    currency = "JPY"
                elif yf_t.endswith(".KS"):
                    currency = "KRW"
                else:
                    currency = "USD"

                rate = 1.0
                if currency == "USD" and "USDJPY=X" in prices_df.columns:
                    rate = prices_df.iloc[curr_idx]["USDJPY=X"]
                elif currency == "KRW" and "KRWJPY=X" in prices_df.columns:
                    rate = prices_df.iloc[curr_idx]["KRWJPY=X"]

                if pd.isna(rate) or rate == 0:
                    rate = 1.0

                diff = (
                    (float(curr_price) - float(prev_price)) * float(qty) * float(rate)
                )
                holding_pnl += diff

                # ポートフォリオ評価額を計算（現在価格 × 数量 × 為替レート）
                portfolio_value += float(curr_price) * float(qty) * float(rate)

            # B. 売却損益
            daily_realized = (
                db.session.query(db.func.sum(RealizedPnl.realized_pnl))
                .filter(RealizedPnl.sell_date == d)
                .scalar()
            )
            realized_pnl = float(daily_realized or 0)

            # C. 受取配当
            for div in div_by_date[d]:
                qty_at_div = holdings_at_date.get(div.ticker_symbol, 0)
                if qty_at_div > 0:
                    rate = 1.0
                    if div.currency == "USD" and "USDJPY=X" in prices_df.columns:
                        rate = prices_df.iloc[curr_idx]["USDJPY=X"]
                    elif div.currency == "KRW" and "KRWJPY=X" in prices_df.columns:
                        rate = prices_df.iloc[curr_idx]["KRWJPY=X"]

                    if pd.isna(rate) or rate == 0:
                        rate = 1.0
                    dividend_income += (
                        float(div.dividend_amount or 0)
                        * float(qty_at_div)
                        * float(rate)
                    )

            results.append(
                {
                    "date": d.isoformat(),
                    "holding_pnl": round(holding_pnl, 2),
                    "realized_pnl": round(realized_pnl, 2),
                    "dividend_income": round(dividend_income, 2),
                    "total": round(holding_pnl + realized_pnl + dividend_income, 2),
                    "portfolio_value": round(portfolio_value, 2),
                }
            )

        return results

    @staticmethod
    def get_monthly_performance_history():
        """
        過去1年間の月次損益推移を計算する
        holding_pnlは前月末株価と当月末株価の差分×保有数量で計算
        """
        from datetime import datetime
        import yfinance as yf

        end_date = date.today()
        start_date = end_date - timedelta(days=400)  # 余裕を持って取得

        # 全取引を取得
        transactions = Transaction.query.order_by(Transaction.transaction_date).all()
        if not transactions:
            return []

        # 全ティッカーを取得
        all_tickers = sorted(list(set(t.ticker_symbol for t in transactions)))
        yf_tickers = []
        ticker_map = {}  # yf_ticker -> original_ticker
        for t in all_tickers:
            if t.isdigit():
                yf_t = f"{t}.T"
            else:
                yf_t = t
            yf_tickers.append(yf_t)
            ticker_map[yf_t] = t

        yf_tickers.extend(["USDJPY=X", "KRWJPY=X"])

        # 一度に全価格データを取得
        all_data_frames = []
        batch_size = 15
        for i in range(0, len(yf_tickers), batch_size):
            batch = yf_tickers[i : i + batch_size]
            try:
                batch_data = yf.download(
                    batch,
                    start=start_date,
                    end=end_date,
                    interval="1d",
                    progress=False,
                    auto_adjust=True,
                )
                if not batch_data.empty:
                    if isinstance(batch_data.columns, pd.MultiIndex):
                        if "Close" in batch_data.columns.get_level_values(0):
                            all_data_frames.append(batch_data["Close"])
                    else:
                        if "Close" in batch_data.columns:
                            all_data_frames.append(
                                batch_data[["Close"]].rename(
                                    columns={"Close": batch[0]}
                                )
                            )
            except:
                pass

        if not all_data_frames:
            return []

        prices_df = pd.concat(all_data_frames, axis=1)
        prices_df = prices_df.loc[:, ~prices_df.columns.duplicated()]
        prices_df = prices_df.ffill()

        # 取引履歴をマップ化
        tx_by_date = defaultdict(list)
        for tx in transactions:
            tx_by_date[tx.transaction_date].append(tx)

        # 実現損益と配当をマップ化
        realized_by_date = defaultdict(list)
        for r in RealizedPnl.query.all():
            realized_by_date[r.sell_date].append(r)

        dividends_by_date = defaultdict(list)
        for div in Dividend.query.all():
            dividends_by_date[div.ex_dividend_date].append(div)

        # 過去13ヶ月分の月を生成
        months = []
        for i in range(14, 0, -1):
            target_month = end_date - timedelta(days=30 * i)
            month_str = target_month.strftime("%Y-%m")
            if month_str not in months:
                months.append(month_str)
        current_month = end_date.strftime("%Y-%m")
        if current_month not in months:
            months.append(current_month)

        # 各月のデータを計算
        results = []
        today = date.today()

        for month_str in months[-13:]:
            year, month = map(int, month_str.split("-"))
            month_start = datetime(year, month, 1).date()
            if month == 12:
                calculated_month_end = datetime(year + 1, 1, 1).date() - timedelta(
                    days=1
                )
            else:
                calculated_month_end = datetime(year, month + 1, 1).date() - timedelta(
                    days=1
                )

            # 現在の月の場合は、今日の日付を使用
            if year == today.year and month == today.month:
                month_end = today
            else:
                month_end = calculated_month_end

            # 前月末日を計算
            prev_month_end = month_start - timedelta(days=1)

            # 月末時点の保有状況を計算
            holdings_at_month_end = defaultdict(Decimal)
            iter_date = transactions[0].transaction_date
            while iter_date <= month_end:
                if iter_date in tx_by_date:
                    for tx in tx_by_date[iter_date]:
                        if tx.transaction_type == "BUY":
                            holdings_at_month_end[tx.ticker_symbol] += Decimal(
                                str(tx.quantity)
                            )
                        elif tx.transaction_type == "SELL":
                            holdings_at_month_end[tx.ticker_symbol] -= Decimal(
                                str(tx.quantity)
                            )
                iter_date += timedelta(days=1)

            # 保有損益を計算
            holding_pnl = 0.0
            portfolio_value = 0.0

            for ticker, qty in holdings_at_month_end.items():
                if qty <= 0:
                    continue

                yf_t = f"{ticker}.T" if ticker.isdigit() else ticker
                if yf_t not in prices_df.columns:
                    continue

                # 月末価格
                try:
                    curr_ts = pd.Timestamp(month_end)
                    curr_indices = prices_df.index.get_indexer([curr_ts], method="pad")
                    curr_idx = curr_indices[0]
                    if curr_idx < 0:
                        continue
                    curr_price = prices_df.iloc[curr_idx][yf_t]
                    if pd.isna(curr_price):
                        continue
                except:
                    continue

                # 前月末価格または取得価格
                # 当月中のBUY取引を確認
                buy_in_month = [
                    tx
                    for tx in transactions
                    if tx.ticker_symbol == ticker
                    and tx.transaction_type == "BUY"
                    and month_start <= tx.transaction_date <= month_end
                ]

                if buy_in_month:
                    # 当月中に取得: 加重平均取得価格を使用（分割調整後）
                    # 取得価格は分割調整前なので、分割比率で割る必要がある
                    # yfinanceはauto_adjust=Trueで今日時点の分割調整価格を返すため、
                    # 取得価格も今日時点の分割に合わせて調整する
                    total_cost = 0.0
                    total_qty = 0.0
                    for tx in buy_in_month:
                        # 取引日から今日までの分割調整係数を取得
                        split_factor = PerformanceService.get_split_adjustment_factor(
                            yf_t, tx.transaction_date, date.today()
                        )
                        # 取得価格を分割調整
                        adjusted_price = float(tx.unit_price) / split_factor
                        total_cost += adjusted_price * float(tx.quantity)
                        total_qty += float(tx.quantity)
                    prev_price = total_cost / total_qty if total_qty > 0 else 0
                else:
                    # 前月から保有: 前月末価格を使用
                    try:
                        prev_ts = pd.Timestamp(prev_month_end)
                        prev_indices = prices_df.index.get_indexer(
                            [prev_ts], method="pad"
                        )
                        prev_idx = prev_indices[0]
                        if prev_idx < 0:
                            continue
                        prev_price = prices_df.iloc[prev_idx][yf_t]
                        if pd.isna(prev_price):
                            continue
                    except:
                        continue

                # 通貨と為替レート
                if yf_t.endswith(".T"):
                    currency = "JPY"
                    rate = 1.0
                elif yf_t.endswith(".KS"):
                    currency = "KRW"
                    if "KRWJPY=X" in prices_df.columns:
                        rate = prices_df.iloc[curr_idx]["KRWJPY=X"]
                        if pd.isna(rate) or rate == 0:
                            rate = 0.11
                    else:
                        rate = 0.11
                else:
                    currency = "USD"
                    if "USDJPY=X" in prices_df.columns:
                        rate = prices_df.iloc[curr_idx]["USDJPY=X"]
                        if pd.isna(rate) or rate == 0:
                            rate = 150.0
                    else:
                        rate = 150.0

                # 損益計算
                price_diff = float(curr_price) - float(prev_price)
                pnl = price_diff * float(qty) * float(rate)
                holding_pnl += pnl

                # 評価額
                portfolio_value += float(curr_price) * float(qty) * float(rate)

            # 実現損益を計算
            realized_pnl = 0.0
            for d in range((month_end - month_start).days + 1):
                check_date = month_start + timedelta(days=d)
                if check_date in realized_by_date:
                    for r in realized_by_date[check_date]:
                        realized_pnl += float(r.realized_pnl)

            # 配当を計算
            dividend_income = 0.0
            for d in range((month_end - month_start).days + 1):
                check_date = month_start + timedelta(days=d)
                if check_date in dividends_by_date:
                    for div in dividends_by_date[check_date]:
                        if div.quantity_held > 0:
                            # 為替換算
                            rate = 1.0
                            if (
                                div.currency == "USD"
                                and "USDJPY=X" in prices_df.columns
                            ):
                                try:
                                    rate = prices_df.iloc[curr_idx]["USDJPY=X"]
                                    if pd.isna(rate) or rate == 0:
                                        rate = 150.0
                                except:
                                    rate = 150.0
                            elif (
                                div.currency == "KRW"
                                and "KRWJPY=X" in prices_df.columns
                            ):
                                try:
                                    rate = prices_df.iloc[curr_idx]["KRWJPY=X"]
                                    if pd.isna(rate) or rate == 0:
                                        rate = 0.11
                                except:
                                    rate = 0.11

                            dividend_jpy = (
                                float(div.dividend_amount or 0)
                                * float(div.quantity_held)
                                * rate
                            )
                            dividend_income += dividend_jpy

            results.append(
                {
                    "date": month_str,
                    "holding_pnl": round(holding_pnl, 2),
                    "realized_pnl": round(realized_pnl, 2),
                    "dividend_income": round(dividend_income, 2),
                    "total": round(holding_pnl + realized_pnl + dividend_income, 2),
                    "portfolio_value": round(portfolio_value, 2),
                }
            )

        return results

    @staticmethod
    def get_daily_detail(target_date_str):
        """
        特定の日付または月の損益詳細を銘柄ごとに取得する
        日付形式: YYYY-MM-DD (日次) または YYYY-MM (月次)
        """
        from datetime import datetime

        # 月次データの場合(YYYY-MM形式)の処理
        if len(target_date_str) == 7 and target_date_str.count("-") == 1:
            # 月次データの場合は、その月の最終日を使用
            year, month = map(int, target_date_str.split("-"))
            # 次の月の1日を取得して1日引く = 当月の最終日
            if month == 12:
                month_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)

            # 現在の月の場合は、今日の日付を使用
            today = date.today()
            if year == today.year and month == today.month:
                target_date = today
            else:
                target_date = month_end

            is_monthly = True
        else:
            # 日次データの場合
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            is_monthly = False

        # 全取引履歴を取得
        transactions = Transaction.query.order_by(Transaction.transaction_date).all()
        if not transactions:
            return {
                "holding_details": [],
                "realized_details": [],
                "dividend_details": [],
            }

        # 全保有銘柄を特定
        all_tickers = sorted(list(set(t.ticker_symbol for t in transactions)))

        # yfinanceティッカーに変換
        yf_tickers = []
        for t in all_tickers:
            if t.isdigit():
                yf_tickers.append(f"{t}.T")
            else:
                yf_tickers.append(t)

        yf_tickers.extend(["USDJPY=X", "KRWJPY=X"])

        # target_dateの前後のデータを取得
        # 月次の場合は前月末の価格が必要なので、取得期間を拡大
        if is_monthly:
            # 前月の最終日を計算
            if target_date_str[:7].endswith("-01"):
                # 1月の場合は前年12月
                year = int(target_date_str[:4]) - 1
                prev_month_end = datetime(year, 12, 31).date()
            else:
                year, month = map(int, target_date_str.split("-"))
                prev_month_end = datetime(year, month, 1).date() - timedelta(days=1)
            start_date = prev_month_end - timedelta(days=5)
        else:
            start_date = target_date - timedelta(days=5)
        end_date = target_date + timedelta(days=2)

        # バッチ処理で取得
        all_data_frames = []
        batch_size = 15
        for i in range(0, len(yf_tickers), batch_size):
            batch = yf_tickers[i : i + batch_size]
            try:
                batch_data = yf.download(
                    batch,
                    start=start_date,
                    end=end_date,
                    interval="1d",
                    progress=False,
                    auto_adjust=True,
                )
                if not batch_data.empty:
                    if isinstance(batch_data.columns, pd.MultiIndex):
                        if "Close" in batch_data.columns.get_level_values(0):
                            all_data_frames.append(batch_data["Close"])
                    else:
                        if "Close" in batch_data.columns:
                            all_data_frames.append(
                                batch_data[["Close"]].rename(
                                    columns={"Close": batch[0]}
                                )
                            )
                        elif len(batch) == 1:
                            all_data_frames.append(
                                batch_data[["Close"]].rename(
                                    columns={"Close": batch[0]}
                                )
                            )
            except:
                pass

        if not all_data_frames:
            return {
                "holding_details": [],
                "realized_details": [],
                "dividend_details": [],
            }

        prices_df = pd.concat(all_data_frames, axis=1)
        prices_df = prices_df.loc[:, ~prices_df.columns.duplicated()]
        prices_df = prices_df.ffill()

        # 指定日時点の保有状況を計算
        tx_by_date = defaultdict(list)
        for tx in transactions:
            tx_by_date[tx.transaction_date].append(tx)

        holdings_at_date = defaultdict(Decimal)
        iter_date = transactions[0].transaction_date

        while iter_date <= target_date:
            if iter_date in tx_by_date:
                for tx in tx_by_date[iter_date]:
                    if tx.transaction_type == "BUY":
                        holdings_at_date[tx.ticker_symbol] += Decimal(str(tx.quantity))
                    elif tx.transaction_type == "SELL":
                        holdings_at_date[tx.ticker_symbol] -= Decimal(str(tx.quantity))
            iter_date += timedelta(days=1)

        # インデックスを取得
        try:
            curr_ts = pd.Timestamp(target_date)
            indices = prices_df.index.get_indexer([curr_ts], method="pad")
            curr_idx = indices[0]

            if curr_idx < 0:
                return {
                    "holding_details": [],
                    "realized_details": [],
                    "dividend_details": [],
                }

            # 月次の場合は前月末の価格を取得
            if is_monthly:
                year, month = map(int, target_date_str.split("-"))
                prev_month_end = datetime(year, month, 1).date() - timedelta(days=1)
                prev_ts = pd.Timestamp(prev_month_end)
                prev_indices = prices_df.index.get_indexer([prev_ts], method="pad")
                prev_idx = prev_indices[0]
                if prev_idx < 0:
                    return {
                        "holding_details": [],
                        "realized_details": [],
                        "dividend_details": [],
                    }
            else:
                # 日次の場合は前日
                if curr_idx <= 0:
                    return {
                        "holding_details": [],
                        "realized_details": [],
                        "dividend_details": [],
                    }
                prev_idx = curr_idx - 1
        except:
            return {
                "holding_details": [],
                "realized_details": [],
                "dividend_details": [],
            }

        # A. 保有損益の詳細
        holding_details = []

        # 月次の場合、月初の日付を計算
        if is_monthly:
            year, month = map(int, target_date_str.split("-"))
            month_start = datetime(year, month, 1).date()

        for ticker, qty in sorted(holdings_at_date.items()):
            if qty <= 0:
                continue

            yf_t = f"{ticker}.T" if ticker.isdigit() else ticker
            if yf_t not in prices_df.columns:
                continue

            curr_price = prices_df.iloc[curr_idx][yf_t]
            prev_price = prices_df.iloc[prev_idx][yf_t]

            # 月次の場合、当月に新規取得した銘柄は取得価格を使用
            # 注意: 前月から保有していて当月に追加購入した場合は前月末株価を使用
            is_new_this_month = False
            if is_monthly:
                # 前月末時点の保有数量を計算
                holdings_at_prev_month_end = Decimal("0")
                for tx in transactions:
                    if tx.ticker_symbol == ticker and tx.transaction_date < month_start:
                        if tx.transaction_type == "BUY":
                            holdings_at_prev_month_end += Decimal(str(tx.quantity))
                        elif tx.transaction_type == "SELL":
                            holdings_at_prev_month_end -= Decimal(str(tx.quantity))

                # 前月末時点で保有がなかった（当月に新規取得した）銘柄のみ取得価格を使用
                if holdings_at_prev_month_end <= 0:
                    buy_in_month = [
                        tx
                        for tx in transactions
                        if tx.ticker_symbol == ticker
                        and tx.transaction_type == "BUY"
                        and month_start <= tx.transaction_date <= target_date
                    ]

                    if buy_in_month:
                        is_new_this_month = True
                        # 当月に新規取得した銘柄: 加重平均取得価格を計算（分割調整後）
                        # yfinanceはauto_adjust=Trueで今日時点の分割調整価格を返すため、
                        # 取得価格も今日時点の分割に合わせて調整する
                        total_cost = 0.0
                        total_qty = 0.0
                        for tx in buy_in_month:
                            # 取引日から今日までの分割調整係数を取得
                            split_factor = (
                                PerformanceService.get_split_adjustment_factor(
                                    yf_t, tx.transaction_date, date.today()
                                )
                            )
                            # 取得価格を分割調整
                            adjusted_price = float(tx.unit_price) / split_factor
                            total_cost += adjusted_price * float(tx.quantity)
                            total_qty += float(tx.quantity)
                        if total_qty > 0:
                            prev_price = total_cost / total_qty

            # curr_priceまたはprev_priceがNaNの場合はスキップ
            if pd.isna(curr_price) or pd.isna(prev_price):
                continue

            # 通貨判定
            if yf_t.endswith(".T"):
                currency = "JPY"
            elif yf_t.endswith(".KS"):
                currency = "KRW"
            else:
                currency = "USD"

            # 為替レート取得
            rate = 1.0
            if currency == "USD" and "USDJPY=X" in prices_df.columns:
                rate = prices_df.iloc[curr_idx]["USDJPY=X"]
                if pd.isna(rate) or rate == 0:
                    rate = 1.0
            elif currency == "KRW" and "KRWJPY=X" in prices_df.columns:
                rate = prices_df.iloc[curr_idx]["KRWJPY=X"]
                if pd.isna(rate) or rate == 0:
                    rate = 1.0

            price_diff = float(curr_price) - float(prev_price)
            pnl = price_diff * float(qty) * float(rate)

            # 銘柄名を取得
            tx = Transaction.query.filter_by(ticker_symbol=ticker).first()
            security_name = tx.security_name if tx else ticker

            holding_details.append(
                {
                    "ticker_symbol": ticker,
                    "security_name": security_name,
                    "quantity": float(qty),
                    "prev_price": float(prev_price),
                    "curr_price": float(curr_price),
                    "price_change": price_diff,
                    "currency": currency,
                    "exchange_rate": float(rate),
                    "pnl": round(pnl, 2),
                    "is_new_this_month": is_new_this_month,
                }
            )

        # B. 実現損益の詳細
        realized_details = []
        if is_monthly:
            # 月次の場合は月間の全実現損益を取得
            year, month = map(int, target_date_str.split("-"))
            month_start = datetime(year, month, 1).date()
            if month == 12:
                month_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)

            monthly_realized = RealizedPnl.query.filter(
                RealizedPnl.sell_date >= month_start, RealizedPnl.sell_date <= month_end
            ).all()

            # 銘柄ごとに集計
            ticker_realized = defaultdict(
                lambda: {"quantity": 0, "pnl": 0, "details": []}
            )
            for r in monthly_realized:
                ticker_realized[r.ticker_symbol]["quantity"] += float(r.quantity)
                ticker_realized[r.ticker_symbol]["pnl"] += float(r.realized_pnl)
                ticker_realized[r.ticker_symbol]["details"].append(r)

            for ticker_symbol, data in ticker_realized.items():
                tx = Transaction.query.filter_by(ticker_symbol=ticker_symbol).first()
                security_name = tx.security_name if tx else ticker_symbol

                # 平均取得単価と売却単価を計算
                total_cost = sum(
                    float(r.average_cost) * float(r.quantity) for r in data["details"]
                )
                total_sell = sum(
                    float(r.sell_price) * float(r.quantity) for r in data["details"]
                )
                avg_cost = total_cost / data["quantity"] if data["quantity"] > 0 else 0
                avg_sell = total_sell / data["quantity"] if data["quantity"] > 0 else 0

                realized_details.append(
                    {
                        "ticker_symbol": ticker_symbol,
                        "security_name": security_name,
                        "quantity": data["quantity"],
                        "average_cost": round(avg_cost, 2),
                        "sell_price": round(avg_sell, 2),
                        "pnl": round(data["pnl"], 2),
                    }
                )
        else:
            # 日次の場合
            daily_realized = RealizedPnl.query.filter_by(sell_date=target_date).all()
            for r in daily_realized:
                tx = Transaction.query.filter_by(ticker_symbol=r.ticker_symbol).first()
                security_name = tx.security_name if tx else r.ticker_symbol

                realized_details.append(
                    {
                        "ticker_symbol": r.ticker_symbol,
                        "security_name": security_name,
                        "quantity": float(r.quantity),
                        "average_cost": float(r.average_cost),
                        "sell_price": float(r.sell_price),
                        "pnl": float(r.realized_pnl),
                    }
                )

        # C. 配当の詳細
        dividend_details = []
        if is_monthly:
            # 月次の場合は月間の全配当を取得
            year, month = map(int, target_date_str.split("-"))
            month_start = datetime(year, month, 1).date()
            if month == 12:
                month_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)

            monthly_dividends = Dividend.query.filter(
                Dividend.ex_dividend_date >= month_start,
                Dividend.ex_dividend_date <= month_end,
            ).all()

            # 銘柄ごとに集計
            ticker_dividends = defaultdict(
                lambda: {"total_jpy": 0, "count": 0, "currency": None}
            )
            for div in monthly_dividends:
                if div.quantity_held > 0:
                    # 為替換算してJPYに統一
                    rate = 1.0
                    if div.currency == "USD" and "USDJPY=X" in prices_df.columns:
                        rate = prices_df.iloc[curr_idx]["USDJPY=X"]
                        if pd.isna(rate) or rate == 0:
                            rate = 150.0  # デフォルト為替レート
                    elif div.currency == "KRW" and "KRWJPY=X" in prices_df.columns:
                        rate = prices_df.iloc[curr_idx]["KRWJPY=X"]
                        if pd.isna(rate) or rate == 0:
                            rate = 0.11  # デフォルト為替レート
                    elif div.currency != "JPY":
                        # その他の通貨はJPY扱い
                        rate = 1.0

                    # dividend_amount × quantity_held × 為替レート
                    dividend_jpy = (
                        float(div.dividend_amount or 0)
                        * float(div.quantity_held)
                        * rate
                    )
                    ticker_dividends[div.ticker_symbol]["total_jpy"] += dividend_jpy
                    ticker_dividends[div.ticker_symbol]["count"] += 1
                    if ticker_dividends[div.ticker_symbol]["currency"] is None:
                        ticker_dividends[div.ticker_symbol]["currency"] = div.currency

            for ticker_symbol, data in ticker_dividends.items():
                tx = Transaction.query.filter_by(ticker_symbol=ticker_symbol).first()
                security_name = tx.security_name if tx else ticker_symbol

                dividend_details.append(
                    {
                        "ticker_symbol": ticker_symbol,
                        "security_name": security_name,
                        "total_dividend": round(data["total_jpy"], 2),
                        "currency": data["currency"] or "JPY",
                    }
                )
        else:
            # 日次の場合
            dividends = Dividend.query.filter_by(ex_dividend_date=target_date).all()

            for div in dividends:
                qty_at_div = holdings_at_date.get(div.ticker_symbol, 0)
                if qty_at_div > 0:
                    rate = 1.0
                    if div.currency == "USD" and "USDJPY=X" in prices_df.columns:
                        rate = prices_df.iloc[curr_idx]["USDJPY=X"]
                        if pd.isna(rate) or rate == 0:
                            rate = 1.0
                    elif div.currency == "KRW" and "KRWJPY=X" in prices_df.columns:
                        rate = prices_df.iloc[curr_idx]["KRWJPY=X"]
                        if pd.isna(rate) or rate == 0:
                            rate = 1.0

                    tx = Transaction.query.filter_by(
                        ticker_symbol=div.ticker_symbol
                    ).first()
                    security_name = tx.security_name if tx else div.ticker_symbol

                    dividend_jpy = (
                        float(div.dividend_amount or 0)
                        * float(qty_at_div)
                        * float(rate)
                    )

                    dividend_details.append(
                        {
                            "ticker_symbol": div.ticker_symbol,
                            "security_name": security_name,
                            "quantity": float(qty_at_div),
                            "dividend_per_share": float(div.dividend_amount or 0),
                            "currency": div.currency,
                            "exchange_rate": float(rate),
                            "total_dividend": round(dividend_jpy, 2),
                        }
                    )

        return {
            "holding_details": holding_details,
            "realized_details": realized_details,
            "dividend_details": dividend_details,
        }

    @staticmethod
    def get_performance_history_with_benchmark(
        days=30, benchmark_keys=["TOPIX", "SP500"]
    ):
        """
        ベンチマーク比較データを含む損益推移データを取得

        Args:
            days: 過去何日分のデータを取得するか
            benchmark_keys: ベンチマークキーのリスト ['TOPIX', 'SP500']

        Returns:
            {
                'portfolio': [  # ポートフォリオデータ
                    {
                        'date': '2024-01-15',
                        'holding_pnl': 125000.50,
                        'realized_pnl': 45000.00,
                        'dividend_income': 8500.00,
                        'total': 178500.50,
                        'portfolio_value': 10000000.0  # その日の評価額
                    }
                ],
                'benchmarks': {
                    'TOPIX': [
                        {
                            'date': '2024-01-15',
                            'close': 2650.5,
                            'daily_return': 0.015,  # 対前日変動率
                            'virtual_pnl': 150000.0,  # 前日評価額 × 変動率
                            'cumulative_return': 0.025  # 初日からの累積リターン
                        }
                    ],
                    'SP500': [...]
                }
            }
        """
        from app.services.benchmark_fetcher import BenchmarkFetcher

        print(
            f"DEBUG: get_performance_history_with_benchmark called with days={days}, benchmarks={benchmark_keys}"
        )

        # 1. 既存のポートフォリオ損益データを取得
        portfolio_data = PerformanceService.get_performance_history(days=days)

        if not portfolio_data:
            print("DEBUG: No portfolio data available")
            return {"portfolio": [], "benchmarks": {}}

        # 2. 各日のポートフォリオ評価額を計算
        # 最初に全取引履歴と保有銘柄を使ってportfolio_valueを計算
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)

            # 取引履歴を取得して保有状況を再計算
            transactions = Transaction.query.order_by(
                Transaction.transaction_date
            ).all()
            if not transactions:
                print("DEBUG: No transactions found")
                return {"portfolio": portfolio_data, "benchmarks": {}}

            # 全銘柄を取得
            all_tickers = sorted(list(set(t.ticker_symbol for t in transactions)))
            yf_tickers = []
            for t in all_tickers:
                if t.isdigit():
                    yf_tickers.append(f"{t}.T")
                else:
                    yf_tickers.append(t)

            yf_tickers.extend(["USDJPY=X", "KRWJPY=X"])

            min_tx_date = transactions[0].transaction_date
            download_start = min(start_date, min_tx_date) - timedelta(days=10)

            # バッチ処理で株価取得
            all_data_frames = []
            batch_size = 15
            for i in range(0, len(yf_tickers), batch_size):
                batch = yf_tickers[i : i + batch_size]
                try:
                    batch_data = yf.download(
                        batch,
                        start=download_start,
                        end=end_date + timedelta(days=2),
                        interval="1d",
                        progress=False,
                        auto_adjust=True,
                    )
                    if not batch_data.empty:
                        if isinstance(batch_data.columns, pd.MultiIndex):
                            if "Close" in batch_data.columns.get_level_values(0):
                                all_data_frames.append(batch_data["Close"])
                        else:
                            if "Close" in batch_data.columns:
                                all_data_frames.append(
                                    batch_data[["Close"]].rename(
                                        columns={"Close": batch[0]}
                                    )
                                )
                            elif len(batch) == 1:
                                all_data_frames.append(
                                    batch_data[["Close"]].rename(
                                        columns={"Close": batch[0]}
                                    )
                                )
                except Exception as e:
                    print(f"ERROR: Batch {batch} failed: {e}")

            if not all_data_frames:
                print("DEBUG: No price data obtained")
                return {"portfolio": portfolio_data, "benchmarks": {}}

            prices_df = pd.concat(all_data_frames, axis=1)
            prices_df = prices_df.loc[:, ~prices_df.columns.duplicated()]
            prices_df = prices_df.ffill()

            # 日ごとの保有状況を計算
            tx_by_date = defaultdict(list)
            for tx in transactions:
                tx_by_date[tx.transaction_date].append(tx)

            full_history_holdings = defaultdict(lambda: defaultdict(Decimal))
            temp_qty = defaultdict(Decimal)

            iter_date = min_tx_date
            while iter_date <= end_date:
                if iter_date in tx_by_date:
                    for tx in tx_by_date[iter_date]:
                        if tx.transaction_type == "BUY":
                            temp_qty[tx.ticker_symbol] += Decimal(str(tx.quantity))
                        elif tx.transaction_type == "SELL":
                            temp_qty[tx.ticker_symbol] -= Decimal(str(tx.quantity))

                if iter_date >= start_date:
                    for t, q in temp_qty.items():
                        if q > 0:
                            full_history_holdings[iter_date][t] = q

                iter_date += timedelta(days=1)

            # 各日のポートフォリオ評価額を計算
            for item in portfolio_data:
                date_obj = datetime.strptime(item["date"], "%Y-%m-%d").date()

                try:
                    curr_ts = pd.Timestamp(date_obj)
                    indices = prices_df.index.get_indexer([curr_ts], method="pad")
                    curr_idx = indices[0]

                    if curr_idx < 0:
                        item["portfolio_value"] = 0.0
                        continue

                    holdings_at_date = full_history_holdings[date_obj]
                    portfolio_value = 0.0

                    for ticker, qty in holdings_at_date.items():
                        if qty <= 0:
                            continue

                        yf_t = f"{ticker}.T" if ticker.isdigit() else ticker
                        if yf_t not in prices_df.columns:
                            continue

                        curr_price = prices_df.iloc[curr_idx][yf_t]
                        if pd.isna(curr_price):
                            continue

                        # 為替レート
                        if yf_t.endswith(".T"):
                            currency = "JPY"
                        elif yf_t.endswith(".KS"):
                            currency = "KRW"
                        else:
                            currency = "USD"

                        rate = 1.0
                        if currency == "USD" and "USDJPY=X" in prices_df.columns:
                            rate = prices_df.iloc[curr_idx]["USDJPY=X"]
                        elif currency == "KRW" and "KRWJPY=X" in prices_df.columns:
                            rate = prices_df.iloc[curr_idx]["KRWJPY=X"]

                        if pd.isna(rate) or rate == 0:
                            rate = 1.0

                        portfolio_value += float(curr_price) * float(qty) * float(rate)

                    item["portfolio_value"] = round(portfolio_value, 2)

                except Exception as e:
                    print(
                        f"ERROR: Failed to calculate portfolio value for {date_obj}: {e}"
                    )
                    item["portfolio_value"] = 0.0

        except Exception as e:
            print(f"ERROR: Failed to calculate portfolio values: {e}")
            import traceback

            traceback.print_exc()
            # ポートフォリオ評価額なしで続行
            for item in portfolio_data:
                item["portfolio_value"] = 0.0

        # 3. ベンチマークデータを取得
        benchmarks_result = {}

        if benchmark_keys:
            start_date_obj = datetime.strptime(
                portfolio_data[0]["date"], "%Y-%m-%d"
            ).date()
            end_date_obj = datetime.strptime(
                portfolio_data[-1]["date"], "%Y-%m-%d"
            ).date()

            benchmarks_history = BenchmarkFetcher.get_multiple_benchmarks(
                benchmark_keys, start_date_obj, end_date_obj
            )

            # 4. 各ベンチマークについて損益計算
            for benchmark_key, benchmark_data in benchmarks_history.items():
                if not benchmark_data:
                    continue

                benchmark_result = []
                initial_close = None

                # ポートフォリオデータとベンチマークデータを日付で紐付け
                portfolio_dict = {item["date"]: item for item in portfolio_data}

                for i, bench_item in enumerate(benchmark_data):
                    date_str = bench_item["date"].isoformat()
                    close_price = bench_item["close"]
                    previous_close = bench_item.get("previous_close")

                    # 初日の終値を記録
                    if initial_close is None:
                        initial_close = close_price

                    # 対前日変動率
                    daily_return = 0.0
                    if previous_close and previous_close > 0:
                        daily_return = (close_price - previous_close) / previous_close

                    # 仮想損益: 前日のポートフォリオ評価額 × ベンチマーク変動率
                    virtual_pnl = 0.0
                    if i > 0 and date_str in portfolio_dict:
                        # 前日のポートフォリオ評価額を取得
                        prev_date_str = benchmark_data[i - 1]["date"].isoformat()
                        if prev_date_str in portfolio_dict:
                            prev_portfolio_value = portfolio_dict[prev_date_str][
                                "portfolio_value"
                            ]
                            virtual_pnl = prev_portfolio_value * daily_return

                    # S&P500の場合、JPY換算が必要
                    if benchmark_key == "SP500":
                        # 為替レートを取得
                        try:
                            rate_data = ExchangeRateFetcher.get_historical_rate(
                                "USD", "JPY", bench_item["date"]
                            )
                            if rate_data and rate_data.get("rate"):
                                # S&P500の変動率はそのまま、virtual_pnlは円建てポートフォリオに対する変動なのでそのまま
                                pass
                        except:
                            pass

                    # 累積リターン
                    cumulative_return = 0.0
                    if initial_close and initial_close > 0:
                        cumulative_return = (
                            close_price - initial_close
                        ) / initial_close

                    benchmark_result.append(
                        {
                            "date": date_str,
                            "close": close_price,
                            "daily_return": round(daily_return, 6),
                            "virtual_pnl": round(virtual_pnl, 2),
                            "cumulative_return": round(cumulative_return, 6),
                        }
                    )

                benchmarks_result[benchmark_key] = benchmark_result

        print(f"DEBUG: Benchmark data prepared: {list(benchmarks_result.keys())}")

        return {"portfolio": portfolio_data, "benchmarks": benchmarks_result}

    @staticmethod
    def calculate_irr_for_holding(ticker_symbol):
        """
        特定の保有銘柄のIRR（内部収益率）を計算する

        キャッシュフロー:
        - 買い: マイナス（投資）
        - 配当: プラス（受取）
        - 現在評価額: プラス（仮想的な売却）

        Returns:
            dict: {'irr': float or None, 'cash_flows': list, 'error': str or None}
        """
        try:
            import numpy_financial as npf
        except ImportError:
            try:
                import numpy as np

                # numpy_financialがない場合はnumpyのnpvを使ってIRRを計算
                npf = None
            except ImportError:
                return {"irr": None, "cash_flows": [], "error": "numpy not available"}

        from datetime import date as date_class

        # 取引履歴を取得
        transactions = (
            Transaction.query.filter_by(ticker_symbol=ticker_symbol)
            .order_by(Transaction.transaction_date)
            .all()
        )

        if not transactions:
            return {"irr": None, "cash_flows": [], "error": "No transactions found"}

        # 配当履歴を取得
        dividends = (
            Dividend.query.filter_by(ticker_symbol=ticker_symbol)
            .order_by(Dividend.ex_dividend_date)
            .all()
        )

        # 保有銘柄情報を取得
        holding = Holding.query.filter_by(ticker_symbol=ticker_symbol).first()

        # キャッシュフローを日付順にまとめる
        cash_flows = []

        # 取引のキャッシュフロー
        for tx in transactions:
            if tx.transaction_type == "BUY":
                # 買い: 支払い（マイナス）- settlement_amountは円建て
                cf_amount = -float(tx.settlement_amount or 0)
            else:  # SELL
                # 売り: 受取（プラス）
                cf_amount = float(tx.settlement_amount or 0)

            cash_flows.append(
                {
                    "date": tx.transaction_date,
                    "amount": cf_amount,
                    "type": tx.transaction_type,
                }
            )

        # 配当のキャッシュフロー（円換算）
        for div in dividends:
            if div.total_dividend and div.total_dividend > 0:
                # 配当は円換算が必要な場合がある
                div_amount = float(div.total_dividend)

                # 通貨が外貨の場合は為替レートを取得して換算
                if div.currency and div.currency.upper() not in ["JPY", "日本円"]:
                    try:
                        rates = ExchangeRateFetcher.get_multiple_rates([div.currency])
                        if rates and div.currency in rates:
                            rate = rates[div.currency].get("rate", 1.0)
                            div_amount = div_amount * rate
                    except Exception:
                        pass  # レート取得失敗時はそのまま

                cash_flows.append(
                    {
                        "date": div.ex_dividend_date,
                        "amount": div_amount,
                        "type": "DIVIDEND",
                    }
                )

        # 現在の評価額を最終キャッシュフローとして追加
        if holding and holding.current_value:
            current_value = float(holding.current_value)
            cash_flows.append(
                {
                    "date": date_class.today(),
                    "amount": current_value,
                    "type": "CURRENT_VALUE",
                }
            )

        # 日付順でソート
        cash_flows.sort(key=lambda x: x["date"])

        if len(cash_flows) < 2:
            return {
                "irr": None,
                "cash_flows": cash_flows,
                "error": "Insufficient cash flows",
            }

        # XIRRを計算（日付を考慮したIRR）
        try:
            irr = PerformanceService._calculate_xirr(cash_flows)
            return {"irr": irr, "cash_flows": cash_flows, "error": None}
        except Exception as e:
            return {"irr": None, "cash_flows": cash_flows, "error": str(e)}

    @staticmethod
    def _calculate_xirr(cash_flows, max_iterations=100, tolerance=1e-6):
        """
        XIRR（日付を考慮した内部収益率）を計算

        Args:
            cash_flows: [{'date': date, 'amount': float}, ...]
            max_iterations: 最大反復回数
            tolerance: 収束判定の許容誤差

        Returns:
            float: 年率IRR（%表示）, または None（計算不可）
        """
        if not cash_flows or len(cash_flows) < 2:
            return None

        # 基準日を最初のキャッシュフロー日とする
        base_date = cash_flows[0]["date"]

        # 日数を年数に変換（365日 = 1年）
        def years_from_base(d):
            if hasattr(d, "date"):
                d = d.date()
            delta = (d - base_date).days
            return delta / 365.0

        # XNPV関数
        def xnpv(rate, cfs):
            total = 0.0
            for cf in cfs:
                t = years_from_base(cf["date"])
                if rate == -1 and t > 0:
                    return float("inf")
                try:
                    total += cf["amount"] / ((1 + rate) ** t)
                except (ZeroDivisionError, OverflowError):
                    return float("inf")
            return total

        # 符号が変わるか確認（IRRが存在するための必要条件）
        positive_cf = sum(cf["amount"] for cf in cash_flows if cf["amount"] > 0)
        negative_cf = sum(cf["amount"] for cf in cash_flows if cf["amount"] < 0)

        if positive_cf <= 0 or negative_cf >= 0:
            # すべて同符号の場合はIRR計算不可
            return None

        # ニュートン・ラフソン法でIRRを探索
        rate = 0.1  # 初期推定値（10%）

        for _ in range(max_iterations):
            npv = xnpv(rate, cash_flows)

            # 微分（数値微分）
            h = 0.0001
            npv_plus = xnpv(rate + h, cash_flows)
            derivative = (npv_plus - npv) / h

            if abs(derivative) < 1e-10:
                break

            new_rate = rate - npv / derivative

            # 収束判定
            if abs(new_rate - rate) < tolerance:
                # 年率IRRを%で返す
                return new_rate * 100

            rate = new_rate

            # 範囲制限（-99%から1000%）
            if rate < -0.99:
                rate = -0.99
            elif rate > 10:
                rate = 10

        # 収束しなかった場合は二分法で再試行
        low, high = -0.99, 10.0

        for _ in range(100):
            mid = (low + high) / 2
            npv = xnpv(mid, cash_flows)

            if abs(npv) < tolerance:
                return mid * 100

            if xnpv(low, cash_flows) * npv < 0:
                high = mid
            else:
                low = mid

        # それでも収束しない場合
        return None

    @staticmethod
    def calculate_irr_for_all_holdings():
        """
        すべての保有銘柄のIRRを計算

        Returns:
            dict: {ticker_symbol: {'irr': float or None, 'error': str or None}}
        """
        holdings = Holding.query.all()
        results = {}

        for holding in holdings:
            result = PerformanceService.calculate_irr_for_holding(holding.ticker_symbol)
            results[holding.ticker_symbol] = {
                "irr": result["irr"],
                "error": result["error"],
            }

        return results

    @staticmethod
    def calculate_irr_for_realized(ticker_symbol):
        """
        売却済み銘柄のIRR（内部収益率）を計算する

        キャッシュフロー:
        - 買い: マイナス（投資）
        - 配当: プラス（受取）- 保有期間中のもの
        - 売り: プラス（売却代金）

        Returns:
            dict: {'irr': float or None, 'cash_flows': list, 'error': str or None}
        """
        from datetime import date as date_class

        # 取引履歴を取得
        transactions = (
            Transaction.query.filter_by(ticker_symbol=ticker_symbol)
            .order_by(Transaction.transaction_date)
            .all()
        )

        if not transactions:
            return {"irr": None, "cash_flows": [], "error": "No transactions found"}

        # 売却取引があるか確認
        sell_transactions = [tx for tx in transactions if tx.transaction_type == "SELL"]
        if not sell_transactions:
            return {
                "irr": None,
                "cash_flows": [],
                "error": "No sell transactions (not realized)",
            }

        # 配当履歴を取得
        dividends = (
            Dividend.query.filter_by(ticker_symbol=ticker_symbol)
            .order_by(Dividend.ex_dividend_date)
            .all()
        )

        # キャッシュフローを日付順にまとめる
        cash_flows = []

        # 取引のキャッシュフロー
        for tx in transactions:
            if tx.transaction_type == "BUY":
                cf_amount = -float(tx.settlement_amount or 0)
            else:  # SELL
                cf_amount = float(tx.settlement_amount or 0)

            cash_flows.append(
                {
                    "date": tx.transaction_date,
                    "amount": cf_amount,
                    "type": tx.transaction_type,
                }
            )

        # 配当のキャッシュフロー（円換算）
        for div in dividends:
            if div.total_dividend and div.total_dividend > 0:
                div_amount = float(div.total_dividend)

                if div.currency and div.currency.upper() not in ["JPY", "日本円"]:
                    try:
                        rates = ExchangeRateFetcher.get_multiple_rates([div.currency])
                        if rates and div.currency in rates:
                            rate = rates[div.currency].get("rate", 1.0)
                            div_amount = div_amount * rate
                    except Exception:
                        pass

                cash_flows.append(
                    {
                        "date": div.ex_dividend_date,
                        "amount": div_amount,
                        "type": "DIVIDEND",
                    }
                )

        # 日付順でソート
        cash_flows.sort(key=lambda x: x["date"])

        if len(cash_flows) < 2:
            return {
                "irr": None,
                "cash_flows": cash_flows,
                "error": "Insufficient cash flows",
            }

        # XIRRを計算
        try:
            irr = PerformanceService._calculate_xirr(cash_flows)
            return {"irr": irr, "cash_flows": cash_flows, "error": None}
        except Exception as e:
            return {"irr": None, "cash_flows": cash_flows, "error": str(e)}

    @staticmethod
    def calculate_irr_for_all_realized():
        """
        全ての売却済み銘柄のIRRを計算する

        Returns:
            dict: {ticker_symbol: {'irr': float or None, 'error': str or None}}
        """
        # RealizedPnlテーブルからユニークなティッカーを取得
        realized_tickers = db.session.query(RealizedPnl.ticker_symbol).distinct().all()
        ticker_symbols = [t[0] for t in realized_tickers]

        results = {}
        for ticker in ticker_symbols:
            result = PerformanceService.calculate_irr_for_realized(ticker)
            results[ticker] = {"irr": result["irr"], "error": result["error"]}

        return results
