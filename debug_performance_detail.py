"""
Detailed debug for performance calculation on a specific date
"""
from app import create_app, db
from app.models import Transaction, Holding
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
from decimal import Decimal

app = create_app('development')

with app.app_context():
    print("=" * 80)
    print("2026-01-06の保有損益を詳細にデバッグ")
    print("=" * 80)

    # 取引履歴を取得
    transactions = Transaction.query.order_by(Transaction.transaction_date).all()

    # 全ての保有銘柄を特定
    all_tickers = sorted(list(set(t.ticker_symbol for t in transactions)))

    # yfinanceのティッカーに変換
    yf_tickers = []
    for t in all_tickers:
        if t.isdigit():
            yf_tickers.append(f"{t}.T")
        else:
            yf_tickers.append(t)

    yf_tickers.extend(['USDJPY=X', 'KRWJPY=X'])

    # 2026-01-05と2026-01-06のデータを取得
    start_date = datetime(2026, 1, 5).date()
    end_date = datetime(2026, 1, 7).date()

    print(f"\nデータ取得: {start_date} to {end_date}")

    # データ取得
    data = yf.download(yf_tickers, start=start_date, end=end_date,
                      interval='1d', progress=False, auto_adjust=True)

    if isinstance(data.columns, pd.MultiIndex):
        prices_df = data['Close']
    else:
        prices_df = data[['Close']].rename(columns={'Close': yf_tickers[0]})

    prices_df = prices_df.ffill()

    print(f"\n取得データの形状: {prices_df.shape}")
    print(f"データのインデックス: {prices_df.index.tolist()}")

    # 2026-01-06時点の保有数量を計算
    target_date = datetime(2026, 1, 6).date()

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

    print(f"\n{target_date}時点の保有銘柄数: {len([k for k, v in holdings_at_date.items() if v > 0])}")

    # 2026-01-06の損益を計算
    try:
        curr_ts = pd.Timestamp(target_date)
        indices = prices_df.index.get_indexer([curr_ts], method='pad')
        curr_idx = indices[0]

        if curr_idx >= 1:
            prev_idx = curr_idx - 1

            print(f"\ncurr_idx={curr_idx}, prev_idx={prev_idx}")
            print(f"curr_date={prices_df.index[curr_idx]}, prev_date={prices_df.index[prev_idx]}")

            print("\n" + "=" * 80)
            print("各銘柄の損益詳細")
            print("=" * 80)

            total_pnl = 0.0

            for ticker, qty in sorted(holdings_at_date.items()):
                if qty <= 0:
                    continue

                yf_t = f"{ticker}.T" if ticker.isdigit() else ticker

                if yf_t not in prices_df.columns:
                    print(f"\n{ticker}: 株価データなし")
                    continue

                curr_price = prices_df.iloc[curr_idx][yf_t]
                prev_price = prices_df.iloc[prev_idx][yf_t]

                if pd.isna(curr_price) or pd.isna(prev_price):
                    print(f"\n{ticker}: 株価がNaN")
                    continue

                # 通貨判定（yfinanceティッカーで判定）
                if yf_t.endswith('.T'):
                    currency = 'JPY'
                elif yf_t.endswith('.KS'):
                    currency = 'KRW'
                else:
                    currency = 'USD'

                # 為替レート取得
                rate = 1.0
                rate_info = "デフォルト"

                if currency == 'USD':
                    if 'USDJPY=X' in prices_df.columns:
                        rate = prices_df.iloc[curr_idx]['USDJPY=X']
                        if not pd.isna(rate) and rate != 0:
                            rate_info = f"USDJPY={rate}"
                        else:
                            rate = 1.0
                            rate_info = "USDJPY=NaN/0, デフォルト使用"
                elif currency == 'KRW':
                    if 'KRWJPY=X' in prices_df.columns:
                        rate = prices_df.iloc[curr_idx]['KRWJPY=X']
                        if not pd.isna(rate) and rate != 0:
                            rate_info = f"KRWJPY={rate}"
                        else:
                            rate = 1.0
                            rate_info = "KRWJPY=NaN/0, デフォルト使用"

                # 損益計算
                price_diff = float(curr_price) - float(prev_price)
                qty_float = float(qty)
                rate_float = float(rate)
                pnl = price_diff * qty_float * rate_float

                total_pnl += pnl

                # 出力
                print(f"\n{ticker} ({currency}):")
                print(f"  保有数量: {qty_float:,.2f}")
                print(f"  前日株価: {prev_price:,.4f} {currency}")
                print(f"  当日株価: {curr_price:,.4f} {currency}")
                print(f"  株価差分: {price_diff:,.4f} {currency}")
                print(f"  為替レート: {rate_info}")
                print(f"  計算: {price_diff:,.4f} * {qty_float:,.2f} * {rate_float:,.6f}")
                print(f"  損益: {pnl:,.2f} JPY")

            print("\n" + "=" * 80)
            print(f"合計保有損益: {total_pnl:,.2f} JPY")
            print("=" * 80)

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
