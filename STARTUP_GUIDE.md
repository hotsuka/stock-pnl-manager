# アプリケーション起動ガイド

## 問題: http://localhost:5000 にアクセスできない

マイグレーションは正常に完了しましたが、アプリケーションが起動していないため、アクセスできません。

## 原因

仮想環境のFlaskパッケージが不完全な状態になっている可能性があります。
(`flask/__init__.py`が欠落しています)

## 解決方法

### 方法1: 依存パッケージの再インストール(推奨)

1. **コマンドプロンプトまたはPowerShellを開く**

2. **プロジェクトディレクトリに移動**
   ```cmd
   cd c:\Users\the-b\stock-pnl-manager
   ```

3. **仮想環境を再作成**
   ```cmd
   rmdir /s /q venv
   python -m venv venv
   ```

4. **依存パッケージをインストール**
   ```cmd
   venv\Scripts\pip.exe install -r requirements.txt
   ```

5. **アプリケーションを起動**
   ```cmd
   venv\Scripts\python.exe run.py
   ```

### 方法2: システムのPythonを使用

依存パッケージをシステム全体にインストールする場合:

1. **依存パッケージをインストール**
   ```cmd
   pip install -r requirements.txt
   ```

2. **アプリケーションを起動**
   ```cmd
   python run.py
   ```

### 方法3: Flask CLIを使用

1. **環境変数を設定**
   ```cmd
   set FLASK_APP=run.py
   set FLASK_ENV=development
   ```

2. **Flaskを起動**
   ```cmd
   venv\Scripts\flask.exe run
   ```

   または、システムのPythonを使用する場合:
   ```cmd
   python -m flask run
   ```

## 起動確認

アプリケーションが正常に起動すると、以下のような出力が表示されます:

```
 * Serving Flask app 'run.py'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://127.0.0.1:5000
 * Running on http://0.0.0.0:5000
Press CTRL+C to quit
 * Restarting with stat
 * Debugger is active!
```

その後、以下のURLにアクセスできます:

- **トップページ**: http://localhost:5000
- **ダッシュボード**: http://localhost:5000/dashboard
- **CSV アップロード**: http://localhost:5000/upload

## トラブルシューティング

### エラー: `ModuleNotFoundError: No module named 'flask'`

→ 依存パッケージがインストールされていません。上記の「方法1」を実行してください。

### エラー: `Address already in use`

→ ポート5000が既に使用されています。

1. 使用中のプロセスを確認:
   ```cmd
   netstat -ano | findstr :5000
   ```

2. 別のポートを使用:
   ```cmd
   python run.py --port 5001
   ```

### エラー: データベース関連のエラー

→ マイグレーションが適用されていない可能性があります。

```cmd
python quick_migrate.py
```

## 次のステップ

アプリケーションが起動したら:

1. **ダッシュボードにアクセス**: http://localhost:5000/dashboard
2. **CSVファイルをアップロード**: http://localhost:5000/upload
   - サンプルファイル: `data/sample_transactions.csv`
3. **株価と指標が自動的に取得されます**

## データベースの状態

現在のデータベースの状態:

- ✅ すべてのテーブルが作成済み
- ✅ stock_metricsテーブル(Phase 10)も作成済み
- ⚠️ データは空(CSVアップロードが必要)

### テーブル一覧

1. `transactions` - 取引履歴
2. `holdings` - 保有銘柄
3. `dividends` - 配当履歴
4. `stock_prices` - 株価キャッシュ
5. `realized_pnl` - 確定損益
6. `stock_metrics` - 株式評価指標(Phase 10)
7. `alembic_version` - マイグレーション管理

すべてのテーブルが正常に作成され、マイグレーションバージョンは `001_initial` に設定されています。
