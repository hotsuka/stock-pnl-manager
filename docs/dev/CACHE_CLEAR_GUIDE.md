# ブラウザキャッシュのクリア方法

## 問題
holdings.htmlの変更がブラウザに反映されない

## 原因
ブラウザがJavaScriptファイルをキャッシュしているため、古いバージョンが使用されている可能性があります。

## 解決方法

### 方法1: スーパーリロード（最も簡単）

**Windows/Linux:**
- `Ctrl + F5`
- または `Ctrl + Shift + R`

**Mac:**
- `Cmd + Shift + R`

### 方法2: 開発者ツールでキャッシュを無効化

1. **開発者ツールを開く** (F12)
2. **Networkタブ**を選択
3. **「Disable cache」にチェック**を入れる
4. 開発者ツールを**開いたまま**ページをリロード

### 方法3: ブラウザのキャッシュを完全にクリア

#### Chrome/Edge
1. `Ctrl + Shift + Delete`
2. 「キャッシュされた画像とファイル」を選択
3. 「データを削除」をクリック

#### Firefox
1. `Ctrl + Shift + Delete`
2. 「キャッシュ」を選択
3. 「今すぐクリア」をクリック

### 方法4: プライベートウィンドウで開く

**Windows/Linux:**
- `Ctrl + Shift + N` (Chrome/Edge)
- `Ctrl + Shift + P` (Firefox)

**Mac:**
- `Cmd + Shift + N` (Chrome/Edge)
- `Cmd + Shift + P` (Firefox)

プライベートウィンドウで http://localhost:5000/holdings を開く

## 確認方法

開発者ツール(F12) → Consoleタブで以下を実行:

```javascript
// formatMarketCap関数の内容を確認
console.log(formatMarketCap.toString());

// 実際の値で動作確認
console.log('3.5B:', formatMarketCap(3500000000, 'USD'));
console.log('150兆:', formatMarketCap(150000000000000, 'JPY'));
```

**期待される出力:**
- `3.5B:` → `4BN` (小数点なし、TN/BN/MN形式)
- `150兆:` → `150.00兆円`

## それでも反映されない場合

### アプリケーションの再起動

1. **サーバーを停止** (Ctrl+C)
2. **サーバーを再起動**
   ```bash
   python run.py
   ```
3. ブラウザで再度アクセス

### タイムスタンプの確認

開発者ツール → Networkタブで:
1. holdings ページをリロード
2. `holdings` (HTMLファイル) をクリック
3. Headersタブで `Last-Modified` の日時を確認
4. 最近の日時になっているか確認

## 変更内容の確認

ファイルには以下の変更が正しく保存されています:

### 1. 時価総額・売上フォーマット
```javascript
// 外貨の場合
if (value >= 1e12) return (value / 1e12).toFixed(0) + 'TN';  // 小数点なし
if (value >= 1e9) return (value / 1e9).toFixed(0) + 'BN';    // 小数点なし
if (value >= 1e6) return (value / 1e6).toFixed(0) + 'MN';    // 小数点なし
```

### 2. 利益率フォーマット
```javascript
// +マークを削除
return pct.toFixed(2) + '%';  // 以前: (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%'
```

### 3. YTD/1年リターン
- stock_metrics_fetcher.pyのリターン計算ロジックを修正
- `python update_metrics_returns.py` でデータを再取得する必要があります

## まとめ

1. **Ctrl + F5** でスーパーリロード
2. それでもダメなら開発者ツールで「Disable cache」を有効化
3. まだダメならプライベートウィンドウで開く
4. 最終手段: ブラウザを完全に閉じて再起動

ほとんどの場合、**Ctrl + F5** で解決します。
