# Phase 11: ベンチマーク比較機能 - 実装完了レポート

## 実装日
2026-01-10

## 概要

損益推移ページ (`/performance`) に、TOPIXとS&P 500のベンチマーク比較機能を実装しました。ポートフォリオのパフォーマンスを市場指数と比較することで、投資成果を客観的に評価できるようになりました。

また、月次損益推移の表示機能を改善し、モーダル表示の精度向上とパフォーマンス最適化を実現しました。

## 実装した機能

### 1. ベンチマーク比較グラフ

#### 1.1 上段グラフへのベンチマーク追加
- **表示内容**: ベンチマーク指数と同じ変動率での仮想損益をドット(scatter)で表示
- **計算式**: `前日の保有銘柄評価額 × ベンチマークの対前日変動率`
- **ベンチマーク**:
  - 日経平均225 (TOPIX → Nikkei 225に変更)
  - S&P 500
- **UI機能**: チェックボックスで表示/非表示を切替

#### 1.2 データソース
- Yahoo Finance APIから指数データを取得
  - 日経平均225: `^N225`
  - S&P 500: `^GSPC`
- データベースにキャッシュして再利用

### 2. 月次損益推移の改善

#### 2.1 モーダル表示の改善
- **動的ヘッダー**: 月次データと日次データで列名を自動切替
  - 月次: 「前月末株価」「当月末株価」
  - 日次: 「前日株価」「当日株価」

#### 2.2 当月取得銘柄の損益計算
- 当月中に取得した銘柄は、前月末株価ではなく**取得価格（加重平均）**を基準に損益計算
- より正確な損益把握が可能に

#### 2.3 現在月(2026-01)の処理修正
- 現在月のデータ取得時に未来の日付を参照しないよう修正
- NaN値のチェック強化により、JSON解析エラーを防止

#### 2.4 データ整合性の確保
- モーダルの合計値と一覧表の値が一致するように計算ロジックを統一

### 3. パフォーマンス最適化

#### 3.1 月次データ取得の高速化
- **改善前**: `get_daily_detail()` を13回呼び出し → 約130秒
- **改善後**: 価格データを一括取得して全月を一度に計算 → 約43秒
- **成果**: **67%の処理時間削減**

#### 3.2 最適化手法
- yfinance APIへの呼び出しを最小化（バッチ処理）
- 取引履歴、実現損益、配当データをメモリ上で事前マッピング
- 日付ごとのループ処理を効率化

### 4. 削除した機能

#### 4.1 累積リターン比較グラフ
- ユーザーフィードバックにより削除
- 理由: 「わかりにくい」「正確な数値を出すのが難しい」
- 関連コードとHTML要素を完全削除

## アーキテクチャ

```
データフロー:

[ユーザー操作]
  ↓
/performance ページ
  ↓ (期間選択: 1m/1y, ベンチマーク選択)
  ↓
GET /api/performance/history?period=1m&benchmarks=true
  ↓
PerformanceService.get_performance_history_with_benchmark()
  ├─ get_performance_history() (既存)
  │   └→ ポートフォリオの日次損益・評価額
  └─ BenchmarkFetcher.get_multiple_benchmarks()
      ├─ yfinance API (^N225, ^GSPC)
      ├─ ExchangeRateFetcher (USD→JPY換算)
      └─ BenchmarkPrice DB (キャッシュ)
  ↓
JSON レスポンス
{
  portfolio: [{date, holding_pnl, realized_pnl, dividend_income, portfolio_value}],
  benchmarks: {
    TOPIX: [{date, close, daily_return, virtual_pnl, cumulative_return}],
    SP500: [{date, close, daily_return, virtual_pnl, cumulative_return}]
  }
}
  ↓
Plotly.js でグラフ描画
  ├─ 棒グラフ (保有損益、実現損益、配当)
  └─ ドット (ベンチマーク仮想損益)
```

## 実装ファイル

### 新規作成ファイル

1. **`app/models/benchmark_price.py`** - ベンチマーク価格キャッシュモデル
   ```python
   class BenchmarkPrice(db.Model):
       benchmark_key = 'TOPIX' | 'SP500'
       price_date = Date
       close_price = Decimal
       previous_close = Decimal
       currency = 'JPY' | 'USD'
   ```

2. **`app/services/benchmark_fetcher.py`** - ベンチマークデータ取得サービス
   - `get_benchmark_price()`: 現在価格取得（キャッシュ対応）
   - `get_historical_benchmark()`: 履歴データ取得
   - `get_multiple_benchmarks()`: 複数ベンチマークの一括取得

3. **`migrations/versions/df3c33605d6e_add_benchmark_prices_table.py`** - DBマイグレーション

### 修正ファイル

1. **`app/models/__init__.py`**
   - BenchmarkPriceモデルのインポート追加

2. **`app/routes/api.py`**
   - `/api/performance/history` エンドポイント拡張
   - `benchmarks=true` パラメータ対応
   - レスポンス構造変更（portfolio + benchmarks）

3. **`app/services/performance_service.py`**
   - `get_performance_history_with_benchmark()` メソッド追加
   - `get_monthly_performance_history()` 完全リライト（パフォーマンス最適化）
   - `get_daily_detail()` 修正
     - 月次/日次の判定ロジック追加
     - 現在月の処理修正
     - 当月取得銘柄の取得価格計算
     - NaN値チェック強化

4. **`app/templates/performance.html`**
   - UIコントロール追加（ベンチマークチェックボックス）
   - `renderChart()` 修正（ベンチマークドット追加）
   - `showDetail()` 修正（月次/日次判定）
   - `renderHoldingDetails()` 修正（動的ヘッダー）
   - 累積リターングラフのコード削除
   - エラーハンドリング強化

