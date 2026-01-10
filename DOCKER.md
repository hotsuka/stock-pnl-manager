# Docker利用ガイド

Stock P&L ManagerをDockerで実行するためのガイドです。

## 目次

1. [前提条件](#前提条件)
2. [開発環境での実行](#開発環境での実行)
3. [本番環境での実行](#本番環境での実行)
4. [コマンドリファレンス](#コマンドリファレンス)
5. [トラブルシューティング](#トラブルシューティング)
6. [Docker構成の詳細](#docker構成の詳細)

---

## 前提条件

### 必要なソフトウェア

- **Docker**: 20.10以上
- **Docker Compose**: 2.0以上

### インストール確認

```bash
docker --version
docker-compose --version
```

### Dockerのインストール

#### Windows
1. [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) をダウンロード
2. インストーラーを実行
3. WSL 2を有効化（推奨）

#### macOS
1. [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/) をダウンロード
2. インストーラーを実行

#### Linux
```bash
# Ubuntuの場合
sudo apt-get update
sudo apt-get install docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker

# ユーザーをdockerグループに追加
sudo usermod -aG docker $USER
```

---

## 開発環境での実行

### 1. 基本的な起動

```bash
# イメージのビルドとコンテナ起動
docker-compose up -d

# ログの確認
docker-compose logs -f app

# ブラウザでアクセス
# http://localhost:5000
```

### 2. 初回セットアップ

```bash
# データベースの初期化
docker-compose exec app flask db upgrade

# サンプルデータのインポート（オプション）
docker-compose exec app python -c "
from app import create_app, db
from app.services.csv_parser import CSVParser
from app.services.transaction_service import TransactionService

app = create_app('development')
with app.app_context():
    parser = CSVParser()
    data = parser.parse_file('data/sample_transactions.csv')
    TransactionService.save_transactions(data)
"
```

### 3. コンテナの停止

```bash
# コンテナを停止（データは保持）
docker-compose stop

# コンテナを停止して削除（データは保持）
docker-compose down

# コンテナとボリュームを削除（データも削除）
docker-compose down -v
```

---

## 本番環境での実行

### 1. 環境変数の設定

```bash
# .envファイルを作成
cp .env.example .env

# .envファイルを編集
nano .env
```

**.env の必須項目**:
```bash
# シークレットキー（必ず変更すること）
SECRET_KEY=<強固なランダム文字列>

# 環境設定
FLASK_ENV=production

# データベースURL（デフォルトはSQLite）
DATABASE_URL=sqlite:///data/stock_pnl.db

# ログレベル
LOG_LEVEL=INFO

# バックアップ保持日数
BACKUP_RETENTION_DAYS=30
```

**シークレットキーの生成**:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. 本番環境での起動

```bash
# 本番用docker-composeで起動
docker-compose -f docker-compose.prod.yml up -d

# ログの確認
docker-compose -f docker-compose.prod.yml logs -f app

# ブラウザでアクセス
# http://localhost:8000
```

### 3. データベースマイグレーション

```bash
# マイグレーション実行
docker-compose -f docker-compose.prod.yml exec app flask db upgrade

# マイグレーション履歴確認
docker-compose -f docker-compose.prod.yml exec app flask db history
```

### 4. Nginxリバースプロキシの設定（オプション）

Nginxを使用する場合:

```bash
# nginx.confを作成
mkdir -p nginx
cat > nginx/nginx.conf <<'EOF'
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:8000;
    }

    server {
        listen 80;
        server_name localhost;

        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /static {
            alias /app/app/static;
        }
    }
}
EOF

# docker-compose.prod.ymlのnginxサービスのコメントを解除
# docker-compose -f docker-compose.prod.yml up -d
```

---

## コマンドリファレンス

### ビルド関連

```bash
# イメージのビルド
docker-compose build

# キャッシュを使わずにビルド
docker-compose build --no-cache

# 特定のサービスのみビルド
docker-compose build app
```

### 起動・停止

```bash
# バックグラウンドで起動
docker-compose up -d

# フォアグラウンドで起動（ログ表示）
docker-compose up

# 停止
docker-compose stop

# 停止して削除
docker-compose down

# ボリュームも含めて削除
docker-compose down -v
```

### ログ確認

```bash
# 全サービスのログ
docker-compose logs

# 特定サービスのログ
docker-compose logs app

# ログをフォロー（リアルタイム表示）
docker-compose logs -f app

# 最新100行のログ
docker-compose logs --tail=100 app
```

### コンテナ内でコマンド実行

```bash
# シェルに入る
docker-compose exec app bash

# Pythonインタラクティブシェル
docker-compose exec app python

# Flaskコマンド
docker-compose exec app flask --help

# データベースマイグレーション
docker-compose exec app flask db upgrade

# スクリプト実行
docker-compose exec app python scripts/update_prices_manual.py
```

### データベース操作

```bash
# データベースバックアップ
docker-compose exec app python -c "
import shutil
from datetime import datetime
shutil.copy('data/stock_pnl.db', f'backups/stock_pnl_{datetime.now():%Y%m%d_%H%M%S}.db')
"

# データベース復元
docker cp backups/stock_pnl_20260111.db stock-pnl-manager-prod:/app/data/stock_pnl.db
docker-compose -f docker-compose.prod.yml restart app
```

### ボリューム管理

```bash
# ボリューム一覧
docker volume ls

# ボリューム詳細
docker volume inspect stock-pnl-manager_app-data

# ボリュームのバックアップ
docker run --rm -v stock-pnl-manager_app-data:/data -v $(pwd)/backups:/backup alpine tar czf /backup/data-backup.tar.gz /data

# ボリュームの復元
docker run --rm -v stock-pnl-manager_app-data:/data -v $(pwd)/backups:/backup alpine tar xzf /backup/data-backup.tar.gz -C /
```

---

## トラブルシューティング

### Q1. コンテナが起動しない

**原因**: ポートが既に使用されている

**対処法**:
```bash
# Windowsの場合
netstat -ano | findstr :5000

# macOS/Linuxの場合
lsof -i :5000

# ポートを変更
# docker-compose.ymlのportsを編集: "5001:5000"
```

### Q2. データベースエラーが発生する

**原因**: マイグレーションが実行されていない

**対処法**:
```bash
docker-compose exec app flask db upgrade
```

### Q3. イメージのビルドが失敗する

**原因**: キャッシュの問題

**対処法**:
```bash
# キャッシュをクリアしてビルド
docker-compose build --no-cache

# Docker全体のクリーンアップ
docker system prune -a
```

### Q4. パフォーマンスが遅い

**原因**: Windowsでのファイルシステムの問題

**対処法**:
- WSL 2を使用する
- ボリュームマウントを最小限にする
- データベースをDocker volumeに配置

### Q5. ログが表示されない

**原因**: ログレベルの設定

**対処法**:
```bash
# .envファイルを編集
LOG_LEVEL=DEBUG

# コンテナを再起動
docker-compose restart app
```

---

## Docker構成の詳細

### ファイル構成

```
stock-pnl-manager/
├── Dockerfile                 # アプリケーションイメージ定義
├── docker-compose.yml         # 開発環境設定
├── docker-compose.prod.yml    # 本番環境設定
├── .dockerignore             # イメージに含めないファイル
└── nginx/                    # Nginx設定（オプション）
    ├── nginx.conf
    └── ssl/
```

### Dockerfile の構成

**マルチステージビルド**を使用:

1. **base**: Python環境とシステム依存関係
2. **dependencies**: Python依存パッケージのインストール
3. **production**: 本番用の最小イメージ

**セキュリティ対策**:
- 非rootユーザー（appuser）で実行
- 不要なファイルを除外（.dockerignore）
- 最小限のベースイメージ（python:3.11-slim）

### ボリューム構成

**開発環境**:
- `app-data`: データベースファイル
- `app-logs`: ログファイル
- `pip-cache`: pipキャッシュ（高速化）

**本番環境**:
- `app-data-prod`: 本番データベース
- `app-logs-prod`: 本番ログ
- `nginx-logs`: Nginxログ

### ネットワーク構成

- **開発**: `stock-pnl-network` (bridge)
- **本番**: `stock-pnl-network-prod` (172.20.0.0/16)

---

## 本番デプロイのベストプラクティス

### 1. リソース制限

docker-compose.prod.ymlで設定済み:
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

### 2. ヘルスチェック

自動でコンテナの健全性を監視:
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; ..."]
  interval: 30s
  timeout: 10s
  retries: 3
```

### 3. 自動再起動

```yaml
restart: always
```

### 4. 環境変数の管理

- `.env`ファイルで管理
- シークレットは環境変数で注入
- Gitに`.env`は含めない（`.gitignore`で除外）

### 5. ログローテーション

Docker標準のログドライバーを使用:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 6. バックアップ

自動バックアップサービスを有効化:
```bash
# docker-compose.prod.ymlのbackupサービスを有効化
docker-compose -f docker-compose.prod.yml up -d backup
```

---

## 参考資料

- [Docker公式ドキュメント](https://docs.docker.com/)
- [Docker Compose公式ドキュメント](https://docs.docker.com/compose/)
- [Flask Docker デプロイガイド](https://flask.palletsprojects.com/en/2.3.x/tutorial/deploy/)
- [USER_GUIDE.md](docs/USER_GUIDE.md) - ユーザーマニュアル
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - デプロイガイド（準備中）

---

**最終更新**: 2026-01-11
**バージョン**: 1.0.0
