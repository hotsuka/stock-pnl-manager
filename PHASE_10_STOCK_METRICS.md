# Phase 10: 株式評価指標表示機能 - 実装完了レポート

## 実装日
2026-01-09

## 概要

保有銘柄一覧ページ (`/holdings`) に、Yahoo Financeから取得した12種類の株式評価指標をタブ切替UIで表示する機能を実装しました。

## 実装した機能

### 1. 対象評価指標（12種類）

| 指標名 | 説明 | yfinance infoキー |
|--------|------|-------------------|
| 時価総額 (Market Cap) | 企業の時価総額 | `marketCap` |
| Beta (5Y Monthly) | 市場との連動性 | `beta` |
| PER (Price/Earnings Ratio) | 株価収益率 | `trailingPE` |
| EPS (Earnings Per Share) | 1株当たり利益 | `trailingEps` |
| 52週レンジ | 過去52週の最高値・最安値 | `fiftyTwoWeekLow`, `fiftyTwoWeekHigh` |
| YTDリターン | 年初来リターン | *計算で算出 |
| 1年リターン | 過去1年間のリターン | *計算で算出 |
| PBR (Price/Book Ratio) | 株価純資産倍率 | `priceToBook` |
| EV/売上 | 企業価値/売上高 | `enterpriseToRevenue` |
| EV/EBITDA | 企業価値/EBITDA | `enterpriseToEbitda` |
| 売上 (Revenue TTM) | 過去12ヶ月売上高 | `totalRevenue` |
| 利益率 (Profit Margin) | 当期純利益率 | `profitMargins` |

*YTD・1年リターンは `stock.history()` から取得した過去データから計算

## アーキテクチャ

```
データフロー:
yfinance API
  ↓
StockMetricsFetcher (サービス層)
  ↓
StockMetrics (モデル) → データベース (stock_metrics テーブル)
  ↓
/api/holdings/metrics (APIエンドポイント)
  ↓
holdings.html (タブUI + JavaScript)
```

## 実装ファイル

### 新規作成ファイル

1. **`app/models/stock_metrics.py`** - 評価指標モデル
   - 14フィールド（12種類の指標 + 通貨 + 更新日時）
   - `to_dict()` メソッドでNull値を適切に処理
   - ticker_symbolにユニーク制約

2. **`app/services/stock_metrics_fetcher.py`** - 評価指標取得サービス
   - `get_stock_metrics()` - 単一銘柄の評価指標取得（キャッシュ対応）
   - `get_multiple_metrics()` - 複数銘柄の一括取得
   - `update_all_holdings_metrics()` - 全保有銘柄の評価指標更新
   - `_calculate_returns()` - YTD・1年リターンの計算
   - `_save_metrics_to_db()` - データベースへのUPSERT保存

3. **`tests/test_stock_metrics.py`** - ユニットテスト
   - 5つのテストケース（全てpass）
   - 作成、to_dict、Null値、ユニーク制約、日本株のテスト

4. **`migrations/versions/33622936f4f0_add_stock_metrics_table_for_financial_.py`**
   - stock_metricsテーブル作成マイグレーション

### 変更ファイル

1. **`app/models/__init__.py`**
   - StockMetricsのインポートとエクスポート追加

2. **`app/services/__init__.py`**
   - StockMetricsFetcherのインポートとエクスポート追加

3. **`app/routes/api.py`**
   - 2つの新規エンドポイント追加:
     - `GET /api/holdings/metrics` - 全保有銘柄の評価指標取得
     - `POST /api/stock-metrics/update-all` - 評価指標一括更新
   - StockMetricsFetcherのインポート追加

4. **`app/services/stock_price_fetcher.py`**
   - `update_all_holdings_prices()` メソッドに評価指標更新を統合
   - Step 6として評価指標の自動更新を追加
   - エラーハンドリング付き（失敗してもスキップ）

5. **`app/templates/holdings.html`**
   - タブUI追加（基本情報タブ・評価指標タブ）
   - 評価指標テーブル追加（14列）
   - JavaScriptコード追加:
     - `metricsData` 変数
     - `loadMetricsData()` - 評価指標データ取得
     - `renderMetricsTable()` - テーブル描画
     - フォーマット関数群（時価総額、売上、リターン等）
   - タブ切替時の遅延ロード実装