## データベーススキーマ

### 新規テーブル: `benchmark_prices`

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | Integer | 主キー |
| benchmark_key | String(10) | ベンチマーク識別子 ('TOPIX', 'SP500') |
| price_date | Date | 価格日付 |
| close_price | Numeric(15,4) | 終値 |
| previous_close | Numeric(15,4) | 前日終値 |
| currency | String(3) | 通貨 ('JPY', 'USD') |
| created_at | DateTime | 作成日時 |

**制約**: `UNIQUE(benchmark_key, price_date)`

## 主要な実装ロジック

### 1. ベンチマーク仮想損益の計算

```python
# 各日のベンチマーク変動率を計算
daily_return = (close - previous_close) / previous_close

# 前日のポートフォリオ評価額 × ベンチマーク変動率
virtual_pnl = previous_portfolio_value × daily_return

# 為替換算 (S&P 500の場合)
virtual_pnl_jpy = virtual_pnl × usd_jpy_rate
```

### 2. 当月取得銘柄の損益計算

```python
# 当月中のBUY取引を確認
buy_in_month = [tx for tx in transactions
               if tx.ticker_symbol == ticker
               and tx.transaction_type == 'BUY'
               and month_start <= tx.transaction_date <= month_end]

if buy_in_month:
    # 加重平均取得価格を計算
    total_cost = sum(tx.unit_price * tx.quantity for tx in buy_in_month)
    total_qty = sum(tx.quantity for tx in buy_in_month)
    prev_price = total_cost / total_qty
else:
    # 前月末株価を使用
    prev_price = get_month_end_price(ticker, previous_month)
```

### 3. 月次/日次の判定

```javascript
// 日付フォーマットで判定
const isMonthly = date.length === 7 && date.split('-').length === 2;
// YYYY-MM → 月次
// YYYY-MM-DD → 日次
```

## テスト

### 動作確認項目

- [x] ベンチマークチェックボックスのON/OFF動作
- [x] 日経平均225のドット表示（赤色）
- [x] S&P 500のドット表示（青色）
- [x] 月次データのモーダル表示（前月末株価/当月末株価）
- [x] 日次データのモーダル表示（前日株価/当日株価）
- [x] 当月取得銘柄の損益計算（取得価格基準）
- [x] 現在月(2026-01)のモーダル表示
- [x] モーダル合計値と一覧表の値の一致
- [x] 期間切替（過去1か月/過去1年）の動作
- [x] データキャッシュの動作
- [x] ベンチマーク価格のDBキャッシュ

### パフォーマンステスト

| 処理 | 改善前 | 改善後 | 改善率 |
|------|--------|--------|--------|
| 月次データ取得 | 約130秒 | 約43秒 | **-67%** |
| 日次データ取得 | 約15秒 | 約15秒 | - |

## エラー修正履歴

### Issue 1: 月次モーダルのヘッダーが日次と同じ
- **原因**: ヘッダーが固定値
- **修正**: `isMonthly` フラグで動的に変更

### Issue 2: モーダルと一覧表の値が不一致
- **原因**: `get_monthly_performance_history()` と `get_daily_detail()` の計算ロジックが異なる
- **修正**: 計算ロジックを統一

### Issue 3: 2026-01のモーダルでJSON解析エラー
- **原因**:
  1. 未来の日付(2026-01-31)の価格を取得しようとした
  2. NaN値がJSONに含まれた
- **修正**:
  1. 現在月は今日の日付を使用
  2. `pd.isna()` チェックを強化

### Issue 4: 月次データの読み込みが遅い
- **原因**: `get_daily_detail()` を13回呼び出し
- **修正**: 価格データを一括取得してバッチ処理

## 保留機能

以下の機能は要件から外れたため、実装を保留します。

### 1. セクター別分析
- セクター別のパフォーマンス比較
- セクター別の資産配分

### 2. リスク指標計算
- シャープレシオ
- ボラティリティ
- 最大ドローダウン
- VaR (Value at Risk)

これらの機能が必要になった場合は、Phase 12以降で実装を検討します。

## 完了条件

- [x] 上段グラフに日経平均225/S&P 500のドットが表示される
- [x] チェックボックスで表示/非表示を切替できる
- [x] 月次モーダルのヘッダーが「前月末株価」「当月末株価」になる
- [x] 当月取得銘柄が取得価格基準で計算される
- [x] 現在月(2026-01)のモーダルが正常に開く
- [x] モーダル合計値と一覧表の値が一致する
- [x] 期間切替(1m/1y)に両グラフが連動する
- [x] ベンチマーク価格がDBにキャッシュされる
- [x] 月次データの取得時間が大幅に改善される
- [x] 累積リターングラフが削除される
- [x] エラー時にユーザーフレンドリーなメッセージが表示される

## 次のステップ

Phase 11の実装は完了しました。今後の拡張として以下が考えられます:

1. **ベンチマークの追加**
   - ナスダック総合指数
   - 各国の主要指数

2. **パフォーマンス分析**
   - アルファ（超過収益）の計算
   - ベータ（市場感応度）の計算

3. **レポート機能**
   - 月次/年次パフォーマンスレポートのPDF出力
   - ベンチマーク比較レポート

## 関連ドキュメント

- [Phase 10: 株式評価指標表示機能](PHASE_10_STOCK_METRICS.md)
- [パフォーマンス最適化ガイド](PERFORMANCE_OPTIMIZATION.md)
- [Yahoo Finance API 利用ガイド](YAHOO_FINANCE_API.md)

## 変更履歴

| 日付 | 変更内容 |
|------|----------|
| 2026-01-10 | Phase 11完了、ドキュメント作成 |
