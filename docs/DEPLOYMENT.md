# デプロイガイド

Stock P&L Managerを本番環境にデプロイするための包括的なガイドです。

## 目次

1. [デプロイ前の準備](#デプロイ前の準備)
2. [ローカル環境へのデプロイ](#ローカル環境へのデプロイ)
3. [Dockerでのデプロイ](#dockerでのデプロイ)
4. [クラウド環境へのデプロイ](#クラウド環境へのデプロイ)
5. [本番環境の設定](#本番環境の設定)
6. [セキュリティ設定](#セキュリティ設定)
7. [パフォーマンスチューニング](#パフォーマンスチューニング)
8. [トラブルシューティング](#トラブルシューティング)

---

## デプロイ前の準備

### 1. システム要件

#### 最小要件
- **CPU**: 1コア以上
- **メモリ**: 1GB以上
- **ディスク**: 5GB以上の空き容量
- **OS**: Windows 10/11, macOS 10.15+, Ubuntu 20.04+

#### 推奨要件
- **CPU**: 2コア以上
- **メモリ**: 2GB以上
- **ディスク**: 10GB以上の空き容量（ログ・バックアップ用）

### 2. 必要なソフトウェア

#### Python環境でのデプロイ
- Python 3.8以上（推奨: 3.10+）
- pip 21.0以上

#### Docker環境でのデプロイ
- Docker 20.10以上
- Docker Compose 2.0以上

### 3. チェックリスト

デプロイ前に以下を確認してください:

- [ ] システム要件を満たしている
- [ ] 必要なポートが開放されている（5000または8000）
- [ ] データベースのバックアップが取得されている
- [ ] 環境変数が適切に設定されている
- [ ] SSL証明書が用意されている（HTTPSの場合）
- [ ] ドメイン名が設定されている（公開する場合）

---

## ローカル環境へのデプロイ

### Windows環境

#### 1. リポジトリのクローン

```powershell
git clone <repository-url>
cd stock-pnl-manager
```

#### 2. 仮想環境の作成

```powershell
python -m venv venv
venv\Scripts\activate
```

#### 3. 依存パッケージのインストール

```powershell
pip install -r requirements.txt
```

#### 4. 環境変数の設定

```powershell
# .envファイルを作成
copy .env.example .env

# .envファイルを編集
notepad .env
```

**.env の設定例**:
```bash
FLASK_ENV=production
SECRET_KEY=<強固なランダム文字列>
DATABASE_URL=sqlite:///data/stock_pnl.db
LOG_LEVEL=INFO
```

**シークレットキーの生成**:
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

#### 5. データベースの初期化

```powershell
flask db upgrade
```

#### 6. 本番サーバーの起動

**Waitressを使用** (Windows推奨):

```powershell
# Waitressのインストール
pip install waitress

# 起動
waitress-serve --host 0.0.0.0 --port 8000 --call app:create_app
```

または**起動スクリプトを使用**:

```powershell
scripts\start_production.bat
```

### Linux/macOS環境

#### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd stock-pnl-manager
```

#### 2. 仮想環境の作成

```bash
python3 -m venv venv
source venv/bin/activate
```

#### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

#### 4. 環境変数の設定

```bash
# .envファイルを作成
cp .env.example .env

# .envファイルを編集
nano .env
```

#### 5. データベースの初期化

```bash
flask db upgrade
```

#### 6. 本番サーバーの起動

**Gunicornを使用** (Linux/macOS推奨):

```bash
gunicorn -w 4 -b 0.0.0.0:8000 --timeout 120 'app:create_app("production")'
```

または**起動スクリプトを使用**:

```bash
chmod +x scripts/start_production.sh
./scripts/start_production.sh
```

---

## Dockerでのデプロイ

Dockerを使用したデプロイは最も簡単で推奨される方法です。

### 1. 環境変数の設定

```bash
cp .env.example .env
nano .env
```

### 2. Dockerイメージのビルド

```bash
# 開発環境
docker-compose build

# 本番環境
docker-compose -f docker-compose.prod.yml build
```

### 3. コンテナの起動

```bash
# 開発環境（ポート5000）
docker-compose up -d

# 本番環境（ポート8000）
docker-compose -f docker-compose.prod.yml up -d
```

### 4. ログの確認

```bash
docker-compose logs -f app
```

### 5. データベースマイグレーション

```bash
docker-compose exec app flask db upgrade
```

詳細は [DOCKER.md](../DOCKER.md) を参照してください。

---

## クラウド環境へのデプロイ

### AWS (EC2)でのデプロイ

#### 1. EC2インスタンスの作成

1. AWS Management Consoleにログイン
2. EC2ダッシュボードから「インスタンスを起動」
3. AMI選択: Ubuntu Server 22.04 LTS
4. インスタンスタイプ: t2.small以上
5. セキュリティグループ: HTTP(80), HTTPS(443), カスタムTCP(8000)を許可

#### 2. サーバーのセットアップ

```bash
# SSH接続
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>

# システム更新
sudo apt update && sudo apt upgrade -y

# Dockerのインストール
sudo apt install docker.io docker-compose -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu

# 再ログイン
exit
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>
```

#### 3. アプリケーションのデプロイ

```bash
# リポジトリのクローン
git clone <repository-url>
cd stock-pnl-manager

# 環境変数の設定
cp .env.example .env
nano .env

# Dockerで起動
docker-compose -f docker-compose.prod.yml up -d
```

#### 4. Nginxリバースプロキシの設定

```bash
# Nginxのインストール
sudo apt install nginx -y

# 設定ファイルの作成
sudo nano /etc/nginx/sites-available/stock-pnl-manager
```

**Nginx設定例**:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# 設定を有効化
sudo ln -s /etc/nginx/sites-available/stock-pnl-manager /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Herokuでのデプロイ

#### 1. Procfileの作成

```bash
# プロジェクトルートに作成
cat > Procfile <<EOF
web: gunicorn -w 4 -b 0.0.0.0:\$PORT 'app:create_app("production")'
EOF
```

#### 2. runtime.txtの作成

```bash
cat > runtime.txt <<EOF
python-3.11.7
EOF
```

#### 3. Heroku CLIでデプロイ

```bash
# Heroku CLIのインストール
# https://devcenter.heroku.com/articles/heroku-cli

# ログイン
heroku login

# アプリ作成
heroku create your-app-name

# 環境変数の設定
heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
heroku config:set FLASK_ENV=production

# デプロイ
git push heroku main

# マイグレーション実行
heroku run flask db upgrade

# ログ確認
heroku logs --tail
```

### Google Cloud Platform (App Engine)

#### 1. app.yamlの作成

```yaml
runtime: python311

env_variables:
  FLASK_ENV: "production"
  SECRET_KEY: "<your-secret-key>"

handlers:
- url: /static
  static_dir: app/static

- url: /.*
  script: auto
```

#### 2. デプロイ

```bash
# Google Cloud SDKのインストール
# https://cloud.google.com/sdk/docs/install

# 認証
gcloud auth login

# プロジェクト設定
gcloud config set project your-project-id

# デプロイ
gcloud app deploy

# ログ確認
gcloud app logs tail -s default
```

---

## 本番環境の設定

### 1. 環境変数

本番環境で必ず設定すべき環境変数:

```bash
# セキュリティ
SECRET_KEY=<強固な64文字のランダム文字列>
FLASK_ENV=production

# データベース
DATABASE_URL=sqlite:///data/stock_pnl.db

# ログ
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log

# パフォーマンス
WORKERS=4
TIMEOUT=120

# バックアップ
BACKUP_RETENTION_DAYS=30
```

### 2. データベース設定

#### SQLiteの場合（小規模運用）

```bash
# データディレクトリの作成
mkdir -p data
chmod 755 data

# データベースの初期化
flask db upgrade
```

#### PostgreSQLへの移行（推奨: 大規模運用）

```bash
# PostgreSQLのインストール
sudo apt install postgresql postgresql-contrib -y

# データベースとユーザーの作成
sudo -u postgres psql
```

```sql
CREATE DATABASE stock_pnl_db;
CREATE USER stock_pnl_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE stock_pnl_db TO stock_pnl_user;
\q
```

**.env の更新**:
```bash
DATABASE_URL=postgresql://stock_pnl_user:secure_password@localhost/stock_pnl_db
```

**psycopg2のインストール**:
```bash
pip install psycopg2-binary
```

**マイグレーション**:
```bash
flask db upgrade
```

### 3. ログ設定

```bash
# ログディレクトリの作成
mkdir -p logs
chmod 755 logs

# ログローテーション設定（Linux）
sudo nano /etc/logrotate.d/stock-pnl-manager
```

**logrotate設定例**:
```
/path/to/stock-pnl-manager/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload stock-pnl-manager
    endscript
}
```

---

## セキュリティ設定

### 1. ファイアウォール設定

#### UFW (Ubuntu)

```bash
# UFWのインストールと有効化
sudo apt install ufw -y
sudo ufw enable

# 必要なポートのみ開放
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8000/tcp   # アプリポートは直接公開しない

# 状態確認
sudo ufw status
```

#### Windows Firewall

```powershell
# PowerShellで実行
New-NetFirewallRule -DisplayName "Stock PnL Manager" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

### 2. SSL/TLS証明書の設定

#### Let's Encryptを使用（無料）

```bash
# Certbotのインストール
sudo apt install certbot python3-certbot-nginx -y

# 証明書の取得
sudo certbot --nginx -d your-domain.com

# 自動更新の設定
sudo certbot renew --dry-run
```

**Nginx設定（HTTPS対応後）**:
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

### 3. セキュリティヘッダーの設定

**Nginx設定に追加**:
```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

---

## パフォーマンスチューニング

### 1. Gunicornワーカー数の最適化

**推奨ワーカー数**:
```
ワーカー数 = (2 × CPUコア数) + 1
```

**例**: 2コアCPUの場合
```bash
gunicorn -w 5 -b 0.0.0.0:8000 'app:create_app("production")'
```

### 2. データベース最適化

#### SQLiteの最適化

**.env に追加**:
```bash
SQLALCHEMY_ENGINE_OPTIONS='{"pool_pre_ping": true, "pool_recycle": 3600}'
```

#### PostgreSQLの最適化

**postgresql.confの調整**:
```
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
```

### 3. キャッシュの設定

**Redis導入（オプション）**:

```bash
# Redisのインストール
sudo apt install redis-server -y

# requirements.txtに追加
pip install Flask-Caching redis
```

**app/__init__.pyに追加**:
```python
from flask_caching import Cache

cache = Cache(config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': 'redis://localhost:6379/0'
})

def create_app(config_name=None):
    app = Flask(__name__)
    cache.init_app(app)
    # ...
```

---

## トラブルシューティング

### 問題1: アプリケーションが起動しない

**原因**: ポートが既に使用されている

**確認**:
```bash
# Linux/macOS
lsof -i :8000

# Windows
netstat -ano | findstr :8000
```

**対処法**: 別のポートを使用するか、既存のプロセスを終了

---

### 問題2: データベース接続エラー

**原因**: データベースファイルのパーミッション

**対処法**:
```bash
chmod 644 data/stock_pnl.db
chmod 755 data
```

---

### 問題3: 静的ファイルが読み込まれない

**原因**: Nginxの設定ミス

**対処法**:
```nginx
location /static {
    alias /path/to/stock-pnl-manager/app/static;
}
```

---

### 問題4: メモリ不足

**原因**: ワーカー数が多すぎる

**対処法**: ワーカー数を減らす
```bash
gunicorn -w 2 -b 0.0.0.0:8000 'app:create_app("production")'
```

---

### 問題5: ログが記録されない

**原因**: ログディレクトリのパーミッション

**対処法**:
```bash
mkdir -p logs
chmod 755 logs
chown -R $USER:$USER logs
```

---

## systemdサービス設定（Linux）

永続的にアプリケーションを実行するためのsystemdサービス設定:

```bash
sudo nano /etc/systemd/system/stock-pnl-manager.service
```

**サービスファイル**:
```ini
[Unit]
Description=Stock P&L Manager
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/stock-pnl-manager
Environment="PATH=/home/ubuntu/stock-pnl-manager/venv/bin"
ExecStart=/home/ubuntu/stock-pnl-manager/venv/bin/gunicorn -w 4 -b 0.0.0.0:8000 --timeout 120 'app:create_app("production")'
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**サービスの有効化**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable stock-pnl-manager
sudo systemctl start stock-pnl-manager
sudo systemctl status stock-pnl-manager
```

**ログ確認**:
```bash
sudo journalctl -u stock-pnl-manager -f
```

---

## デプロイ後のチェックリスト

デプロイ完了後、以下を確認してください:

- [ ] アプリケーションが正常に起動している
- [ ] データベースマイグレーションが完了している
- [ ] 環境変数が正しく設定されている
- [ ] ログが正常に記録されている
- [ ] 外部からアクセスできる
- [ ] HTTPSが有効になっている（本番環境）
- [ ] バックアップが設定されている
- [ ] 監視システムが稼働している
- [ ] ファイアウォールが適切に設定されている
- [ ] セキュリティヘッダーが設定されている

---

## 参考資料

- [USER_GUIDE.md](USER_GUIDE.md) - ユーザーマニュアル
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - 開発者ガイド
- [DOCKER.md](../DOCKER.md) - Docker利用ガイド
- [MONITORING.md](MONITORING.md) - 監視・運用ガイド
- [Flask Deployment Guide](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)

---

**最終更新**: 2026-01-11
**バージョン**: 1.0.0
