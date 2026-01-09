"""
Yahoo Finance API テストスクリプト

このスクリプトは、Yahoo Finance APIを使用して
株価、配当、為替レートを取得する例を示します。
"""

# SSL証明書エラー対策（日本語ユーザー名対応）
import os
import ssl
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context

from app import create_app, db
from app.services.stock_price_fetcher import StockPriceFetcher
from app.services.dividend_fetcher import DividendFetcher
from app.services.exchange_rate_fetcher import ExchangeRateFetcher

# Flaskアプリのコンテキストを作成
app = create_app()
ctx = app.app_context()
ctx.push()

print('=' * 70)
print('Yahoo Finance API テスト')
print('=' * 70)

# ========================================
# 1. 株価取得テスト
# ========================================
print('\n[1] 株価取得テスト')
print('-' * 70)

# 米国株
print('\n米国株:')
tickers = ['AAPL', 'MSFT', 'TSLA']
for ticker in tickers:
    price_data = StockPriceFetcher.get_current_price(ticker)
    if price_data:
        print(f"  {ticker:6s}: {price_data['currency']} {price_data['price']:,.2f} (from {price_data['source']})")
    else:
        print(f"  {ticker:6s}: 取得失敗")

# 日本株
print('\n日本株:')
tickers = ['7203', '6758', '9984']
for ticker in tickers:
    price_data = StockPriceFetcher.get_current_price(ticker)
    if price_data:
        print(f"  {ticker:6s}: {price_data['currency']} {price_data['price']:,.2f} (from {price_data['source']})")
    else:
        print(f"  {ticker:6s}: 取得失敗")

# ========================================
# 2. 配当取得テスト
# ========================================
print('\n\n[2] 配当取得テスト')
print('-' * 70)

ticker = 'AAPL'
print(f'\n{ticker}の配当履歴:')
dividends = DividendFetcher.fetch_dividends_yahoo(ticker)
if dividends:
    print(f'  過去1年間の配当: {len(dividends)}件')
    for div in dividends[:5]:  # 最新5件のみ表示
        print(f"  {div['ex_date']}: {div['currency']} {div['amount']:.4f}")
else:
    print('  配当データなし')

# ========================================
# 3. 為替レート取得テスト
# ========================================
print('\n\n[3] 為替レート取得テスト')
print('-' * 70)

pairs = [('USD', 'JPY'), ('EUR', 'JPY'), ('KRW', 'JPY')]
for from_curr, to_curr in pairs:
    rate_data = ExchangeRateFetcher.get_exchange_rate(from_curr, to_curr)
    if rate_data:
        print(f"  1 {from_curr} = {rate_data['rate']:,.4f} {to_curr}")
    else:
        print(f"  {from_curr}/{to_curr}: 取得失敗")

# ========================================
# 4. 複数銘柄一括取得テスト
# ========================================
print('\n\n[4] 複数銘柄一括取得テスト')
print('-' * 70)

tickers = ['AAPL', 'MSFT', 'GOOGL', '7203', '6758']
print(f'\n{len(tickers)}銘柄を一括取得:')
prices = StockPriceFetcher.get_multiple_prices(tickers)
for ticker, price_data in prices.items():
    print(f"  {ticker:6s}: {price_data['currency']} {price_data['price']:,.2f}")

# ========================================
# 5. 保有銘柄の株価一括更新テスト
# ========================================
print('\n\n[5] 保有銘柄の株価一括更新テスト')
print('-' * 70)

print('\n全保有銘柄の株価を更新中...')
result = StockPriceFetcher.update_all_holdings_prices()
print(f"  成功: {result['success']}件")
print(f"  失敗: {result['failed']}件")
if result['errors']:
    print('  エラー:')
    for error in result['errors'][:3]:  # 最初の3件のみ表示
        print(f"    - {error}")

# ========================================
# 6. 過去の株価取得テスト
# ========================================
print('\n\n[6] 過去の株価取得テスト')
print('-' * 70)

ticker = 'AAPL'
print(f'\n{ticker}の過去30日間の株価:')
from datetime import datetime, timedelta
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

historical = StockPriceFetcher.get_historical_prices(ticker, start_date, end_date)
if historical:
    print(f'  取得件数: {len(historical)}日分')
    # 最初と最後の5日分を表示
    print('  最初の5日:')
    for data in historical[:5]:
        print(f"    {data['date']}: {data['currency']} {data['close']:,.2f}")
    if len(historical) > 10:
        print('  ...')
        print('  最後の5日:')
        for data in historical[-5:]:
            print(f"    {data['date']}: {data['currency']} {data['close']:,.2f}")
else:
    print('  データ取得失敗')

print('\n' + '=' * 70)
print('テスト完了')
print('=' * 70)
