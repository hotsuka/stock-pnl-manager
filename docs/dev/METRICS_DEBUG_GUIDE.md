# 評価指標のデバッグガイド

## 問題

「保有銘柄一覧」ページの「評価指標」タブでデータが読み込めない。

## 確認済み事項

### ✅ データベース
- stock_metricsテーブルに26件のデータが正常に保存されている
- データの内容も正しい（PER、時価総額など）

### ✅ バックエンドAPI
- `/api/holdings/metrics` エンドポイントが正常に動作
- テストスクリプトで確認済み（`test_metrics_api.py`）
- レスポンス例:
  ```json
  {
    "success": true,
    "count": 26,
    "metrics": [
      {
        "ticker_symbol": "6498.T",
        "market_cap": 159695142912.0,
        "pe_ratio": 13.86,
        ...
      }
    ]
  }
  ```

### ✅ フロントエンド実装
- JavaScriptの実装は正しい
- APIエンドポイントのパスも正しい（`/api/holdings/metrics`）
- デバッグログを追加済み

## デバッグ手順

### 1. ブラウザでページを開く

http://localhost:5000/holdings にアクセスします。

### 2. ブラウザの開発者ツールを開く

- **Chrome/Edge**: F12 または 右クリック → 検証
- **Firefox**: F12 または 右クリック → 要素を調査

### 3. コンソールタブを確認

「評価指標」タブをクリックした時に以下のようなログが表示されるはずです:

```
[DEBUG] loadMetricsData 開始
[DEBUG] APIリクエスト送信: /api/holdings/metrics
[DEBUG] レスポンス受信: 200 true
[DEBUG] JSONパース完了: {success: true, count: 26, metrics: Array(26)}
[DEBUG] success: true
[DEBUG] count: 26
[DEBUG] metrics length: 26
[DEBUG] metricsData 設定完了: 26 件
[DEBUG] renderMetricsTable 開始
[DEBUG] tbody要素: [object HTMLTableSectionElement]
[DEBUG] metricsData件数: 26
[DEBUG] テーブル描画開始
[DEBUG] テーブル描画完了
```

### 4. エラーの確認

もしエラーが発生している場合、以下のいずれかが表示されます:

- **ネットワークエラー**: `[DEBUG] 評価指標データ取得エラー: ...`
- **描画エラー**: `[DEBUG] テーブル描画エラー: ...`

### 5. ネットワークタブの確認

開発者ツールの「Network」(ネットワーク) タブで:

1. 「評価指標」タブをクリック
2. `/api/holdings/metrics` へのリクエストを探す
3. ステータスコードが200になっているか確認
4. レスポンスの内容を確認

## よくある問題と解決方法

### 問題1: ネットワークエラー (404 Not Found)

**原因**: アプリケーションが起動していないか、URLが間違っている

**解決方法**:
```bash
# アプリケーションを起動
python run.py
```

### 問題2: CORS エラー

**原因**: ブラウザのセキュリティ設定

**解決方法**:
- 同じドメインからアクセスしていることを確認
- http://localhost:5000 から直接アクセス

### 問題3: JavaScriptエラー

**原因**: フォーマット関数が未定義

**解決方法**:
- ページを完全にリロード（Ctrl+F5）
- キャッシュをクリア

### 問題4: データは取得できているがテーブルが空

**原因**: レンダリング関数のエラー

**解決方法**:
- コンソールログで `metricsData` の内容を確認
- どのフォーマット関数でエラーが発生しているか特定

## トラブルシューティング用コマンド

### データベースの確認
```python
python -c "import sys; sys.path.insert(0, 'venv/Lib/site-packages'); import sqlite3; conn = sqlite3.connect('data/stock_pnl.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM stock_metrics'); print('評価指標レコード数:', cursor.fetchone()[0]); conn.close()"
```

### APIテスト
```python
python test_metrics_api.py
```

### アプリケーションログの確認
```bash
# ログファイルを確認（もし存在すれば）
cat logs/app.log | grep metrics
```

## 解決しない場合の追加デバッグ

### JavaScriptコンソールで直接テスト

開発者ツールのコンソールで以下を実行:

```javascript
// APIを直接呼び出し
fetch('/api/holdings/metrics')
  .then(r => r.json())
  .then(data => console.log('API Response:', data))
  .catch(e => console.error('Error:', e));

// metricsDataの確認
console.log('Current metricsData:', metricsData);

// 手動でloadを実行
loadMetricsData();
```

## 次のステップ

コンソールログとネットワークログを確認して、具体的なエラーメッセージを特定してください。
エラーメッセージがあれば、それをもとに原因を特定できます。

## 連絡先

問題が解決しない場合は、以下の情報を添えて報告してください:

1. ブラウザのコンソールログ（全文）
2. ネットワークタブのスクリーンショット
3. エラーメッセージ（あれば）
4. `test_metrics_api.py` の実行結果
