# サーバー管理ガイド

Stock P&L Manager本番サーバーの起動・停止方法

## サーバーの起動

### 方法1: 簡易起動スクリプト（推奨）

プロジェクトディレクトリで以下のファイルをダブルクリック：

```
start_server.bat
```

または、コマンドプロンプトから：

```cmd
start_server.bat
```

サーバーが起動すると以下のように表示されます：

```
======================================
Stock P&L Manager - 本番サーバー起動
======================================

[情報] サーバーを起動しています...

アクセスURL: http://localhost:8000
停止方法: Ctrl+C を押してください

INFO:waitress:Serving on http://0.0.0.0:8000
```

### 方法2: 手動起動

コマンドプロンプトで以下を実行：

```cmd
cd c:\Users\the-b\stock-pnl-manager
python -m waitress --host=0.0.0.0 --port=8000 --threads=4 wsgi:app
```

### 方法3: バックグラウンド起動

コマンドプロンプトで以下を実行：

```cmd
cd c:\Users\the-b\stock-pnl-manager
start /B python -m waitress --host=0.0.0.0 --port=8000 --threads=4 wsgi:app > logs\server.log 2>&1
```

この方法では、ウィンドウを閉じてもサーバーが動き続けます。

## サーバーの停止

### 方法1: フォアグラウンド実行時（方法1または2で起動）

サーバーが実行されているコマンドプロンプトで：

```
Ctrl + C を押す
```

### 方法2: バックグラウンド実行時（方法3で起動）

1. タスクマネージャーを開く（Ctrl + Shift + Esc）
2. 「詳細」タブを選択
3. `python.exe`プロセスを見つける
   - コマンドライン: `python -m waitress...`
4. プロセスを右クリック → 「タスクの終了」

または、コマンドプロンプトで：

```cmd
taskkill /F /IM python.exe /FI "WINDOWTITLE eq waitress*"
```

**注意**: この方法は全てのpython.exeを終了する可能性があります。

## サーバーの状態確認

### ヘルスチェック

サーバーが起動しているか確認：

```cmd
curl http://localhost:8000/api/health
```

正常時の応答：

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "data": {
      "status": "healthy",
      "transactions": 236,
      "holdings": 26
    }
  }
}
```

### プロセス確認

```cmd
netstat -ano | findstr :8000
```

ポート8000を使用しているプロセスが表示されれば起動中です。

## トラブルシューティング

### ポート8000が既に使用されている

**エラー**: `OSError: [WinError 10048] 通常、各ソケット アドレスに対してプロトコル、ネットワーク アドレス、またはポートのどれか 1 つのみを使用できます。`

**解決方法**:

1. 使用中のプロセスを確認：
   ```cmd
   netstat -ano | findstr :8000
   ```

2. プロセスIDを確認して終了：
   ```cmd
   taskkill /F /PID <プロセスID>
   ```

3. または、別のポートで起動：
   ```cmd
   python -m waitress --port=8001 wsgi:app
   ```

### .envファイルが見つからない

**エラー**: `.envファイルが見つかりません`

**解決方法**:

1. .env.exampleをコピー：
   ```cmd
   copy .env.example .env
   ```

2. .envファイルを編集してSECRET_KEYを設定

### Waitressがインストールされていない

**エラー**: `No module named 'waitress'`

**解決方法**:

```cmd
pip install waitress
```

### データベースエラー

**エラー**: `Database connection failed`

**解決方法**:

1. データベースファイルの確認：
   ```cmd
   dir data\stock_pnl.db
   ```

2. データベースが存在しない場合、初期化：
   ```cmd
   python scripts\init_db.py
   ```

3. マイグレーション実行：
   ```cmd
   flask db upgrade
   ```

## ログの確認

### アプリケーションログ

```cmd
type logs\flask.log
```

最新の10行を表示：

```cmd
powershell Get-Content logs\flask.log -Tail 10
```

リアルタイムでログを監視：

```cmd
powershell Get-Content logs\flask.log -Wait
```

### サーバーログ（バックグラウンド実行時）

```cmd
type logs\server.log
```

## 自動起動設定（オプション）

Windowsスタートアップに登録して、PC起動時に自動起動：

1. `start_server.bat`のショートカットを作成
2. ショートカットを以下のフォルダに移動：
   ```
   C:\Users\<ユーザー名>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup
   ```

または、タスクスケジューラで設定：

1. タスクスケジューラを開く
2. 「基本タスクの作成」を選択
3. トリガー: 「ログオン時」
4. 操作: 「プログラムの起動」
5. プログラム: `C:\Users\the-b\stock-pnl-manager\start_server.bat`

## アクセスURL

- **メイン画面**: http://localhost:8000/
- **ダッシュボード**: http://localhost:8000/
- **保有銘柄**: http://localhost:8000/holdings
- **取引履歴**: http://localhost:8000/transactions
- **配当履歴**: http://localhost:8000/dividends
- **パフォーマンス**: http://localhost:8000/performance
- **ベンチマーク**: http://localhost:8000/benchmarks
- **CSVアップロード**: http://localhost:8000/upload
- **API**: http://localhost:8000/api/*
- **ヘルスチェック**: http://localhost:8000/api/health

## サーバー設定

サーバーの設定は`.env`ファイルで変更できます：

```ini
# ポート番号
PORT=8000

# ワーカー数（スレッド数）
WORKERS=4

# タイムアウト（秒）
TIMEOUT=120

# ログレベル
LOG_LEVEL=INFO
```

設定変更後はサーバーを再起動してください。

## 関連ドキュメント

- [デプロイガイド](docs/DEPLOYMENT.md) - 詳細なデプロイ手順
- [監視・運用ガイド](docs/MONITORING.md) - ログ監視とメンテナンス
- [ユーザーガイド](docs/USER_GUIDE.md) - アプリケーションの使い方
- [トラブルシューティング](docs/FAQ.md) - よくある質問
