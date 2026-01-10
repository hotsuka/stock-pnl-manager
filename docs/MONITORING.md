# 監視・運用ガイド

Stock P&L Managerの監視とメンテナンスに関するガイドです。

## 目次

1. [ログ管理](#ログ管理)
2. [パフォーマンス監視](#パフォーマンス監視)
3. [バックアップとリストア](#バックアップとリストア)
4. [定期メンテナンス](#定期メンテナンス)
5. [アラート設定](#アラート設定)
6. [トラブルシューティング](#トラブルシューティング)

---

## ログ管理

### 1. ログの種類

Stock P&L Managerは以下のログを出力します:

| ログファイル | 内容 | 場所 |
|------------|------|------|
| app.log | アプリケーションログ | logs/app.log |
| access.log | アクセスログ（Nginx使用時） | /var/log/nginx/access.log |
| error.log | エラーログ（Nginx使用時） | /var/log/nginx/error.log |
| gunicorn.log | Gunicornログ | logs/gunicorn.log |

### 2. ログレベル

環境変数 `LOG_LEVEL` で設定:

```bash
# 開発環境
LOG_LEVEL=DEBUG

# 本番環境
LOG_LEVEL=INFO
```

**ログレベルの種類**:
- `DEBUG`: 詳細なデバッグ情報
- `INFO`: 一般的な情報（推奨: 本番環境）
- `WARNING`: 警告メッセージ
- `ERROR`: エラーメッセージ
- `CRITICAL`: 致命的なエラー

### 3. ログの確認

#### アプリケーションログ

```bash
# 最新100行を表示
tail -100 logs/app.log

# リアルタイムで表示
tail -f logs/app.log

# エラーのみ表示
grep ERROR logs/app.log

# 特定の日付のログ
grep "2026-01-11" logs/app.log
```

#### Dockerコンテナのログ

```bash
# コンテナログを表示
docker-compose logs app

# リアルタイムで表示
docker-compose logs -f app

# 最新100行
docker-compose logs --tail=100 app

# エラーのみ
docker-compose logs app 2>&1 | grep ERROR
```

### 4. ログローテーション

#### Linux (logrotate)

```bash
sudo nano /etc/logrotate.d/stock-pnl-manager
```

**設定例**:
```
/path/to/stock-pnl-manager/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 appuser appuser
    sharedscripts
    postrotate
        systemctl reload stock-pnl-manager
    endscript
}
```

#### Windows (PowerShell スクリプト)

```powershell
# logs/rotate-logs.ps1
$logPath = "C:\path\to\stock-pnl-manager\logs"
$archivePath = "$logPath\archive"
$retentionDays = 30

# アーカイブディレクトリ作成
if (!(Test-Path $archivePath)) {
    New-Item -ItemType Directory -Path $archivePath
}

# 古いログをアーカイブ
Get-ChildItem -Path $logPath -Filter "*.log" | ForEach-Object {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $archiveName = "$($_.BaseName)_$timestamp.log"
    Move-Item -Path $_.FullName -Destination "$archivePath\$archiveName"
}

# 30日以上前のアーカイブを削除
Get-ChildItem -Path $archivePath -Filter "*.log" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$retentionDays) } |
    Remove-Item
```

**タスクスケジューラで毎日実行**:
```powershell
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\path\to\logs\rotate-logs.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 3AM
Register-ScheduledTask -TaskName "StockPnL_LogRotation" -Action $action -Trigger $trigger
```

---

## パフォーマンス監視

### 1. システムリソース監視

#### CPU・メモリ使用率

**Linux**:
```bash
# リアルタイム監視
top -p $(pgrep -f gunicorn)

# htopを使用（推奨）
htop -p $(pgrep -f gunicorn | tr '\n' ',')

# プロセス情報
ps aux | grep gunicorn
```

**Windows**:
```powershell
# タスクマネージャー
taskmgr

# PowerShellで確認
Get-Process python | Select-Object CPU, WorkingSet
```

#### ディスク使用量

```bash
# Linux
df -h
du -sh /path/to/stock-pnl-manager/data

# Windows
Get-PSDrive C | Select-Object Used,Free
```

### 2. アプリケーション監視

#### ヘルスチェックエンドポイント

アプリケーションが正常に動作しているか確認:

```bash
# ローカル
curl http://localhost:8000/api/health

# リモート
curl https://your-domain.com/api/health
```

**期待されるレスポンス**:
```json
{
  "status": "healthy",
  "database": "connected",
  "uptime": "24h 30m",
  "version": "1.0.0"
}
```

#### レスポンスタイム測定

```bash
# curlでレスポンスタイム測定
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/

# curl-format.txt の内容
# time_namelookup:  %{time_namelookup}\n
# time_connect:  %{time_connect}\n
# time_starttransfer:  %{time_starttransfer}\n
# time_total:  %{time_total}\n
```

### 3. データベース監視

#### SQLite統計

```bash
# データベースサイズ
ls -lh data/stock_pnl.db

# テーブル統計
sqlite3 data/stock_pnl.db "SELECT name, COUNT(*) FROM sqlite_master WHERE type='table' GROUP BY name;"

# レコード数
sqlite3 data/stock_pnl.db "SELECT
  (SELECT COUNT(*) FROM transactions) as transactions,
  (SELECT COUNT(*) FROM holdings) as holdings,
  (SELECT COUNT(*) FROM dividends) as dividends;"
```

#### クエリパフォーマンス

```python
# Pythonスクリプトで実行
from app import create_app, db
import time

app = create_app('production')
with app.app_context():
    start = time.time()
    # クエリ実行
    result = db.session.execute("SELECT COUNT(*) FROM transactions")
    end = time.time()
    print(f"Query time: {end - start:.3f}s")
```

### 4. 外部API監視

Yahoo Finance APIの応答時間と成功率を監視:

```bash
# スクリプト: scripts/check_external_apis.py
python scripts/check_external_apis.py
```

---

## バックアップとリストア

### 1. データベースバックアップ

#### 手動バックアップ

**SQLite**:
```bash
# タイムスタンプ付きバックアップ
cp data/stock_pnl.db backups/stock_pnl_$(date +%Y%m%d_%H%M%S).db

# または専用スクリプト
python scripts/backup_database.py
```

**PostgreSQL**:
```bash
pg_dump -U stock_pnl_user stock_pnl_db > backups/stock_pnl_$(date +%Y%m%d_%H%M%S).sql
```

#### 自動バックアップ

**Linux (cron)**:
```bash
# crontabを編集
crontab -e

# 毎日午前3時にバックアップ
0 3 * * * /path/to/stock-pnl-manager/scripts/backup_database.sh
```

**backup_database.sh**:
```bash
#!/bin/bash
cd /path/to/stock-pnl-manager
source venv/bin/activate
python scripts/backup_database.py
find backups -name "stock_pnl_*.db" -mtime +30 -delete
```

**Windows (タスクスケジューラ)**:
```powershell
# バックアップスクリプト: scripts/backup_database.ps1
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item "data\stock_pnl.db" "backups\stock_pnl_$timestamp.db"

# 30日以上前のバックアップを削除
Get-ChildItem "backups\stock_pnl_*.db" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
    Remove-Item

# タスク登録
schtasks /create /tn "StockPnL_Backup" /tr "powershell.exe -File C:\path\to\scripts\backup_database.ps1" /sc daily /st 03:00
```

**Docker環境**:
```bash
# docker-compose.prod.ymlのbackupサービスが自動実行
docker-compose -f docker-compose.prod.yml up -d backup
```

### 2. データベースリストア

#### SQLiteのリストア

```bash
# アプリケーションを停止
systemctl stop stock-pnl-manager
# または
docker-compose stop app

# バックアップからリストア
cp backups/stock_pnl_20260111_030000.db data/stock_pnl.db

# アプリケーションを再起動
systemctl start stock-pnl-manager
# または
docker-compose start app
```

#### PostgreSQLのリストア

```bash
# データベースを削除して再作成
dropdb -U postgres stock_pnl_db
createdb -U postgres stock_pnl_db

# バックアップからリストア
psql -U stock_pnl_user stock_pnl_db < backups/stock_pnl_20260111.sql
```

### 3. クラウドバックアップ

#### AWS S3へのバックアップ

```bash
# AWS CLIのインストール
pip install awscli

# 認証設定
aws configure

# バックアップスクリプト
#!/bin/bash
BACKUP_FILE="backups/stock_pnl_$(date +%Y%m%d_%H%M%S).db"
cp data/stock_pnl.db $BACKUP_FILE
aws s3 cp $BACKUP_FILE s3://your-bucket/stock-pnl-backups/
```

#### Google Cloud Storageへのバックアップ

```bash
# gcloud CLIのインストール
# https://cloud.google.com/sdk/docs/install

# バックアップ
gsutil cp data/stock_pnl.db gs://your-bucket/stock-pnl-backups/stock_pnl_$(date +%Y%m%d_%H%M%S).db
```

---

## 定期メンテナンス

### 1. データ更新

#### 株価の自動更新

**cron設定 (Linux)**:
```bash
# 平日の午後6時（日本市場終了後）
0 18 * * 1-5 cd /path/to/stock-pnl-manager && venv/bin/python scripts/update_prices_manual.py

# 平日の午前6時（米国市場終了後・日本時間）
0 6 * * 2-6 cd /path/to/stock-pnl-manager && venv/bin/python scripts/update_prices_manual.py
```

**タスクスケジューラ (Windows)**:
```powershell
# 平日午後6時に実行
schtasks /create /tn "StockPnL_UpdatePrices" /tr "C:\path\to\venv\Scripts\python.exe C:\path\to\scripts\update_prices_manual.py" /sc weekly /d MON,TUE,WED,THU,FRI /st 18:00
```

#### 配当データの更新

```bash
# 毎週日曜日午前8時
0 8 * * 0 cd /path/to/stock-pnl-manager && venv/bin/python scripts/update_dividends.py
```

#### すべてのデータを更新

```bash
# 毎日午前2時に全データ更新
0 2 * * * cd /path/to/stock-pnl-manager && venv/bin/python scripts/update_all_data.py
```

### 2. データベース最適化

#### SQLite VACUUM

```bash
# 週次で実行
sqlite3 data/stock_pnl.db "VACUUM;"
```

**cron設定**:
```bash
# 毎週日曜日午前4時
0 4 * * 0 sqlite3 /path/to/stock-pnl-manager/data/stock_pnl.db "VACUUM;"
```

### 3. ログのクリーンアップ

```bash
# 30日以上前のログを削除
find logs -name "*.log" -mtime +30 -delete

# 圧縮してアーカイブ
find logs -name "*.log" -mtime +7 -exec gzip {} \;
```

---

## アラート設定

### 1. ディスク使用量アラート

```bash
#!/bin/bash
# scripts/check_disk_usage.sh

THRESHOLD=80
USAGE=$(df -h /path/to/stock-pnl-manager | awk 'NR==2 {print $5}' | sed 's/%//')

if [ $USAGE -gt $THRESHOLD ]; then
    echo "Disk usage is ${USAGE}% - exceeds ${THRESHOLD}% threshold" |
        mail -s "Stock PnL Manager: Disk Usage Alert" admin@example.com
fi
```

### 2. アプリケーション停止アラート

```bash
#!/bin/bash
# scripts/check_app_status.sh

if ! curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "Application is not responding" |
        mail -s "Stock PnL Manager: Application Down" admin@example.com
    # 自動再起動（オプション）
    systemctl restart stock-pnl-manager
fi
```

**cron設定**:
```bash
# 5分ごとにチェック
*/5 * * * * /path/to/scripts/check_app_status.sh
```

### 3. エラーログ監視

```bash
#!/bin/bash
# scripts/monitor_errors.sh

ERROR_COUNT=$(grep -c ERROR logs/app.log)

if [ $ERROR_COUNT -gt 10 ]; then
    tail -50 logs/app.log | grep ERROR |
        mail -s "Stock PnL Manager: High Error Count ($ERROR_COUNT)" admin@example.com
fi
```

---

## トラブルシューティング

### 1. 一般的な問題

#### アプリケーションが応答しない

**診断**:
```bash
# プロセス確認
ps aux | grep gunicorn

# ポート確認
lsof -i :8000

# ログ確認
tail -100 logs/app.log
```

**対処法**:
```bash
# アプリケーション再起動
systemctl restart stock-pnl-manager

# または
docker-compose restart app
```

#### データベースロック

**診断**:
```bash
# ロック確認
fuser data/stock_pnl.db
```

**対処法**:
```bash
# ロックしているプロセスを終了
fuser -k data/stock_pnl.db

# アプリケーション再起動
systemctl restart stock-pnl-manager
```

#### メモリ不足

**診断**:
```bash
# メモリ使用状況
free -h

# プロセスごとのメモリ使用量
ps aux --sort=-%mem | head -10
```

**対処法**:
```bash
# ワーカー数を減らす（config変更後）
systemctl restart stock-pnl-manager

# スワップの追加（Linux）
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 2. デバッグモード

一時的にデバッグモードを有効化:

```bash
# .envファイルを編集
LOG_LEVEL=DEBUG

# アプリケーション再起動
systemctl restart stock-pnl-manager

# ログをリアルタイム監視
tail -f logs/app.log
```

---

## 監視ツール

### 1. Prometheus + Grafana（推奨）

本格的な監視システムを構築する場合:

**docker-compose.prod.ymlで有効化**:
```yaml
# prometheus, grafanaサービスのコメントを解除
docker-compose -f docker-compose.prod.yml up -d prometheus grafana
```

**アクセス**:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

### 2. Uptime Kuma（軽量監視）

```bash
# Docker で起動
docker run -d --restart=always -p 3001:3001 -v uptime-kuma:/app/data --name uptime-kuma louislam/uptime-kuma:1

# http://localhost:3001 でアクセス
```

---

## メンテナンススケジュール例

| タスク | 頻度 | 推奨時刻 | 説明 |
|--------|------|---------|------|
| 株価更新 | 毎日 | 18:00 | 日本市場終了後 |
| 配当データ更新 | 週次 | 日曜 08:00 | 週次で最新データ取得 |
| データベースバックアップ | 毎日 | 03:00 | データ損失防止 |
| ログローテーション | 毎日 | 04:00 | ディスク容量管理 |
| データベース最適化 | 週次 | 日曜 04:00 | パフォーマンス維持 |
| システム更新 | 月次 | 第1日曜 05:00 | セキュリティパッチ適用 |
| 古いバックアップ削除 | 毎日 | 04:30 | 30日以上前を削除 |

---

## 参考資料

- [DEPLOYMENT.md](DEPLOYMENT.md) - デプロイガイド
- [USER_GUIDE.md](USER_GUIDE.md) - ユーザーマニュアル
- [DOCKER.md](../DOCKER.md) - Docker利用ガイド
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

---

**最終更新**: 2026-01-11
**バージョン**: 1.0.0
