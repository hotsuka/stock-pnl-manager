# Yahoo Finance API 使用ガイド

## 概要

このアプリケーションでは、**yfinance**ライブラリを使用してYahoo FinanceからAPIでデータを取得しています。

## 必要なライブラリ

```bash
pip install yfinance
```

## 実装済みの機能

### 1. 株価取得 (`StockPriceFetcher`)

**場所:** `app/services/stock_price_fetcher.py`

#### 主要メソッド

##### 現在の株価を取得
```python
from app.services.stock_price_fetcher import StockPriceFetcher

# 単一銘柄の株価取得
price_data = StockPriceFetcher.get_current_price('AAPL')
# 結果: {'price': 180.0, 'currency': 'USD', 'timestamp': datetime, 'source': 'yahoo_finance'}

# 日本株（自動で.Tサフィックスを追加）
price_data = StockPriceFetcher.get_current_price('7203')  # トヨタ
# 内部的に '7203.T' として取得
```

##### 複数銘柄の株価を一括取得
```python
tickers = ['AAPL', 'MSFT', 'GOOGL']
prices = StockPriceFetcher.get_multiple_prices(tickers)
# 結果: {'AAPL': {...}, 'MSFT': {...}, 'GOOGL': {...}}
```

##### すべての保有銘柄の株価を更新
```python
result = StockPriceFetcher.update_all_holdings_prices()
# 結果: {'success': 10, 'failed': 2, 'errors': [...]}
```

##### 過去の株価を取得
```python
from datetime import datetime

historical = StockPriceFetcher.get_historical_prices(
    'AAPL',
    start_date='2024-01-01',
    end_date='2024-12-31'
)
# 結果: [{'date': datetime, 'close': float, 'currency': str}, ...]
```

#### キャッシュ機能

- デフォルトで当日の株価はDBにキャッシュされます
- 同じ日に複数回取得してもAPIを1回だけ呼び出します
- `use_cache=False`でキャッシュを無効化できます

```python
# キャッシュを使用しない
price_data = StockPriceFetcher.get_current_price('AAPL', use_cache=False)
```

---

### 2. 配当データ取得 (`DividendFetcher`)

**場所:** `app/services/dividend_fetcher.py`

#### 主要メソッド

##### 配当履歴を取得
```python
from app.services.dividend_fetcher import DividendFetcher
from datetime import datetime, timedelta

# 過去1年の配当履歴
dividends = DividendFetcher.fetch_dividends_yahoo('AAPL')
# 結果: [{'ex_date': date, 'amount': 0.24, 'currency': 'USD', 'source': 'yahoo_finance'}, ...]

# 期間を指定
dividends = DividendFetcher.fetch_dividends_yahoo(
    'AAPL',
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2024, 12, 31)
)
```

##### 配当をDBに保存
```python
result = DividendFetcher.save_dividends_to_db('AAPL', security_name='Apple Inc.')
# 結果: {'ticker': 'AAPL', 'total': 4, 'new': 2, 'existing': 2, 'errors': []}
```

##### すべての保有銘柄の配当を更新
```python
result = DividendFetcher.update_all_holdings_dividends()
# 結果: {'success': 15, 'failed': 3, 'errors': [...]}
```

---

### 3. 為替レート取得 (`ExchangeRateFetcher`)

**場所:** `app/services/exchange_rate_fetcher.py`

#### 主要メソッド

##### 現在の為替レートを取得
```python
from app.services.exchange_rate_fetcher import ExchangeRateFetcher

# USD/JPY
rate = ExchangeRateFetcher.get_exchange_rate('USD', 'JPY')
# 結果: {'rate': 150.5, 'from': 'USD', 'to': 'JPY', 'timestamp': datetime}

# EUR/JPY
rate = ExchangeRateFetcher.get_exchange_rate('EUR', 'JPY')

# JPY/USD（逆算）
rate = ExchangeRateFetcher.get_exchange_rate('JPY', 'USD')
```

##### 対応通貨ペア

- USD/JPY
- EUR/JPY
- GBP/JPY
- CNY/JPY
- KRW/JPY（韓国ウォン）
- TWD/JPY（台湾ドル）
- その他主要通貨

##### 過去の為替レートを取得
```python
rate = ExchangeRateFetcher.get_historical_rate('USD', '2024-01-15')
# 結果: {'rate': 148.2, 'from': 'USD', 'to': 'JPY', 'date': '2024-01-15'}
```

---

## Pythonコンソールでの使用例

### 使用方法

```bash
cd "C:\Users\大塚 久仁\stock-pnl-manager"
venv/Scripts/python.exe
```

