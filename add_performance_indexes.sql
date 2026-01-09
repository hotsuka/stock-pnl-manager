-- パフォーマンス最適化のためのインデックス追加
-- 実行日: 2026-01-09

-- 1. 取引履歴テーブル（transactions）のインデックス
-- 銘柄と日付で頻繁に検索されるため、複合インデックスを追加
CREATE INDEX IF NOT EXISTS idx_transactions_ticker_date
ON transactions(ticker_symbol, transaction_date DESC);

-- 取引タイプでのフィルタリング用
CREATE INDEX IF NOT EXISTS idx_transactions_type
ON transactions(transaction_type);

-- 2. 株価履歴テーブル（stock_prices）のインデックス
-- 銘柄と日付で頻繁に検索されるため、複合インデックスを追加
CREATE INDEX IF NOT EXISTS idx_stock_prices_ticker_date
ON stock_prices(ticker_symbol, price_date DESC);

-- 3. 実現損益テーブル（realized_pnl）のインデックス
-- 売却日での検索・ソート用
CREATE INDEX IF NOT EXISTS idx_realized_pnl_sell_date
ON realized_pnl(sell_date DESC);

-- 銘柄での検索用（既存のINDEXがあれば不要）
CREATE INDEX IF NOT EXISTS idx_realized_pnl_ticker
ON realized_pnl(ticker_symbol);

-- 4. 配当履歴テーブル（dividends）のインデックス
-- 権利落ち日での検索用
CREATE INDEX IF NOT EXISTS idx_dividends_ex_date
ON dividends(ex_dividend_date DESC);

-- 銘柄での検索用（既存のINDEXがあれば不要）
CREATE INDEX IF NOT EXISTS idx_dividends_ticker
ON dividends(ticker_symbol);

-- 5. 保有銘柄テーブル（holdings）のインデックス
-- 銘柄シンボルはすでにユニーク制約があるため、追加不要
-- ただし、更新日時でのソート用にインデックス追加
CREATE INDEX IF NOT EXISTS idx_holdings_last_updated
ON holdings(last_updated DESC);

-- インデックス作成完了確認用クエリ
SELECT
    name as index_name,
    tbl_name as table_name,
    sql as index_definition
FROM sqlite_master
WHERE type = 'index'
  AND name LIKE 'idx_%'
ORDER BY tbl_name, name;