## データベーススキーマ

### stock_metricsテーブル

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER | 主キー |
| ticker_symbol | VARCHAR(20) | ティッカーシンボル（UNIQUE, INDEX） |
| market_cap | NUMERIC(20, 2) | 時価総額 |
| beta | NUMERIC(10, 4) | Beta |
| pe_ratio | NUMERIC(10, 2) | PER |
| eps | NUMERIC(15, 4) | EPS |
| pb_ratio | NUMERIC(10, 2) | PBR |
| ev_to_revenue | NUMERIC(10, 2) | EV/売上 |
| ev_to_ebitda | NUMERIC(10, 2) | EV/EBITDA |
| revenue | NUMERIC(20, 2) | 売上 |
| profit_margin | NUMERIC(10, 4) | 利益率 |
| fifty_two_week_low | NUMERIC(15, 4) | 52週安値 |
| fifty_two_week_high | NUMERIC(15, 4) | 52週高値 |
| ytd_return | NUMERIC(10, 4) | YTDリターン（小数） |
| one_year_return | NUMERIC(10, 4) | 1年リターン（小数） |
| currency | VARCHAR(3) | 通貨コード |
| last_updated | DATETIME | 最終更新日時 |
| created_at | DATETIME | 作成日時 |

## 主要機能

### 1. キャッシュ機能

**日次キャッシュ:**
- `last_updated` が当日の場合、APIを呼び出さずDBから取得
- 株価更新時に自動的に評価指標も更新

**メモリキャッシュ:**
- JavaScriptで `metricsData` 配列をキャッシュ
- タブを再度開いても再度APIを呼ばない

### 2. 遅延ロード

- 初回ページ表示時は基本情報タブのみ表示
- 評価指標タブをクリックした時点で初めてデータ取得
- パフォーマンス向上とAPI呼び出し削減

### 3. リターン計算

**YTDリターン:**
```python
ytd_return = (現在価格 - 年初価格) / 年初価格
```

**1年リターン:**
```python
one_year_return = (現在価格 - 365日前価格) / 365日前価格
```

### 4. エラーハンドリング

- yfinance APIエラー → ログ記録 + Noneを返す
- 指標が取得できない → 部分的なデータでも保存
- history()失敗 → リターン指標のみNone
- フロントエンド: Null → `-` 表示

## API仕様

### GET /api/holdings/metrics

**説明:** 全保有銘柄の評価指標を取得

**レスポンス:**
```json
{
  "success": true,
  "count": 3,
  "metrics": [
    {
      "ticker_symbol": "AAPL",
      "market_cap": 3000000000000,
      "beta": 1.2,
      "pe_ratio": 28.5,
      "eps": 6.12,
      "fifty_two_week_low": 124.17,
      "fifty_two_week_high": 199.62,
      "ytd_return": 0.125,
      "one_year_return": 0.35,
      "pb_ratio": 45.3,
      "ev_to_revenue": 7.5,
      "ev_to_ebitda": 22.1,
      "revenue": 394000000000,
      "profit_margin": 0.265,
      "currency": "USD",
      "last_updated": "2026-01-09T12:00:00"
    }
  ]
}
```

### POST /api/stock-metrics/update-all

**説明:** 全保有銘柄の評価指標を強制更新

**レスポンス:**
```json
{
  "success": true,
  "results": {
    "success": 3,
    "failed": 0,
    "details": [
      {"ticker": "AAPL", "status": "success"},
      {"ticker": "GOOGL", "status": "success"},
      {"ticker": "7203.T", "status": "success"}
    ]
  }
}
```

## UI仕様

### タブUI

**基本情報タブ:**
- 既存の保有銘柄一覧テーブル
- 保有数量、取得単価、現在株価、損益等を表示

**評価指標タブ:**
- 12種類の財務・株価指標を表示
- リターン指標は正負で色分け（緑/赤）
- 通貨に応じた表示フォーマット:
  - 時価総額: JPY → 兆円/億円、USD → B/M
  - 売上: 同上
  - リターン: パーセンテージ（+12.50%）