```python
from app import create_app, db
from app.services.stock_price_fetcher import StockPriceFetcher
from app.services.dividend_fetcher import DividendFetcher
from app.services.exchange_rate_fetcher import ExchangeRateFetcher

# Flaskアプリのコンテキストを作成
app = create_app()
ctx = app.app_context()
ctx.push()

# 株価取得
price = StockPriceFetcher.get_current_price('AAPL')
print(f"AAPL: ${price['price']}")

# 日本株
price = StockPriceFetcher.get_current_price('7203')  # トヨタ
print(f"Toyota: ¥{price['price']}")

# 配当取得
dividends = DividendFetcher.fetch_dividends_yahoo('AAPL')
for div in dividends:
    print(f"{div['ex_date']}: ${div['amount']}")

# 為替レート
rate = ExchangeRateFetcher.get_exchange_rate('USD', 'JPY')
print(f"1 USD = {rate['rate']} JPY")

# 保有銘柄の株価を一括更新
result = StockPriceFetcher.update_all_holdings_prices()
print(f"更新: {result['success']}件成功, {result['failed']}件失敗")
```

---

## ティッカーシンボルの指定方法

### 米国株
```python
'AAPL'    # Apple
'MSFT'    # Microsoft
'GOOGL'   # Google
'TSLA'    # Tesla
```

### 日本株
```python
'7203'    # トヨタ自動車 → 内部的に '7203.T'
'6758'    # ソニー → 内部的に '6758.T'
'9984'    # ソフトバンク → 内部的に '9984.T'
```

数字のみのティッカーは自動的に `.T` サフィックスが追加されます。

### 韓国株
```python
'005930.KS'  # Samsung Electronics
'660'        # SK Hynix（アプリでは手動で指定）
```

### ETF
```python
'VOO'     # Vanguard S&P 500
'QQQ'     # Nasdaq 100
'SPY'     # S&P 500
'1475'    # iSTOPIX（日本）
```

---

## APIエンドポイント経由での使用

### 株価更新API（要実装）

```python
# app/routes/api.py に追加
@bp.route('/holdings/update-prices', methods=['POST'])
def update_holdings_prices():
    """保有銘柄の株価を一括更新"""
    result = StockPriceFetcher.update_all_holdings_prices()
    return jsonify({
        'success': True,
        'result': result
    })
```

### フロントエンドから呼び出し

```javascript
// ダッシュボードに「株価更新」ボタンを追加
async function updatePrices() {
    const response = await fetch('/api/holdings/update-prices', {
        method: 'POST'
    });
    const result = await response.json();

    if (result.success) {
        alert(`${result.result.success}件の株価を更新しました`);
        // ダッシュボードを再読み込み
        loadDashboardData();
    }
}
```

---

## yfinanceの基本的な使い方

### 直接使用する場合

```python
import yfinance as yf

# Tickerオブジェクトを作成
stock = yf.Ticker('AAPL')

# 株価情報
print(stock.info['currentPrice'])
print(stock.info['currency'])

# 過去データ
hist = stock.history(period='1mo')  # 1ヶ月
print(hist)

# 配当履歴
dividends = stock.dividends
print(dividends)

# 財務情報
print(stock.financials)
print(stock.balance_sheet)
print(stock.cashflow)
```

### 複数銘柄を一度に取得

```python
import yfinance as yf

# 複数銘柄のデータを取得
tickers = yf.Tickers('AAPL MSFT GOOGL')

# 各銘柄の情報にアクセス
print(tickers.tickers['AAPL'].info)
print(tickers.tickers['MSFT'].info)
```

---

## エラーハンドリング

### SSL証明書エラーの対処

アプリでは既に対処済みですが、日本語ユーザー名の環境で問題が発生する場合があります：

```python
import ssl
import os

# SSL検証を無効化
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context
```

### タイムアウト対策

```python
import yfinance as yf

# タイムアウトを設定
stock = yf.Ticker('AAPL')
hist = stock.history(period='1d', timeout=10)
```

---

## 注意事項

1. **API制限**: Yahoo Financeは非公式APIのため、過度なリクエストは避けてください
2. **レート制限**: 短時間に大量のリクエストを送ると一時的にブロックされる可能性があります
3. **データ遅延**: リアルタイムではなく、15-20分遅延のデータです
4. **キャッシュ活用**: 頻繁な更新が必要ない場合はキャッシュを活用してください
5. **日本株**: 数字のみのティッカーは自動で `.T` が追加されます

---

## 参考リンク

- [yfinance公式ドキュメント](https://pypi.org/project/yfinance/)
- [yfinance GitHub](https://github.com/ranaroussi/yfinance)
- [Yahoo Finance](https://finance.yahoo.com/)

---

## トラブルシューティング

### 株価が取得できない

1. ティッカーシンボルが正しいか確認
2. Yahoo Financeで該当銘柄が存在するか確認
3. インターネット接続を確認
4. SSL証明書エラーの場合は上記の対処法を実行

### 日本株が取得できない

- 数字のみのティッカーは自動で `.T` が追加されます
- 手動で指定する場合: `'7203.T'`

### 配当データが空

- すべての銘柄が配当を出しているわけではありません
- 期間を広げて再度取得してください
