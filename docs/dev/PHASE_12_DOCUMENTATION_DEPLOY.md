# Phase 12: ドキュメント・デプロイ実装計画

## 概要
Phase 12では、アプリケーションの完成度を高めるため、包括的なドキュメント整備とデプロイメント環境の構築を行います。

## 実装スコープ

### 1. APIドキュメントの整備

#### 1.1 API仕様書の作成
**ファイル**: `docs/API_REFERENCE.md`

**内容**:
- 全APIエンドポイントの詳細仕様
- リクエスト/レスポンス形式
- エラーコード一覧
- 認証・認可（将来実装時の考慮）
- レート制限（将来実装時の考慮）

**実装するAPIエンドポイント一覧**:
```
1. 株価取得API
   - GET /api/stock-price/<ticker>
   - POST /api/stock-price/update-all

2. 為替レートAPI
   - GET /api/exchange-rate/<from_currency>
   - GET /api/exchange-rate/multiple

3. 保有銘柄API
   - GET /api/holdings
   - GET /api/holdings/<ticker>

4. 取引履歴API
   - GET /api/transactions
   - POST /api/transactions
   - PUT /api/transactions/<id>
   - DELETE /api/transactions/<id>

5. 配当API
   - GET /api/dividends
   - POST /api/dividends/update
   - POST /api/dividends/update-all

6. 実現損益API
   - GET /api/realized-pnl

7. 損益推移API
   - GET /api/performance/history
   - GET /api/performance/detail

8. 株式評価指標API
   - GET /api/stock-metrics/<ticker>
   - POST /api/stock-metrics/update/<ticker>
   - POST /api/stock-metrics/update-all

9. ベンチマークAPI (Phase 11)
   - GET /api/benchmark/prices/<symbol>
   - POST /api/benchmark/update
```

#### 1.2 OpenAPI (Swagger) 仕様の作成
**ファイル**: `docs/openapi.yaml`

**実装内容**:
- OpenAPI 3.0.0仕様に準拠
- Swagger UIでの閲覧可能
- 自動生成ツールとの連携（将来）

**必要パッケージ**:
```
flask-swagger-ui==4.11.1
pyyaml==6.0.1
```

### 2. ユーザーガイドの作成

#### 2.1 ユーザーマニュアル
**ファイル**: `docs/USER_GUIDE.md`

**章立て**:
1. はじめに
   - アプリケーション概要
   - 主な機能
   - 動作環境

2. インストールと初期設定
   - 環境構築手順
   - データベース初期化
   - 初回起動

3. 基本操作
   - CSVファイルのアップロード
   - ダッシュボードの見方
   - 保有銘柄の確認
   - 取引履歴の管理

4. 高度な機能
   - 損益推移の分析
   - 配当金の管理
   - 株式評価指標の活用
   - ベンチマーク比較（Phase 11）

5. メンテナンス
   - データの更新
   - バックアップ
   - トラブルシューティング

#### 2.2 開発者ガイド
**ファイル**: `docs/DEVELOPER_GUIDE.md`

**章立て**:
1. プロジェクト構造
2. アーキテクチャ概要
3. データモデル詳細
4. サービス層の実装
5. テストの実行
6. コントリビューション方法

#### 2.3 FAQ
**ファイル**: `docs/FAQ.md`

**内容**:
- よくある質問と回答
- トラブルシューティング
- パフォーマンスチューニング

### 3. Dockerコンテナ化

#### 3.1 Dockerfileの作成
**ファイル**: `Dockerfile`

**戦略**:
```dockerfile
# Multi-stage build
FROM python:3.14-slim as builder
# 依存関係のインストール

FROM python:3.14-slim
# 本番環境用の最小構成
```

**含める機能**:
- Python 3.14ベースイメージ
- 必要な依存パッケージのインストール
- アプリケーションコードのコピー
- 非rootユーザーでの実行
- ヘルスチェック

#### 3.2 docker-compose.yml の作成
**ファイル**: `docker-compose.yml`

**サービス構成**:
```yaml
services:
  app:
    # Flaskアプリケーション
  db:
    # SQLiteは組み込みのため不要（将来PostgreSQL対応時に追加）
```

**環境別設定**:
- `docker-compose.yml` - 開発環境
- `docker-compose.prod.yml` - 本番環境

#### 3.3 .dockerignore の作成
**ファイル**: `.dockerignore`