### データ更新フロー

1. ユーザーが「データを更新」ボタンをクリック
2. `/api/stock-price/update-all` を呼び出し
3. 株価更新 → 評価指標も自動更新（Step 6）
4. フロントエンドでキャッシュクリア（`metricsData = []`）
5. 次回評価指標タブを開いた際に最新データを再取得

## パフォーマンス最適化

### キャッシュ戦略
- **日次キャッシュ**: 同日内は再取得しない
- **タブ遅延ロード**: 必要な時だけデータ取得
- **メモリキャッシュ**: 同一セッション内で再利用

### バッチ処理
- `time.sleep(0.1)` でレート制限対策
- yfinance APIの不安定性を考慮して個別取得

## テスト結果

```
tests/test_stock_metrics.py::TestStockMetricsModel::test_create_stock_metrics PASSED
tests/test_stock_metrics.py::TestStockMetricsModel::test_stock_metrics_to_dict PASSED
tests/test_stock_metrics.py::TestStockMetricsModel::test_stock_metrics_null_values PASSED
tests/test_stock_metrics.py::TestStockMetricsModel::test_stock_metrics_unique_ticker PASSED
tests/test_stock_metrics.py::TestStockMetricsModel::test_stock_metrics_japanese_stock PASSED

5 passed, 12 warnings
```

## 使用方法

### ユーザー視点

1. **基本情報の確認**
   - `/holdings` にアクセス
   - 「基本情報」タブで保有銘柄一覧を確認

2. **評価指標の確認**
   - 「評価指標」タブをクリック
   - 初回クリック時に自動的にデータ取得
   - 12種類の財務指標を一覧表示

3. **データ更新**
   - 「データを更新」ボタンをクリック
   - 株価と評価指標が両方更新される

### 開発者視点

**新規銘柄の評価指標取得:**
```python
from app.services import StockMetricsFetcher

# 単一銘柄
metrics = StockMetricsFetcher.get_stock_metrics('AAPL', use_cache=True)

# 複数銘柄
metrics_dict = StockMetricsFetcher.get_multiple_metrics(['AAPL', 'GOOGL'], use_cache=True)

# 全保有銘柄更新
results = StockMetricsFetcher.update_all_holdings_metrics()
```

## 実現したこと

✅ **12種類の評価指標表示**
✅ **タブUIによる切替表示**
✅ **日次キャッシュ機能**
✅ **株価更新との連携**
✅ **遅延ロード**
✅ **適切なエラーハンドリング**
✅ **通貨別フォーマット**
✅ **リターン指標の計算**
✅ **ユニットテスト（5件全てpass）**

## トレードオフ

⚠️ **データの鮮度**
- 最大1日古いデータを表示する可能性
- 解決策: 日次更新（株価更新と同時）、手動更新ボタン

⚠️ **yfinance APIの不安定性**
- 一部の指標が取得できない場合がある
- 解決策: 部分的なデータでも保存、Null値を `-` で表示

⚠️ **API呼び出しの増加**
- 保有銘柄数に応じてAPI呼び出しが増える
- 解決策: 日次キャッシュ、レート制限対策（sleep 0.1秒）

## 今後の拡張案

1. **ソート機能**
   - 評価指標テーブルに列ソート機能を追加
   - クリックで昇順/降順切替

2. **フィルタリング機能**
   - PER、PBR等の範囲でフィルタ
   - 特定の条件に合致する銘柄を抽出

3. **チャート表示**
   - 時系列での指標変化をグラフ表示
   - PER推移、売上推移等

4. **アラート機能**
   - 特定の閾値を超えた場合に通知
   - 例: PER > 50、Beta > 2.0

5. **比較機能**
   - 複数銘柄の指標を横並びで比較
   - ベンチマーク（S&P500等）との比較

## まとめ

Phase 10では、保有銘柄一覧ページにYahoo Financeから取得した12種類の株式評価指標を表示する機能を実装しました。タブUIによる切替表示、日次キャッシュ、遅延ロード等の最適化により、パフォーマンスを維持しながら豊富な投資情報を提供できるようになりました。

全てのユニットテストが成功し、エラーハンドリングも適切に実装されており、安定した機能として運用できます。
