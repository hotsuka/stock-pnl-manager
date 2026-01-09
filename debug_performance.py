"""
Debug script to check performance calculation and exchange rates
"""
from app import create_app, db
from app.models import Transaction, Holding
from app.services import PerformanceService
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

app = create_app('development')

with app.app_context():
    print("=" * 80)
    print("保有銘柄の確認")
    print("=" * 80)

    holdings = Holding.query.filter(Holding.total_quantity > 0).all()
    for h in holdings:
        print(f"\n{h.ticker_symbol} - {h.security_name}")
        print(f"  保有数量: {h.total_quantity}")
        print(f"  通貨: {h.currency}")
        print(f"  現在価格: {h.current_price} {h.currency}")
        print(f"  評価額: {h.current_value} JPY")

    print("\n" + "=" * 80)
    print("為替レートと株価の確認")
    print("=" * 80)

    # Test fetching some sample data
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=5)

    # Get a few tickers for testing
    test_tickers = []
    for h in holdings[:3]:  # First 3 holdings
        ticker = h.ticker_symbol
        if ticker.isdigit():
            test_tickers.append(f"{ticker}.T")
        else:
            test_tickers.append(ticker)

    test_tickers.extend(['USDJPY=X', 'KRWJPY=X'])

    print(f"\n取得対象ティッカー: {test_tickers}")
    print(f"期間: {start_date} to {end_date}")

    try:
        data = yf.download(test_tickers, start=start_date, end=end_date + timedelta(days=1),
                          interval='1d', progress=False, auto_adjust=True)

        if not data.empty:
            print(f"\n取得データの形状: {data.shape}")
            print("\n最新の株価データ:")
            if isinstance(data.columns, pd.MultiIndex):
                if 'Close' in data.columns.get_level_values(0):
                    print(data['Close'].tail())
            else:
                print(data.tail())

            print("\n為替レート:")
            if 'USDJPY=X' in data.columns or ('Close' in str(data.columns) and 'USDJPY=X' in str(data.columns)):
                try:
                    if isinstance(data.columns, pd.MultiIndex):
                        usd_rate = data['Close']['USDJPY=X'].iloc[-1] if 'USDJPY=X' in data['Close'].columns else None
                        krw_rate = data['Close']['KRWJPY=X'].iloc[-1] if 'KRWJPY=X' in data['Close'].columns else None
                    else:
                        usd_rate = data['USDJPY=X'].iloc[-1] if 'USDJPY=X' in data.columns else None
                        krw_rate = data['KRWJPY=X'].iloc[-1] if 'KRWJPY=X' in data.columns else None

                    if usd_rate:
                        print(f"  USDJPY: {usd_rate}")
                    if krw_rate:
                        print(f"  KRWJPY: {krw_rate}")
                except Exception as e:
                    print(f"  為替レート取得エラー: {e}")
        else:
            print("データが取得できませんでした")

    except Exception as e:
        print(f"エラー: {e}")

    print("\n" + "=" * 80)
    print("損益計算のサンプル実行（過去3日間）")
    print("=" * 80)

    try:
        # Get last 3 days of performance data
        perf_data = PerformanceService.get_performance_history(days=3)

        if perf_data:
            print(f"\n取得データ件数: {len(perf_data)}")
            for day in perf_data:
                print(f"\n日付: {day['date']}")
                print(f"  A. 保有損益: {day['holding_pnl']:,.2f} JPY")
                print(f"  B. 実現損益: {day['realized_pnl']:,.2f} JPY")
                print(f"  C. 受取配当: {day['dividend_income']:,.2f} JPY")
                print(f"  合計: {day['total']:,.2f} JPY")
        else:
            print("データなし")

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
