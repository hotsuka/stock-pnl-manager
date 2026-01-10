# Scripts - 運用スクリプト集

このディレクトリには、Stock P&L Managerの運用・管理に使用するスクリプトが含まれています。

## スクリプト一覧

### 本番環境起動スクリプト

#### start_production.sh (Linux/macOS)
```bash
./scripts/start_production.sh
```

**機能**:
- 環境変数の読み込み
- データベースマイグレーション実行
- Gunicornでアプリケーション起動

**前提条件**:
- `.env`ファイルが設定済み
- Gunicornがインストール済み

#### start_production.bat (Windows)
```cmd
scripts\start_production.bat
```

**機能**:
- 環境変数の読み込み
- データベースマイグレーション実行
- Waitressでアプリケーション起動

**前提条件**:
- `.env`ファイルが設定済み
- Waitressがインストール済み

### データベース管理スクリプト

#### backup_database.py
```bash
python scripts/backup_database.py
```

**機能**:
- データベースのバックアップ作成
- タイムスタンプ付きファイル名
- 古いバックアップの自動削除
- クラウドストレージへのアップロード（オプション）

**オプション**:
- `--output-dir`: バックアップ保存先（デフォルト: `./backups`）
- `--keep-days`: 保存期間（デフォルト: 30日）
- `--upload-cloud`: クラウドにアップロード

#### restore_database.py
```bash
python scripts/restore_database.py <backup_file>
```

**機能**:
- バックアップからデータベースを復元
- 復元前の自動バックアップ

### メンテナンススクリプト

#### update_all_data.py
```bash
python scripts/update_all_data.py
```

**機能**:
- 全保有銘柄の株価更新
- 配当データの更新
- 評価指標の更新
- ベンチマーク価格の更新

**使用場面**:
- 毎日の定期実行（cron/タスクスケジューラ）
- 手動での一括更新

#### cleanup_old_data.py
```bash
python scripts/cleanup_old_data.py
```

**機能**:
- 古いログファイルの削除
- 一時ファイルのクリーンアップ
- キャッシュのクリア

### セットアップスクリプト

#### init_production.sh (Linux/macOS)
```bash
./scripts/init_production.sh
```

**機能**:
- 仮想環境の作成
- 依存パッケージのインストール
- データベースの初期化
- 初期設定ファイルの作成

#### init_production.bat (Windows)
```cmd
scripts\init_production.bat
```

Windowsでの初期セットアップを実行します。

### ヘルスチェックスクリプト

#### health_check.py
```bash
python scripts/health_check.py
```

**機能**:
- アプリケーションの稼働確認
- データベース接続確認
- 外部API接続確認
- ディスク容量確認

**使用場面**:
- 監視システムとの連携
- デプロイ後の動作確認

### パフォーマンステストスクリプト

#### load_test.py
```bash
python scripts/load_test.py
```

**機能**:
- API負荷テスト
- レスポンスタイム測定
- エラーレート確認

**オプション**:
- `--users`: 同時ユーザー数
- `--duration`: テスト期間（秒）

## 定期実行の設定

### Linux/macOS (cron)

```bash
# crontabを編集
crontab -e

# 毎日午前2時にデータ更新
0 2 * * * /path/to/venv/bin/python /path/to/scripts/update_all_data.py

# 毎週日曜午前3時にバックアップ
0 3 * * 0 /path/to/venv/bin/python /path/to/scripts/backup_database.py

# 毎日午前4時にクリーンアップ
0 4 * * * /path/to/venv/bin/python /path/to/scripts/cleanup_old_data.py
```

### Windows (タスクスケジューラ)

タスクスケジューラでバッチファイルを登録：

```cmd
schtasks /create /tn "StockPnL_Update" /tr "C:\path\to\scripts\update_all_data.bat" /sc daily /st 02:00
schtasks /create /tn "StockPnL_Backup" /tr "C:\path\to\scripts\backup_database.bat" /sc weekly /d SUN /st 03:00
```

## スクリプト開発ガイドライン

### 新しいスクリプトを作成する際の注意点

1. **シバン行の追加** (Linux/macOS)
   ```python
   #!/usr/bin/env python
   ```

2. **実行権限の付与**
   ```bash
   chmod +x scripts/your_script.py
   ```

3. **ログ出力**
   ```python
   from app.utils.logger import get_logger
   logger = get_logger('script_name')
   ```

4. **エラーハンドリング**
   ```python
   try:
       # 処理
   except Exception as e:
       logger.error(f"エラー: {str(e)}")
       sys.exit(1)
   ```

5. **環境変数の使用**
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

## トラブルシューティング

### スクリプトが実行できない

**原因**: 実行権限がない
```bash
chmod +x scripts/script_name.sh
```

**原因**: Pythonパスが間違っている
```bash
which python
# 仮想環境のPythonを使用
source venv/bin/activate
```

### データベースロックエラー

**対処法**: アプリケーションを停止してから実行
```bash
# アプリケーションを停止
pkill -f "python run.py"

# スクリプト実行
python scripts/backup_database.py
```

## 今後の実装予定

- [ ] start_production.sh / .bat の作成
- [ ] backup_database.py の実装
- [ ] restore_database.py の実装
- [ ] update_all_data.py の実装
- [ ] cleanup_old_data.py の実装
- [ ] init_production.sh / .bat の作成
- [ ] health_check.py の実装
- [ ] load_test.py の実装

---

**最終更新**: 2026-01-10
