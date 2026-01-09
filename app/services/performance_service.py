import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict
from app import db
from app.models import Transaction, RealizedPnl, Dividend, Holding
from app.services.exchange_rate_fetcher import ExchangeRateFetcher

class PerformanceService:
    @staticmethod
    def get_performance_history(days=365):
        """
        過去N日間の日次損益推移を計算する
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # 1. 全取引履歴を取得
        transactions = Transaction.query.order_by(Transaction.transaction_date).all()
        if not transactions:
            return []

        # 2. 過去の全保有銘柄を特定
        all_tickers = sorted(list(set(t.ticker_symbol for t in transactions)))
        
        # 3. ヒストリカル株価と為替レートを取得
        yf_tickers = []
        for t in all_tickers:
            if t.isdigit():
                yf_tickers.append(f"{t}.T")
            else:
                yf_tickers.append(t)
        
        yf_tickers.extend(['USDJPY=X', 'KRWJPY=X'])
        
        min_tx_date = transactions[0].transaction_date
        download_start = min(start_date, min_tx_date) - timedelta(days=10)
        
        print(f"DEBUG: Tickers={len(yf_tickers)}, Period={download_start} to {end_date}")
        
        # バッチ処理で取得
        all_data_frames = []
        batch_size = 15
        for i in range(0, len(yf_tickers), batch_size):
            batch = yf_tickers[i:i+batch_size]
            try:
                # auto_adjust=True を使用して、常に調整後終値を 'Close' として取得
                batch_data = yf.download(batch, start=download_start, end=end_date + timedelta(days=2), interval='1d', progress=False, auto_adjust=True)
                if not batch_data.empty:
                    # 多銘柄の場合は MultiIndex、1銘柄の場合は単一階層
                    if isinstance(batch_data.columns, pd.MultiIndex):
                        if 'Close' in batch_data.columns.get_level_values(0):
                            all_data_frames.append(batch_data['Close'])
                    else:
                        if 'Close' in batch_data.columns:
                            all_data_frames.append(batch_data[['Close']].rename(columns={'Close': batch[0]}))
                        elif len(batch) == 1:
                            # 1銘柄で MultiIndex でない場合、そのまま Close カラムがあるはず
                            all_data_frames.append(batch_data[['Close']].rename(columns={'Close': batch[0]}))
            except Exception as e:
                print(f"DEBUG: Batch {batch} failed: {e}")

        if not all_data_frames:
            print("DEBUG: No price data obtained.")
            return []

        # 全ての DataFrame を横に結合
        prices_df = pd.concat(all_data_frames, axis=1)
        prices_df = prices_df.loc[:, ~prices_df.columns.duplicated()] # 重複排除
        prices_df = prices_df.ffill() # 欠損値を埋める

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
                    if tx.transaction_type == 'BUY':
                        temp_qty[tx.ticker_symbol] += Decimal(str(tx.quantity))
                    elif tx.transaction_type == 'SELL':
                        temp_qty[tx.ticker_symbol] -= Decimal(str(tx.quantity))
            
            if iter_date >= start_date:
                for t, q in temp_qty.items():
                    if q > 0:
                        full_history_holdings[iter_date][t] = q
            
            iter_date += timedelta(days=1)

        # 5. 各有効日ごとに計算
        results = []
        valid_dates = sorted(list(set(d.date() for d in prices_df.index if d.date() >= start_date)))
        
        for i in range(len(valid_dates)):
            d = valid_dates[i]
            # prices_df において、d 以前で最新のデータがある行を探す
            try:
                curr_ts = pd.Timestamp(d)
                # prices_df.index から curr_ts 以前の最新インデックス
                indices = prices_df.index.get_indexer([curr_ts], method='pad')
                curr_idx = indices[0]
                if curr_idx <= 0: continue
                
                prev_idx = curr_idx - 1
            except:
                continue
            
            holding_pnl = 0.0
            realized_pnl = 0.0
            dividend_income = 0.0
            
            holdings_at_date = full_history_holdings[d]
            
            for ticker, qty in holdings_at_date.items():
                if qty <= 0: continue

                yf_t = f"{ticker}.T" if ticker.isdigit() else ticker
                if yf_t not in prices_df.columns:
                    continue

                curr_price = prices_df.iloc[curr_idx][yf_t]
                prev_price = prices_df.iloc[prev_idx][yf_t]

                if pd.isna(curr_price) or pd.isna(prev_price):
                    continue

                # 為替レート（yfinanceティッカーで通貨を判定）
                if yf_t.endswith('.T'):
                    currency = 'JPY'
                elif yf_t.endswith('.KS'):
                    currency = 'KRW'
                else:
                    currency = 'USD'
                
                rate = 1.0
                if currency == 'USD' and 'USDJPY=X' in prices_df.columns:
                    rate = prices_df.iloc[curr_idx]['USDJPY=X']
                elif currency == 'KRW' and 'KRWJPY=X' in prices_df.columns:
                    rate = prices_df.iloc[curr_idx]['KRWJPY=X']
                
                if pd.isna(rate) or rate == 0: rate = 1.0
                
                diff = (float(curr_price) - float(prev_price)) * float(qty) * float(rate)
                holding_pnl += diff
                
            # B. 売却損益
            daily_realized = db.session.query(db.func.sum(RealizedPnl.realized_pnl)).filter(RealizedPnl.sell_date == d).scalar()
            realized_pnl = float(daily_realized or 0)
            
            # C. 受取配当
            for div in div_by_date[d]:
                qty_at_div = holdings_at_date.get(div.ticker_symbol, 0)
                if qty_at_div > 0:
                    rate = 1.0
                    if div.currency == 'USD' and 'USDJPY=X' in prices_df.columns:
                        rate = prices_df.iloc[curr_idx]['USDJPY=X']
                    elif div.currency == 'KRW' and 'KRWJPY=X' in prices_df.columns:
                        rate = prices_df.iloc[curr_idx]['KRWJPY=X']
                    
                    if pd.isna(rate) or rate == 0: rate = 1.0
                    dividend_income += float(div.dividend_amount or 0) * float(qty_at_div) * float(rate)
            
            results.append({
                'date': d.isoformat(),
                'holding_pnl': round(holding_pnl, 2),
                'realized_pnl': round(realized_pnl, 2),
                'dividend_income': round(dividend_income, 2),
                'total': round(holding_pnl + realized_pnl + dividend_income, 2)
            })
            
        return results

    @staticmethod
    def get_monthly_performance_history():
        """
        過去1年間の月次損益推移を計算する
        """
        daily_data = PerformanceService.get_performance_history(days=400)
        if not daily_data:
            return []

        monthly_stats = defaultdict(lambda: {'holding_pnl': 0.0, 'realized_pnl': 0.0, 'dividend_income': 0.0})
        for day in daily_data:
            month_key = day['date'][:7]
            monthly_stats[month_key]['holding_pnl'] += day['holding_pnl']
            monthly_stats[month_key]['realized_pnl'] += day['realized_pnl']
            monthly_stats[month_key]['dividend_income'] += day['dividend_income']

        sorted_months = sorted(monthly_stats.keys())
        results = []
        for m in sorted_months:
            s = monthly_stats[m]
            results.append({
                'date': m,
                'holding_pnl': round(s['holding_pnl'], 2),
                'realized_pnl': round(s['realized_pnl'], 2),
                'dividend_income': round(s['dividend_income'], 2),
                'total': round(s['holding_pnl'] + s['realized_pnl'] + s['dividend_income'], 2)
            })
        return results

    @staticmethod
    def get_daily_detail(target_date_str):
        """
        特定の日付の損益詳細を銘柄ごとに取得する
        """
        from datetime import datetime

        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()

        # 全取引履歴を取得
        transactions = Transaction.query.order_by(Transaction.transaction_date).all()
        if not transactions:
            return {'holding_details': [], 'realized_details': [], 'dividend_details': []}

        # 全保有銘柄を特定
        all_tickers = sorted(list(set(t.ticker_symbol for t in transactions)))

        # yfinanceティッカーに変換
        yf_tickers = []
        for t in all_tickers:
            if t.isdigit():
                yf_tickers.append(f"{t}.T")
            else:
                yf_tickers.append(t)

        yf_tickers.extend(['USDJPY=X', 'KRWJPY=X'])

        # target_dateの前後のデータを取得
        start_date = target_date - timedelta(days=5)
        end_date = target_date + timedelta(days=2)

        # バッチ処理で取得
        all_data_frames = []
        batch_size = 15
        for i in range(0, len(yf_tickers), batch_size):
            batch = yf_tickers[i:i+batch_size]
            try:
                batch_data = yf.download(batch, start=start_date, end=end_date, interval='1d', progress=False, auto_adjust=True)
                if not batch_data.empty:
                    if isinstance(batch_data.columns, pd.MultiIndex):
                        if 'Close' in batch_data.columns.get_level_values(0):
                            all_data_frames.append(batch_data['Close'])
                    else:
                        if 'Close' in batch_data.columns:
                            all_data_frames.append(batch_data[['Close']].rename(columns={'Close': batch[0]}))
                        elif len(batch) == 1:
                            all_data_frames.append(batch_data[['Close']].rename(columns={'Close': batch[0]}))
            except:
                pass

        if not all_data_frames:
            return {'holding_details': [], 'realized_details': [], 'dividend_details': []}

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
                    if tx.transaction_type == 'BUY':
                        holdings_at_date[tx.ticker_symbol] += Decimal(str(tx.quantity))
                    elif tx.transaction_type == 'SELL':
                        holdings_at_date[tx.ticker_symbol] -= Decimal(str(tx.quantity))
            iter_date += timedelta(days=1)

        # インデックスを取得
        try:
            curr_ts = pd.Timestamp(target_date)
            indices = prices_df.index.get_indexer([curr_ts], method='pad')
            curr_idx = indices[0]

            if curr_idx <= 0:
                return {'holding_details': [], 'realized_details': [], 'dividend_details': []}

            prev_idx = curr_idx - 1
        except:
            return {'holding_details': [], 'realized_details': [], 'dividend_details': []}

        # A. 保有損益の詳細
        holding_details = []

        for ticker, qty in sorted(holdings_at_date.items()):
            if qty <= 0:
                continue

            yf_t = f"{ticker}.T" if ticker.isdigit() else ticker
            if yf_t not in prices_df.columns:
                continue

            curr_price = prices_df.iloc[curr_idx][yf_t]
            prev_price = prices_df.iloc[prev_idx][yf_t]

            if pd.isna(curr_price) or pd.isna(prev_price):
                continue

            # 通貨判定
            if yf_t.endswith('.T'):
                currency = 'JPY'
            elif yf_t.endswith('.KS'):
                currency = 'KRW'
            else:
                currency = 'USD'

            # 為替レート取得
            rate = 1.0
            if currency == 'USD' and 'USDJPY=X' in prices_df.columns:
                rate = prices_df.iloc[curr_idx]['USDJPY=X']
                if pd.isna(rate) or rate == 0:
                    rate = 1.0
            elif currency == 'KRW' and 'KRWJPY=X' in prices_df.columns:
                rate = prices_df.iloc[curr_idx]['KRWJPY=X']
                if pd.isna(rate) or rate == 0:
                    rate = 1.0

            price_diff = float(curr_price) - float(prev_price)
            pnl = price_diff * float(qty) * float(rate)

            # 銘柄名を取得
            tx = Transaction.query.filter_by(ticker_symbol=ticker).first()
            security_name = tx.security_name if tx else ticker

            holding_details.append({
                'ticker_symbol': ticker,
                'security_name': security_name,
                'quantity': float(qty),
                'prev_price': float(prev_price),
                'curr_price': float(curr_price),
                'price_change': price_diff,
                'currency': currency,
                'exchange_rate': float(rate),
                'pnl': round(pnl, 2)
            })

        # B. 実現損益の詳細
        realized_details = []
        daily_realized = RealizedPnl.query.filter_by(sell_date=target_date).all()
        for r in daily_realized:
            tx = Transaction.query.filter_by(ticker_symbol=r.ticker_symbol).first()
            security_name = tx.security_name if tx else r.ticker_symbol

            realized_details.append({
                'ticker_symbol': r.ticker_symbol,
                'security_name': security_name,
                'quantity': float(r.quantity),
                'average_cost': float(r.average_cost),
                'sell_price': float(r.sell_price),
                'pnl': float(r.realized_pnl)
            })

        # C. 配当の詳細
        dividend_details = []
        dividends = Dividend.query.filter_by(ex_dividend_date=target_date).all()

        for div in dividends:
            qty_at_div = holdings_at_date.get(div.ticker_symbol, 0)
            if qty_at_div > 0:
                rate = 1.0
                if div.currency == 'USD' and 'USDJPY=X' in prices_df.columns:
                    rate = prices_df.iloc[curr_idx]['USDJPY=X']
                    if pd.isna(rate) or rate == 0:
                        rate = 1.0
                elif div.currency == 'KRW' and 'KRWJPY=X' in prices_df.columns:
                    rate = prices_df.iloc[curr_idx]['KRWJPY=X']
                    if pd.isna(rate) or rate == 0:
                        rate = 1.0

                tx = Transaction.query.filter_by(ticker_symbol=div.ticker_symbol).first()
                security_name = tx.security_name if tx else div.ticker_symbol

                dividend_jpy = float(div.dividend_amount or 0) * float(qty_at_div) * float(rate)

                dividend_details.append({
                    'ticker_symbol': div.ticker_symbol,
                    'security_name': security_name,
                    'quantity': float(qty_at_div),
                    'dividend_per_share': float(div.dividend_amount or 0),
                    'currency': div.currency,
                    'exchange_rate': float(rate),
                    'total_dividend': round(dividend_jpy, 2)
                })

        return {
            'holding_details': holding_details,
            'realized_details': realized_details,
            'dividend_details': dividend_details
        }
