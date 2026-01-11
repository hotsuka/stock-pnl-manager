# API仕様書

Stock P&L Manager API v1.0

ベースURL: `/api`

## ⚠️ 重要: ポート番号について

このドキュメントのサンプルコードでは開発環境用のポート番号（5000）を使用しています。

- **開発環境**: `http://localhost:5000/api/*`
- **本番環境**: `http://localhost:8000/api/*`

本番環境で使用する場合は、URLのポート番号を8000に変更してください。

**例**:
```bash
# 開発環境
curl http://localhost:5000/api/holdings

# 本番環境
curl http://localhost:8000/api/holdings
```

---

## 目次

1. [株価API](#1-株価api)
2. [為替レートAPI](#2-為替レートapi)
3. [配当API](#3-配当api)
4. [保有銘柄API](#4-保有銘柄api)
5. [取引履歴API](#5-取引履歴api)
6. [実現損益API](#6-実現損益api)
7. [ダッシュボードAPI](#7-ダッシュボードapi)
8. [損益推移API](#8-損益推移api)
9. [株式評価指標API](#9-株式評価指標api)
10. [エラーハンドリング](#10-エラーハンドリング)

---

## 1. 株価API

### 1.1 株価取得

指定したティッカーシンボルの現在株価を取得します。

**エンドポイント**: `GET /api/stock-price/<ticker>`

**URLパラメータ**:
- `ticker` (required): ティッカーシンボル（例: AAPL, 9984.T, 005930.KS）

**クエリパラメータ**:
- `cache` (optional): キャッシュ使用フラグ（デフォルト: "true"）
  - 値: "true" | "false"

**リクエスト例**:
```bash
# キャッシュを使用して株価取得
curl -X GET "http://localhost:5000/api/stock-price/AAPL"

# キャッシュを使わずに株価取得
curl -X GET "http://localhost:5000/api/stock-price/AAPL?cache=false"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "ticker": "AAPL",
  "data": {
    "ticker": "AAPL",
    "current_price": 182.45,
    "previous_close": 180.20,
    "day_change": 2.25,
    "day_change_pct": 1.25,
    "currency": "USD",
    "last_updated": "2026-01-10T14:30:00"
  }
}
```

**エラーレスポンス**:

- 400 Bad Request (バリデーションエラー):
```json
{
  "success": false,
  "error": "ティッカーシンボルが指定されていません"
}
```

- 404 Not Found (データ未取得):
```json
{
  "success": false,
  "error": "株価データを取得できませんでした: INVALID"
}
```

- 503 Service Unavailable (API呼び出しエラー):
```json
{
  "success": false,
  "error": "株価の取得中にエラーが発生しました: Connection timeout"
}
```

---

### 1.2 全保有銘柄の株価一括更新

全保有銘柄の株価を一括更新します。

**エンドポイント**: `POST /api/stock-price/update-all`

**リクエストボディ**: なし

**リクエスト例**:
```bash
curl -X POST "http://localhost:5000/api/stock-price/update-all"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "results": {
    "total": 15,
    "success": 14,
    "failed": 1,
    "details": [
      {
        "ticker": "AAPL",
        "success": true,
        "price": 182.45
      },
      {
        "ticker": "INVALID",
        "success": false,
        "error": "株価データを取得できませんでした"
      }
    ]
  }
}
```

**エラーレスポンス**:

- 503 Service Unavailable:
```json
{
  "success": false,
  "error": "株価の一括更新中にエラーが発生しました: Database connection failed"
}
```

---

## 2. 為替レートAPI

### 2.1 複数通貨レート取得

複数通貨の為替レートを一括取得します。

**エンドポイント**: `GET /api/exchange-rate/multiple`

**クエリパラメータ**:
- `currencies` (optional): カンマ区切りの通貨コード（デフォルト: "USD,KRW"）
- `to` (optional): 変換先通貨（デフォルト: "JPY"）

**リクエスト例**:
```bash
# デフォルト（USD, KRWからJPYへの為替レート）
curl -X GET "http://localhost:5000/api/exchange-rate/multiple"

# カスタム通貨指定
curl -X GET "http://localhost:5000/api/exchange-rate/multiple?currencies=USD,EUR,GBP&to=JPY"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "rates": {
    "USD": {
      "from": "USD",
      "to": "JPY",
      "rate": 149.50,
      "last_updated": "2026-01-10T10:00:00"
    },
    "KRW": {
      "from": "KRW",
      "to": "JPY",
      "rate": 0.1124,
      "last_updated": "2026-01-10T10:00:00"
    }
  },
  "to_currency": "JPY"
}
```

---

### 2.2 為替レート取得

指定した通貨ペアの為替レートを取得します。

**エンドポイント**: `GET /api/exchange-rate/<from_currency>`

**URLパラメータ**:
- `from_currency` (required): 変換元通貨コード（例: USD, KRW, EUR）

**クエリパラメータ**:
- `to` (optional): 変換先通貨コード（デフォルト: "JPY"）

**リクエスト例**:
```bash
# USDからJPYへの為替レート
curl -X GET "http://localhost:5000/api/exchange-rate/USD"

# USDからEURへの為替レート
curl -X GET "http://localhost:5000/api/exchange-rate/USD?to=EUR"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "data": {
    "from": "USD",
    "to": "JPY",
    "rate": 149.50,
    "last_updated": "2026-01-10T10:00:00"
  }
}
```

**エラーレスポンス**:

- 404 Not Found:
```json
{
  "success": false,
  "error": "Failed to fetch exchange rate for USD/EUR"
}
```

---

### 2.3 通貨変換

金額を指定した通貨間で変換します。

**エンドポイント**: `POST /api/exchange-rate/convert`

**リクエストボディ**:
```json
{
  "amount": 1000.00,
  "from": "USD",
  "to": "JPY"
}
```

**パラメータ**:
- `amount` (required): 変換する金額（正の数値）
- `from` (required): 変換元通貨コード
- `to` (optional): 変換先通貨コード（デフォルト: "JPY"）

**リクエスト例**:
```bash
curl -X POST "http://localhost:5000/api/exchange-rate/convert" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000.00,
    "from": "USD",
    "to": "JPY"
  }'
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "data": {
    "from_amount": 1000.00,
    "from_currency": "USD",
    "to_amount": 149500.00,
    "to_currency": "JPY",
    "exchange_rate": 149.50,
    "converted_at": "2026-01-10T10:00:00"
  }
}
```

**エラーレスポンス**:

- 400 Bad Request (リクエストボディなし):
```json
{
  "success": false,
  "error": "リクエストボディが空です"
}
```

- 400 Bad Request (必須フィールド不足):
```json
{
  "success": false,
  "error": "必須フィールドが不足しています: amount, from",
  "missing_fields": ["amount", "from"]
}
```

- 400 Bad Request (金額が正の数値でない):
```json
{
  "success": false,
  "error": "金額は正の数値である必要があります",
  "field": "amount",
  "value": -100
}
```

- 503 Service Unavailable:
```json
{
  "success": false,
  "error": "通貨変換に失敗しました: USD → EUR"
}
```

---

## 3. 配当API

### 3.1 配当履歴取得

指定したティッカーの配当履歴を取得します。

**エンドポイント**: `GET /api/dividends/<ticker>`

**URLパラメータ**:
- `ticker` (required): ティッカーシンボル

**リクエスト例**:
```bash
curl -X GET "http://localhost:5000/api/dividends/AAPL"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "ticker": "AAPL",
  "count": 4,
  "dividends": [
    {
      "id": 1,
      "ticker_symbol": "AAPL",
      "ex_dividend_date": "2025-11-08",
      "payment_date": "2025-11-14",
      "dividend_amount": 0.24,
      "currency": "USD",
      "total_dividend": 24.00,
      "quantity_held": 100,
      "source": "yahoo",
      "created_at": "2025-11-10T10:00:00"
    }
  ]
}
```

---

### 3.2 配当データ取得・保存

外部APIから配当データを取得してDBに保存します。

**エンドポイント**: `POST /api/dividends/fetch/<ticker>`

**URLパラメータ**:
- `ticker` (required): ティッカーシンボル

**リクエスト例**:
```bash
curl -X POST "http://localhost:5000/api/dividends/fetch/AAPL"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "results": {
    "ticker": "AAPL",
    "new_records": 2,
    "updated_records": 0,
    "total_records": 12,
    "source": "yahoo"
  }
}
```

---

### 3.3 全保有銘柄の配当データ更新

全保有銘柄の配当データを一括更新します。

**エンドポイント**: `POST /api/dividends/update-all`

**リクエスト例**:
```bash
curl -X POST "http://localhost:5000/api/dividends/update-all"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "total_holdings": 15,
  "success": 14,
  "failed": 1,
  "details": [
    {
      "ticker": "AAPL",
      "success": true,
      "new_records": 2
    },
    {
      "ticker": "INVALID",
      "success": false,
      "error": "配当データを取得できませんでした"
    }
  ]
}
```

**エラーレスポンス**:

- 500 Internal Server Error:
```json
{
  "success": false,
  "error": "Database connection failed"
}
```

---

### 3.4 配当サマリー取得

全銘柄の配当サマリーを年度別に集計して取得します。

**エンドポイント**: `GET /api/dividends/summary`

**リクエスト例**:
```bash
curl -X GET "http://localhost:5000/api/dividends/summary"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "dividends": [
    {
      "ticker_symbol": "AAPL",
      "security_name": "Apple Inc.",
      "total_dividends": 15000.00,
      "total_investment": 500000.00,
      "dividend_yield": 3.00,
      "yearly_dividends": {
        "2025": 8000.00,
        "2024": 5000.00,
        "2023": 2000.00
      }
    }
  ],
  "totals": {
    "total_dividends": 45000.00,
    "total_investment": 2000000.00,
    "dividend_yield": 2.25,
    "yearly_totals": {
      "2025": 25000.00,
      "2024": 15000.00,
      "2023": 5000.00,
      "2022年以前": 0
    }
  }
}
```

**データ説明**:
- `total_dividends`: 総配当額（JPY換算）
- `total_investment`: 総投資額（JPY）
- `dividend_yield`: 配当利回り（%）
- `yearly_dividends`: 年度別配当額（降順、2022年以前は最後）

---

## 4. 保有銘柄API

### 4.1 全保有銘柄取得

全保有銘柄のリストを取得します。

**エンドポイント**: `GET /api/holdings`

**リクエスト例**:
```bash
curl -X GET "http://localhost:5000/api/holdings"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "count": 15,
  "holdings": [
    {
      "id": 1,
      "ticker_symbol": "AAPL",
      "security_name": "Apple Inc.",
      "total_quantity": 100.0,
      "average_cost": 150.00,
      "currency": "USD",
      "total_cost": 15000.00,
      "current_price": 182.45,
      "previous_close": 180.20,
      "day_change_pct": 1.25,
      "current_value": 18245.00,
      "unrealized_pnl": 3245.00,
      "unrealized_pnl_pct": 21.63,
      "last_updated": "2026-01-10T14:30:00",
      "created_at": "2024-01-15T10:00:00"
    }
  ]
}
```

---

### 4.2 保有銘柄詳細取得

指定したティッカーの保有銘柄詳細を取得します。

**エンドポイント**: `GET /api/holdings/<ticker>`

**URLパラメータ**:
- `ticker` (required): ティッカーシンボル

**リクエスト例**:
```bash
curl -X GET "http://localhost:5000/api/holdings/AAPL"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "holding": {
    "id": 1,
    "ticker_symbol": "AAPL",
    "security_name": "Apple Inc.",
    "total_quantity": 100.0,
    "average_cost": 150.00,
    "currency": "USD",
    "total_cost": 15000.00,
    "current_price": 182.45,
    "previous_close": 180.20,
    "day_change_pct": 1.25,
    "current_value": 18245.00,
    "unrealized_pnl": 3245.00,
    "unrealized_pnl_pct": 21.63,
    "last_updated": "2026-01-10T14:30:00",
    "created_at": "2024-01-15T10:00:00"
  }
}
```

**エラーレスポンス**:

- 404 Not Found:
```json
{
  "success": false,
  "error": "保有銘柄が見つかりません: INVALID"
}
```

- 500 Internal Server Error:
```json
{
  "success": false,
  "error": "保有銘柄の取得に失敗しました: Database error"
}
```

---

### 4.3 保有銘柄削除

指定した保有銘柄と関連データを削除します。

**エンドポイント**: `DELETE /api/holdings/<ticker>`

**URLパラメータ**:
- `ticker` (required): ティッカーシンボル

**リクエスト例**:
```bash
curl -X DELETE "http://localhost:5000/api/holdings/AAPL"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "message": "AAPL の保有銘柄と関連データを削除しました",
  "deleted": {
    "ticker": "AAPL",
    "transactions": 12,
    "dividends": 8,
    "realized_pnl": 2
  }
}
```

**エラーレスポンス**:

- 404 Not Found:
```json
{
  "success": false,
  "error": "保有銘柄が見つかりません: INVALID"
}
```

- 500 Internal Server Error:
```json
{
  "success": false,
  "error": "削除に失敗しました: Database transaction failed"
}
```

**注意**: この操作により以下のデータが削除されます
- 保有銘柄レコード
- 関連する全取引履歴
- 関連する全配当データ
- 関連する全実現損益レコード

---

## 5. 取引履歴API

### 5.1 取引履歴一覧取得

取引履歴のリストを取得します。

**エンドポイント**: `GET /api/transactions`

**クエリパラメータ**:
- `ticker` (optional): ティッカーシンボルでフィルタ
- `limit` (optional): 取得件数の上限

**リクエスト例**:
```bash
# 全取引履歴取得
curl -X GET "http://localhost:5000/api/transactions"

# 特定銘柄の取引履歴
curl -X GET "http://localhost:5000/api/transactions?ticker=AAPL"

# 最新10件のみ取得
curl -X GET "http://localhost:5000/api/transactions?limit=10"

# 組み合わせ
curl -X GET "http://localhost:5000/api/transactions?ticker=AAPL&limit=5"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "count": 10,
  "total_count": 125,
  "transactions": [
    {
      "id": 1,
      "transaction_date": "2025-12-15",
      "ticker_symbol": "AAPL",
      "security_name": "Apple Inc.",
      "transaction_type": "BUY",
      "currency": "USD",
      "quantity": 50.0,
      "unit_price": 180.50,
      "commission": 10.00,
      "settlement_amount": 9035.00,
      "exchange_rate": 149.50,
      "settlement_currency": "JPY",
      "created_at": "2025-12-15T10:30:00",
      "updated_at": "2025-12-15T10:30:00"
    }
  ]
}
```

**データ説明**:
- `count`: 返却された取引件数
- `total_count`: フィルタ条件に一致する総取引件数
- `transactions`: 取引データの配列（取引日降順）

---

### 5.2 取引詳細取得

指定したIDの取引詳細を取得します。

**エンドポイント**: `GET /api/transactions/<transaction_id>`

**URLパラメータ**:
- `transaction_id` (required): 取引ID（整数）

**リクエスト例**:
```bash
curl -X GET "http://localhost:5000/api/transactions/123"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "transaction": {
    "id": 123,
    "transaction_date": "2025-12-15",
    "ticker_symbol": "AAPL",
    "security_name": "Apple Inc.",
    "transaction_type": "BUY",
    "currency": "USD",
    "quantity": 50.0,
    "unit_price": 180.50,
    "commission": 10.00,
    "settlement_amount": 9035.00,
    "exchange_rate": 149.50,
    "settlement_currency": "JPY",
    "created_at": "2025-12-15T10:30:00",
    "updated_at": "2025-12-15T10:30:00"
  }
}
```

**エラーレスポンス**:

- 404 Not Found:
```json
{
  "success": false,
  "error": "取引が見つかりません"
}
```

---

### 5.3 取引更新

指定したIDの取引情報を更新します。

**エンドポイント**: `PUT /api/transactions/<transaction_id>`

**URLパラメータ**:
- `transaction_id` (required): 取引ID（整数）

**リクエストボディ**: 更新するフィールドのみ指定
```json
{
  "transaction_date": "2025-12-20",
  "ticker_symbol": "AAPL",
  "security_name": "Apple Inc.",
  "transaction_type": "BUY",
  "quantity": 60.0,
  "unit_price": 175.00,
  "commission": 12.00,
  "settlement_amount": 10512.00,
  "currency": "USD"
}
```

**更新可能フィールド**:
- `transaction_date`: 取引日（YYYY-MM-DD形式）
- `ticker_symbol`: ティッカーシンボル（必須）
- `security_name`: 銘柄名
- `transaction_type`: 取引タイプ（"BUY" | "SELL" | "買付" | "売却"）
- `quantity`: 数量（正の数値）
- `unit_price`: 単価（正の数値）
- `commission`: 手数料（0以上）
- `settlement_amount`: 受渡金額（正の数値）
- `currency`: 通貨コード（"JPY" | "USD" | "KRW" | "日本円"）

**リクエスト例**:
```bash
curl -X PUT "http://localhost:5000/api/transactions/123" \
  -H "Content-Type: application/json" \
  -d '{
    "quantity": 60.0,
    "unit_price": 175.00,
    "commission": 12.00
  }'
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "message": "取引を更新しました",
  "transaction": {
    "id": 123,
    "transaction_date": "2025-12-15",
    "ticker_symbol": "AAPL",
    "security_name": "Apple Inc.",
    "transaction_type": "BUY",
    "currency": "USD",
    "quantity": 60.0,
    "unit_price": 175.00,
    "commission": 12.00,
    "settlement_amount": 10512.00,
    "exchange_rate": 149.50,
    "settlement_currency": "JPY",
    "created_at": "2025-12-15T10:30:00",
    "updated_at": "2026-01-10T15:00:00"
  },
  "affected_tickers": ["AAPL"]
}
```

**エラーレスポンス**:

- 400 Bad Request (更新データなし):
```json
{
  "success": false,
  "error": "更新データが指定されていません"
}
```

- 400 Bad Request (バリデーションエラー):
```json
{
  "success": false,
  "error": "数量は正の数値である必要があります",
  "field": "quantity",
  "value": -10
}
```

- 404 Not Found:
```json
{
  "success": false,
  "error": "取引が見つかりません (ID: 999)"
}
```

- 500 Internal Server Error:
```json
{
  "success": false,
  "error": "取引の更新に失敗しました: Database error"
}
```

**注意**:
- 取引更新後、関連する保有銘柄データが自動的に再計算されます
- `affected_tickers`に影響を受けた銘柄のリストが含まれます

---

### 5.4 取引削除

指定したIDの取引を削除します。

**エンドポイント**: `POST /api/transactions/delete`

**リクエストボディ**:
```json
{
  "transaction_ids": [123, 124, 125]
}
```

**パラメータ**:
- `transaction_ids` (required): 削除する取引IDの配列

**リクエスト例**:
```bash
curl -X POST "http://localhost:5000/api/transactions/delete" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_ids": [123, 124, 125]
  }'
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "message": "3件の取引を削除しました",
  "deleted_count": 3,
  "affected_tickers": ["AAPL", "MSFT"]
}
```

**エラーレスポンス**:

- 400 Bad Request:
```json
{
  "success": false,
  "error": "削除する取引が選択されていません"
}
```

- 500 Internal Server Error:
```json
{
  "success": false,
  "error": "削除に失敗しました: Database transaction failed"
}
```

**注意**:
- 削除後、影響を受けた銘柄の保有データが自動的に再計算されます
- すべての保有数量が0になった銘柄は保有銘柄リストに残ります（削除されません）

---

## 6. 実現損益API

### 6.1 実現損益一覧取得

全銘柄の実現損益データを銘柄別に集計して取得します。

**エンドポイント**: `GET /api/realized-pnl`

**リクエスト例**:
```bash
curl -X GET "http://localhost:5000/api/realized-pnl"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "count": 8,
  "realized_pnl": [
    {
      "ticker_symbol": "AAPL",
      "security_name": "Apple Inc.",
      "total_quantity": 150.0,
      "average_cost": 145.50,
      "sale_unit_price": 180.25,
      "total_cost": 21825.00,
      "sale_proceeds": 27037.50,
      "realized_pnl": 5212.50,
      "realized_pnl_pct": 23.88,
      "currency": "USD"
    }
  ]
}
```

**データ説明**:
- `total_quantity`: 売却した総数量
- `average_cost`: 売却時の平均取得単価（株式の通貨）
- `sale_unit_price`: 平均売却単価（株式の通貨）
- `total_cost`: 総取得コスト（JPY換算）
- `sale_proceeds`: 売却代金（JPY換算）
- `realized_pnl`: 確定損益（JPY）
- `realized_pnl_pct`: 確定損益率（%）
- `currency`: 株式の通貨（表示単価の通貨）

**通貨について**:
- 日本株（.T）: JPY
- 米国株: USD
- 韓国株（.KS）: KRW
- 総コスト、売却代金、損益はすべてJPY建て

---

## 7. ダッシュボードAPI

### 7.1 ダッシュボードサマリー取得

ダッシュボード用の投資サマリーデータを取得します。

**エンドポイント**: `GET /api/dashboard/summary`

**リクエスト例**:
```bash
curl -X GET "http://localhost:5000/api/dashboard/summary"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "summary": {
    "ticker_counts": {
      "total": 20,
      "active": 15,
      "realized": 5
    },
    "investment": {
      "total": 2500000.00,
      "holdings": 2000000.00,
      "realized": 500000.00
    },
    "evaluation": {
      "total": 2875000.00,
      "holdings": 2350000.00,
      "realized": 480000.00,
      "dividends": 45000.00
    },
    "total_pnl": {
      "amount": 375000.00,
      "percentage": 15.00
    },
    "currency": "JPY"
  }
}
```

**データ説明**:

**ticker_counts** (銘柄数):
- `total`: 投資実績のある総銘柄数（保有中 + 売却済み）
- `active`: 現在保有中の銘柄数
- `realized`: 売却済み（保有なし）の銘柄数

**investment** (投資額、JPY):
- `total`: 総投資額
- `holdings`: 現在保有分の投資額
- `realized`: 売却済み分の投資額

**evaluation** (評価額、JPY):
- `total`: 総評価額
- `holdings`: 保有銘柄の現在評価額
- `realized`: 売却済み代金
- `dividends`: 配当総額

**total_pnl** (総合損益):
- `amount`: 総合損益額（JPY）
- `percentage`: 総合損益率（%）

**計算式**:
```
総評価額 = 保有評価額 + 売却代金 + 配当総額
総合損益 = 総評価額 - 総投資額
総合損益率 = (総合損益 / 総投資額) × 100
```

---

### 7.2 ポートフォリオ構成取得

ポートフォリオの構成比データを取得します（円グラフ用）。

**エンドポイント**: `GET /api/dashboard/portfolio-composition`

**リクエスト例**:
```bash
curl -X GET "http://localhost:5000/api/dashboard/portfolio-composition"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "data": [
    {
      "ticker": "AAPL",
      "name": "Apple Inc.",
      "value": 450000.00,
      "percentage": 0
    },
    {
      "ticker": "MSFT",
      "name": "Microsoft Corporation",
      "value": 380000.00,
      "percentage": 0
    }
  ]
}
```

**データ説明**:
- `ticker`: ティッカーシンボル
- `name`: 銘柄名
- `value`: 評価額（JPY換算）
- `percentage`: 構成比率（%）- フロントエンド側で計算

**注意**:
- 評価額が0より大きい銘柄のみ返却されます
- 全銘柄の評価額がJPY換算されています

---

### 7.3 損益履歴取得（レガシー）

損益推移データを取得します。

**エンドポイント**: `GET /api/dashboard/pnl-history`

**クエリパラメータ**:
- `period` (optional): 期間（デフォルト: "30d"）
  - 値: "30d" | "1y" | "all"

**リクエスト例**:
```bash
# 直近30日
curl -X GET "http://localhost:5000/api/dashboard/pnl-history"

# 直近1年
curl -X GET "http://localhost:5000/api/dashboard/pnl-history?period=1y"

# 全期間
curl -X GET "http://localhost:5000/api/dashboard/pnl-history?period=all"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "data": [
    {
      "date": "2025-12-11",
      "pnl": 0.00
    },
    {
      "date": "2025-12-15",
      "pnl": 12500.00
    },
    {
      "date": "2026-01-10",
      "pnl": 23750.00
    }
  ]
}
```

**データ説明**:
- 日次の累積実現損益を返却
- `pnl`: 当日までの累積実現損益（JPY）

**注意**: このエンドポイントはレガシー版です。新しい実装は `/api/performance/history` を使用してください。

---

### 7.4 年度別統計取得

年度別の実現損益統計を取得します。

**エンドポイント**: `GET /api/dashboard/yearly-stats`

**リクエスト例**:
```bash
curl -X GET "http://localhost:5000/api/dashboard/yearly-stats"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "yearly_stats": [
    {
      "year": "2025",
      "total_cost": 800000.00,
      "total_proceeds": 920000.00,
      "realized_pnl": 120000.00,
      "pnl_pct": 15.00
    },
    {
      "year": "2024",
      "total_cost": 500000.00,
      "total_proceeds": 450000.00,
      "realized_pnl": -50000.00,
      "pnl_pct": -10.00
    }
  ],
  "total": {
    "year": "合計",
    "total_cost": 1300000.00,
    "total_proceeds": 1370000.00,
    "realized_pnl": 70000.00,
    "pnl_pct": 5.38
  }
}
```

**データ説明**:
- `year`: 年度（または"合計"）
- `total_cost`: 総取得コスト（JPY）
- `total_proceeds`: 総売却代金（JPY）
- `realized_pnl`: 確定損益（JPY）
- `pnl_pct`: 確定損益率（%）

**ソート**: 年度の降順（最新年が最初）

---

## 8. 損益推移API

### 8.1 損益推移履歴取得

投資損益の推移履歴をベンチマーク比較データとともに取得します。

**エンドポイント**: `GET /api/performance/history`

**クエリパラメータ**:
- `period` (optional): 期間（デフォルト: "1m"）
  - 値: "1m"（1ヶ月、日次） | "1y"（1年、月次）
- `benchmarks` (optional): ベンチマーク比較を含めるか（デフォルト: "true"）
  - 値: "true" | "false"
- `benchmark_keys` (optional): ベンチマーク指標（デフォルト: ["TOPIX", "SP500"]）
  - 値の例: TOPIX, SP500, NIKKEI225

**リクエスト例**:
```bash
# 1ヶ月の日次データ（デフォルト）
curl -X GET "http://localhost:5000/api/performance/history"

# 1年の月次データ
curl -X GET "http://localhost:5000/api/performance/history?period=1y"

# ベンチマーク比較なし
curl -X GET "http://localhost:5000/api/performance/history?benchmarks=false"

# カスタムベンチマーク
curl -X GET "http://localhost:5000/api/performance/history?benchmark_keys=TOPIX&benchmark_keys=NIKKEI225"
```

**成功レスポンス** (200 OK) - 1ヶ月（日次）:
```json
{
  "success": true,
  "period": "1m",
  "data": {
    "portfolio": [
      {
        "date": "2025-12-11",
        "total_value": 2000000.00,
        "total_cost": 1950000.00,
        "unrealized_pnl": 50000.00,
        "realized_pnl": 0.00,
        "dividends": 0.00,
        "total_pnl": 50000.00,
        "total_return_pct": 2.56
      },
      {
        "date": "2026-01-10",
        "total_value": 2350000.00,
        "total_cost": 2000000.00,
        "unrealized_pnl": 350000.00,
        "realized_pnl": 70000.00,
        "dividends": 45000.00,
        "total_pnl": 465000.00,
        "total_return_pct": 23.25
      }
    ],
    "benchmarks": {
      "TOPIX": [
        {
          "date": "2025-12-11",
          "value": 2650.50,
          "return_pct": 0.00
        },
        {
          "date": "2026-01-10",
          "value": 2720.30,
          "return_pct": 2.63
        }
      ],
      "SP500": [
        {
          "date": "2025-12-11",
          "value": 4850.20,
          "return_pct": 0.00
        },
        {
          "date": "2026-01-10",
          "value": 4920.50,
          "return_pct": 1.45
        }
      ]
    }
  }
}
```

**成功レスポンス** (200 OK) - 1年（月次）:
```json
{
  "success": true,
  "period": "1y",
  "data": {
    "portfolio": [
      {
        "date": "2025-01",
        "total_value": 1800000.00,
        "total_cost": 1850000.00,
        "unrealized_pnl": -50000.00,
        "realized_pnl": 0.00,
        "dividends": 0.00,
        "total_pnl": -50000.00,
        "total_return_pct": -2.70
      },
      {
        "date": "2026-01",
        "total_value": 2350000.00,
        "total_cost": 2000000.00,
        "unrealized_pnl": 350000.00,
        "realized_pnl": 70000.00,
        "dividends": 45000.00,
        "total_pnl": 465000.00,
        "total_return_pct": 23.25
      }
    ],
    "benchmarks": {
      "TOPIX": [
        {
          "date": "2025-01",
          "value": 2580.10,
          "return_pct": 0.00
        },
        {
          "date": "2026-01",
          "value": 2720.30,
          "return_pct": 5.43
        }
      ]
    }
  }
}
```

**ポートフォリオデータ説明**:
- `date`: 日付（日次: YYYY-MM-DD、月次: YYYY-MM）
- `total_value`: 総評価額（JPY）
- `total_cost`: 総投資額（JPY）
- `unrealized_pnl`: 未実現損益（JPY）
- `realized_pnl`: 実現損益（JPY）
- `dividends`: 配当額（JPY）
- `total_pnl`: 総損益（JPY）= 未実現 + 実現 + 配当
- `total_return_pct`: 総合リターン率（%）

**ベンチマークデータ説明**:
- `date`: 日付
- `value`: ベンチマーク指数値
- `return_pct`: 期間開始日からのリターン率（%）

**エラーレスポンス**:

- 500 Internal Server Error:
```json
{
  "success": false,
  "error": "Database query failed",
  "detail": "Traceback..."
}
```

---

### 8.2 日別詳細取得

指定日のポートフォリオ詳細（銘柄別内訳）を取得します。

**エンドポイント**: `GET /api/performance/detail`

**クエリパラメータ**:
- `date` (required): 日付（YYYY-MM-DD形式）

**リクエスト例**:
```bash
curl -X GET "http://localhost:5000/api/performance/detail?date=2026-01-10"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "date": "2026-01-10",
  "details": {
    "holdings": [
      {
        "ticker_symbol": "AAPL",
        "security_name": "Apple Inc.",
        "quantity": 100.0,
        "average_cost": 150.00,
        "current_price": 182.45,
        "current_value": 18245.00,
        "unrealized_pnl": 3245.00,
        "unrealized_pnl_pct": 21.63,
        "currency": "USD"
      }
    ],
    "summary": {
      "total_value": 2350000.00,
      "total_cost": 2000000.00,
      "total_unrealized_pnl": 350000.00,
      "total_realized_pnl": 70000.00,
      "total_dividends": 45000.00,
      "total_pnl": 465000.00,
      "return_pct": 23.25
    }
  }
}
```

**エラーレスポンス**:

- 400 Bad Request:
```json
{
  "success": false,
  "error": "Date parameter is required"
}
```

- 500 Internal Server Error:
```json
{
  "success": false,
  "error": "Failed to retrieve data",
  "traceback": "..."
}
```

---

## 9. 株式評価指標API

### 9.1 全保有銘柄の評価指標取得

全保有銘柄の株式評価指標を取得します。

**エンドポイント**: `GET /api/holdings/metrics`

**リクエスト例**:
```bash
curl -X GET "http://localhost:5000/api/holdings/metrics"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "count": 15,
  "metrics": [
    {
      "ticker": "AAPL",
      "security_name": "Apple Inc.",
      "pe_ratio": 28.5,
      "pb_ratio": 42.3,
      "dividend_yield": 0.52,
      "market_cap": 2850000000000,
      "eps": 6.42,
      "revenue_growth": 8.5,
      "profit_margin": 26.3,
      "roe": 148.2,
      "debt_to_equity": 1.73,
      "current_ratio": 0.93,
      "last_updated": "2026-01-10T10:00:00"
    }
  ]
}
```

**データ説明**:
- `pe_ratio`: PER（株価収益率）
- `pb_ratio`: PBR（株価純資産倍率）
- `dividend_yield`: 配当利回り（%）
- `market_cap`: 時価総額
- `eps`: 1株あたり利益
- `revenue_growth`: 売上成長率（%）
- `profit_margin`: 利益率（%）
- `roe`: 自己資本利益率（%）
- `debt_to_equity`: 負債資本比率
- `current_ratio`: 流動比率
- `last_updated`: 最終更新日時

**エラーレスポンス**:

- 503 Service Unavailable:
```json
{
  "success": false,
  "error": "評価指標の取得中にエラーが発生しました: API limit exceeded"
}
```

---

### 9.2 全保有銘柄の評価指標更新

全保有銘柄の株式評価指標を外部APIから取得・更新します。

**エンドポイント**: `POST /api/stock-metrics/update-all`

**リクエスト例**:
```bash
curl -X POST "http://localhost:5000/api/stock-metrics/update-all"
```

**成功レスポンス** (200 OK):
```json
{
  "success": true,
  "results": {
    "total": 15,
    "success": 14,
    "failed": 1,
    "details": [
      {
        "ticker": "AAPL",
        "success": true,
        "metrics": {
          "pe_ratio": 28.5,
          "pb_ratio": 42.3
        }
      },
      {
        "ticker": "INVALID",
        "success": false,
        "error": "評価指標を取得できませんでした"
      }
    ]
  }
}
```

**エラーレスポンス**:

- 503 Service Unavailable:
```json
{
  "success": false,
  "error": "評価指標の一括更新中にエラーが発生しました: External API error"
}
```

---

## 10. エラーハンドリング

### エラーレスポンス形式

全てのエラーレスポンスは以下の基本形式に従います。

```json
{
  "success": false,
  "error": "エラーメッセージ"
}
```

追加情報がある場合は、追加フィールドが含まれます。

```json
{
  "success": false,
  "error": "必須フィールドが不足しています: amount, from",
  "missing_fields": ["amount", "from"]
}
```

---

### HTTPステータスコード

| コード | 意味 | 説明 |
|--------|------|------|
| 200 | OK | リクエスト成功 |
| 400 | Bad Request | バリデーションエラー、不正なリクエスト |
| 404 | Not Found | リソースが見つからない |
| 500 | Internal Server Error | サーバー内部エラー、データベースエラー |
| 503 | Service Unavailable | 外部API呼び出しエラー |

---

### エラータイプ

#### ValidationError (400)

入力データのバリデーションエラーです。

**発生条件**:
- 必須フィールドの不足
- データ型の不一致
- 数値範囲外
- 日付フォーマット不正
- サポートされていない値

**例**:
```json
{
  "success": false,
  "error": "金額は正の数値である必要があります",
  "field": "amount",
  "value": -100
}
```

---

#### NotFoundError (404)

リソースが見つからないエラーです。

**発生条件**:
- 指定されたティッカーの保有銘柄が存在しない
- 指定された取引IDが存在しない
- 株価データが取得できない

**例**:
```json
{
  "success": false,
  "error": "保有銘柄が見つかりません: INVALID"
}
```

---

#### DatabaseError (500)

データベース操作中のエラーです。

**発生条件**:
- データベース接続エラー
- トランザクション失敗
- クエリ実行エラー

**例**:
```json
{
  "success": false,
  "error": "保有銘柄の取得に失敗しました: Database connection failed"
}
```

---

#### ExternalAPIError (503)

外部API呼び出し時のエラーです。

**発生条件**:
- 株価APIの呼び出し失敗
- 為替レートAPIの呼び出し失敗
- APIレート制限超過
- ネットワークエラー

**例**:
```json
{
  "success": false,
  "error": "株価の取得中にエラーが発生しました: Connection timeout"
}
```

---

### バリデーションルール

#### 必須フィールド検証

```python
# 必須フィールド: amount, from
validate_required_fields(data, ['amount', 'from'])
```

エラー例:
```json
{
  "success": false,
  "error": "必須フィールドが不足しています: amount, from",
  "missing_fields": ["amount", "from"]
}
```

---

#### 正の数値検証

```python
# 正の数値チェック
validate_positive_number(amount, '金額')
```

エラー例:
```json
{
  "success": false,
  "error": "金額は正の数値である必要があります",
  "field": "amount",
  "value": -100
}
```

---

#### 日付フォーマット検証

```python
# YYYY-MM-DD形式チェック
validate_date_format(date_string, '取引日')
```

エラー例:
```json
{
  "success": false,
  "error": "取引日の日付フォーマットが正しくありません (YYYY-MM-DD形式で指定してください)",
  "field": "transaction_date",
  "value": "2025/12/15"
}
```

---

#### 通貨コード検証

```python
# サポート通貨: JPY, USD, KRW, 日本円
validate_currency(currency)
```

エラー例:
```json
{
  "success": false,
  "error": "サポートされていない通貨です: EUR",
  "currency": "EUR",
  "valid_currencies": ["JPY", "USD", "KRW", "日本円"]
}
```

---

#### 取引タイプ検証

```python
# サポートタイプ: BUY, SELL, 買付, 売却
validate_transaction_type(transaction_type)
```

エラー例:
```json
{
  "success": false,
  "error": "サポートされていない取引タイプです: SHORT",
  "transaction_type": "SHORT",
  "valid_types": ["BUY", "SELL", "買付", "売却"]
}
```

---

## 付録

### A. データモデル

#### Holding（保有銘柄）

```python
{
  "id": int,
  "ticker_symbol": str,          # ティッカーシンボル（ユニーク）
  "security_name": str,          # 銘柄名
  "total_quantity": float,       # 現在保有数量
  "average_cost": float,         # 平均取得単価（移動平均法）
  "currency": str,               # 通貨（JPY/USD/KRW）
  "total_cost": float,           # 総取得コスト
  "current_price": float,        # 最新株価
  "previous_close": float,       # 前日終値
  "day_change_pct": float,       # 対前日変動率（%）
  "current_value": float,        # 現在評価額
  "unrealized_pnl": float,       # 未実現損益
  "unrealized_pnl_pct": float,   # 未実現損益率（%）
  "last_updated": datetime,      # 最終更新日時
  "created_at": datetime         # 作成日時
}
```

---

#### Transaction（取引履歴）

```python
{
  "id": int,
  "transaction_date": date,      # 取引日
  "ticker_symbol": str,          # ティッカーシンボル
  "security_name": str,          # 銘柄名
  "transaction_type": str,       # BUY/SELL
  "currency": str,               # 通貨
  "quantity": float,             # 数量
  "unit_price": float,           # 単価
  "commission": float,           # 手数料
  "settlement_amount": float,    # 受渡金額
  "exchange_rate": float,        # 為替レート
  "settlement_currency": str,    # 受渡通貨
  "created_at": datetime,        # 作成日時
  "updated_at": datetime         # 更新日時
}
```

---

#### Dividend（配当）

```python
{
  "id": int,
  "ticker_symbol": str,          # ティッカーシンボル
  "ex_dividend_date": date,      # 権利落ち日
  "payment_date": date,          # 支払日
  "dividend_amount": float,      # 1株あたり配当額
  "currency": str,               # 通貨
  "total_dividend": float,       # 総配当額
  "quantity_held": float,        # 配当時の保有数量
  "source": str,                 # データソース
  "created_at": datetime         # 作成日時
}
```

---

#### RealizedPnl（実現損益）

```python
{
  "id": int,
  "ticker_symbol": str,          # ティッカーシンボル
  "sell_date": date,             # 売却日
  "quantity": float,             # 数量
  "average_cost": float,         # 売却時の平均取得単価
  "sell_price": float,           # 売却単価
  "realized_pnl": float,         # 確定損益
  "realized_pnl_pct": float,     # 確定損益率（%）
  "commission": float,           # 手数料
  "currency": str,               # 通貨
  "created_at": datetime         # 作成日時
}
```

---

### B. 通貨と為替レート

#### サポート通貨

| コード | 名称 | 用途 |
|--------|------|------|
| JPY | 日本円 | 日本株、受渡金額 |
| USD | 米ドル | 米国株 |
| KRW | 韓国ウォン | 韓国株 |
| 日本円 | 日本円（別名） | 日本株（レガシー） |

#### ティッカーサフィックスと通貨

| サフィックス | 市場 | 通貨 | 例 |
|-------------|------|------|-----|
| .T | 東京証券取引所 | JPY | 9984.T（ソフトバンク） |
| .KS | 韓国証券取引所 | KRW | 005930.KS（サムスン） |
| なし | 米国市場 | USD | AAPL（アップル） |

#### 為替レート取得

- デフォルト変換先: JPY
- キャッシュ有効期限: 15分
- データソース: 外部為替レートAPI

---

### C. 計算ロジック

#### 平均取得単価（移動平均法）

```
新しい平均単価 = (既存保有額 + 新規購入額) / (既存数量 + 新規数量)

例:
既存: 100株 @ 150円 = 15,000円
追加購入: 50株 @ 180円 = 9,000円
新平均単価 = (15,000 + 9,000) / (100 + 50) = 160円
```

#### 未実現損益

```
未実現損益 = 現在評価額 - 総取得コスト
未実現損益率 = (未実現損益 / 総取得コスト) × 100
```

#### 実現損益

```
実現損益 = 売却代金 - (平均取得単価 × 売却数量)
実現損益率 = (実現損益 / (平均取得単価 × 売却数量)) × 100
```

#### 配当利回り

```
配当利回り = (総配当額 / 総投資額) × 100
```

#### 総合損益

```
総評価額 = 保有評価額 + 売却代金 + 配当総額
総合損益 = 総評価額 - 総投資額
総合損益率 = (総合損益 / 総投資額) × 100
```

---

### D. 使用例集

#### シナリオ1: 新規銘柄の株価チェック

```bash
# 1. 株価取得
curl -X GET "http://localhost:5000/api/stock-price/AAPL"

# 2. 評価指標確認（保有銘柄にある場合）
curl -X GET "http://localhost:5000/api/holdings/metrics"
```

#### シナリオ2: ポートフォリオ全体の更新

```bash
# 1. 全保有銘柄の株価更新
curl -X POST "http://localhost:5000/api/stock-price/update-all"

# 2. 配当データ更新
curl -X POST "http://localhost:5000/api/dividends/update-all"

# 3. 評価指標更新
curl -X POST "http://localhost:5000/api/stock-metrics/update-all"

# 4. ダッシュボード確認
curl -X GET "http://localhost:5000/api/dashboard/summary"
```

#### シナリオ3: 取引の追加と確認

```bash
# 1. 取引履歴確認（最新10件）
curl -X GET "http://localhost:5000/api/transactions?limit=10"

# 2. 特定銘柄の保有状況確認
curl -X GET "http://localhost:5000/api/holdings/AAPL"

# 3. 配当履歴確認
curl -X GET "http://localhost:5000/api/dividends/AAPL"
```

#### シナリオ4: 損益分析

```bash
# 1. ダッシュボードサマリー
curl -X GET "http://localhost:5000/api/dashboard/summary"

# 2. 実現損益確認
curl -X GET "http://localhost:5000/api/realized-pnl"

# 3. 配当サマリー
curl -X GET "http://localhost:5000/api/dividends/summary"

# 4. 損益推移（1年）
curl -X GET "http://localhost:5000/api/performance/history?period=1y"

# 5. 年度別統計
curl -X GET "http://localhost:5000/api/dashboard/yearly-stats"
```

#### シナリオ5: 通貨変換

```bash
# 1. 為替レート確認
curl -X GET "http://localhost:5000/api/exchange-rate/USD"

# 2. 金額変換
curl -X POST "http://localhost:5000/api/exchange-rate/convert" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000.00,
    "from": "USD",
    "to": "JPY"
  }'
```

---

## 変更履歴

### v1.0 (2026-01-10)
- 初版リリース
- 全APIエンドポイントの仕様策定
- エラーハンドリング標準化
- バリデーションルール定義

---

**ドキュメント作成日**: 2026-01-10
**API バージョン**: v1.0
**アプリケーション**: Stock P&L Manager