**除外対象**:
- venv/
- __pycache__/
- *.pyc
- .git/
- *.db
- data/uploads/*
- flask.log

### 4. 本番環境デプロイ手順

#### 4.1 デプロイガイド
**ファイル**: `docs/DEPLOYMENT.md`

**章立て**:
1. デプロイ前の準備
   - 環境要件
   - 設定ファイルの準備
   - シークレット管理

2. ローカルデプロイ
   - 仮想環境でのセットアップ
   - systemdサービス設定（Linux）
   - Windowsサービス設定

3. Dockerデプロイ
   - Dockerイメージのビルド
   - コンテナの起動
   - ログ確認

4. クラウドデプロイ（将来対応）
   - AWS (EC2, ECS)
   - Google Cloud (Cloud Run)
   - Azure (App Service)
   - Heroku

5. リバースプロキシ設定
   - Nginx設定例
   - SSL/TLS証明書

#### 4.2 環境変数管理
**ファイル**: `.env.example`

**内容**:
```bash
# アプリケーション設定
FLASK_APP=run.py
FLASK_ENV=production
SECRET_KEY=<generate-secret-key>

# データベース
DATABASE_URL=sqlite:///stock_pnl.db

# ログ設定
LOG_LEVEL=INFO
LOG_FILE=flask.log

# 外部API（オプション）
# YAHOO_FINANCE_API_KEY=
```

#### 4.3 起動スクリプト
**ファイル**: `scripts/start_production.sh`

**内容**:
- 環境変数の読み込み
- データベースマイグレーション
- Gunicorn/uWSGIでの起動

**ファイル**: `scripts/start_production.bat` (Windows)

### 5. CI/CDパイプライン（基礎）

#### 5.1 GitHub Actions設定
**ファイル**: `.github/workflows/test.yml`

**ワークフロー**:
- プッシュ時のテスト実行
- Linting (pylint, flake8)
- カバレッジレポート

**ファイル**: `.github/workflows/docker.yml`

**ワークフロー**:
- Dockerイメージのビルド
- イメージのプッシュ（Docker Hub / GitHub Container Registry）

### 6. 運用ツール

#### 6.1 ヘルスチェックエンドポイント
**実装場所**: `app/routes/api.py`

```python
@bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'database': check_database_connection()
    })
```

#### 6.2 バックアップスクリプト
**ファイル**: `scripts/backup_database.py`

**機能**:
- データベースのバックアップ
- 古いバックアップの自動削除
- クラウドストレージへのアップロード（オプション）

#### 6.3 モニタリング
**ファイル**: `docs/MONITORING.md`

**内容**:
- ログの監視方法
- パフォーマンスメトリクス
- アラート設定（将来）

## 実装順序

### Step 1: APIドキュメント整備（優先度: 高）
1. API_REFERENCE.mdの作成
2. 既存のAPIエンドポイントを調査
3. リクエスト/レスポンス例を記述
4. エラーハンドリングを文書化

### Step 2: ユーザーガイド作成（優先度: 高）
1. USER_GUIDE.mdの作成
2. スクリーンショットの準備
3. 操作手順の詳細記述
4. FAQの作成

### Step 3: Dockerコンテナ化（優先度: 中）
1. Dockerfileの作成
2. docker-compose.ymlの作成
3. .dockerignoreの作成
4. ローカルでの動作確認

### Step 4: デプロイ手順書作成（優先度: 中）
1. DEPLOYMENT.mdの作成
2. .env.exampleの作成
3. 起動スクリプトの作成
4. デプロイテスト

### Step 5: 運用ツール実装（優先度: 低）
1. ヘルスチェックエンドポイント実装
2. バックアップスクリプト作成
3. モニタリングガイド作成

### Step 6: CI/CD設定（優先度: 低）
1. GitHub Actionsの設定
2. 自動テストの統合
3. Dockerイメージの自動ビルド

## 成果物チェックリスト

### ドキュメント
- [ ] docs/API_REFERENCE.md
- [ ] docs/openapi.yaml
- [ ] docs/USER_GUIDE.md
- [ ] docs/DEVELOPER_GUIDE.md
- [ ] docs/FAQ.md
- [ ] docs/DEPLOYMENT.md
- [ ] docs/MONITORING.md

### Docker関連
- [ ] Dockerfile
- [ ] docker-compose.yml
- [ ] docker-compose.prod.yml
- [ ] .dockerignore

### 設定ファイル
- [ ] .env.example
- [ ] .github/workflows/test.yml
- [ ] .github/workflows/docker.yml

### スクリプト
- [ ] scripts/start_production.sh
- [ ] scripts/start_production.bat
- [ ] scripts/backup_database.py

### コード追加
- [ ] app/routes/api.py (ヘルスチェック)
- [ ] requirements.txt (Swagger UI関連)

## 完了条件

1. 全APIエンドポイントが文書化されている
2. ユーザーが操作手順を理解できる
3. Dockerで簡単に起動できる
4. 本番環境へのデプロイ手順が明確
5. 基本的な運用監視ができる

## 補足事項

### セキュリティ考慮事項
- シークレットキーの管理
- 環境変数の適切な設定
- SQLインジェクション対策（既存）
- CSRF対策（既存）

### パフォーマンス考慮事項
- 静的ファイルの配信（Nginx）
- データベース接続プーリング
- キャッシュ戦略

### スケーラビリティ
- 現状: 単一インスタンス想定
- 将来: 水平スケーリング対応（Redis, PostgreSQL）

## 参考資料

- Flask公式ドキュメント: https://flask.palletsprojects.com/
- Docker公式ドキュメント: https://docs.docker.com/
- OpenAPI Specification: https://swagger.io/specification/
- GitHub Actions: https://docs.github.com/actions

---

**作成日**: 2026-01-10
**最終更新**: 2026-01-10
**バージョン**: 1.0
