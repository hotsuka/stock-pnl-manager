# 開発者ガイド

Stock P&L Managerの開発者向けドキュメント

## 目次

1. [プロジェクト概要](#プロジェクト概要)
2. [アーキテクチャ](#アーキテクチャ)
3. [開発環境のセットアップ](#開発環境のセットアップ)
4. [プロジェクト構造](#プロジェクト構造)
5. [データベース設計](#データベース設計)
6. [ビジネスロジック](#ビジネスロジック)
7. [API設計](#api設計)
8. [テスト](#テスト)
9. [コーディング規約](#コーディング規約)
10. [デプロイ](#デプロイ)
11. [コントリビューション](#コントリビューション)

---

## プロジェクト概要

### 技術スタック

| カテゴリ | 技術 | バージョン | 用途 |
|---------|------|-----------|------|
| **バックエンド** | Python | 3.14+ | メイン言語 |
| | Flask | 3.0.0 | Webフレームワーク |
| | Flask-SQLAlchemy | 3.1.1 | ORM |
| | Flask-Migrate | 4.0.5 | DBマイグレーション |
| | Flask-WTF | 1.2.1 | フォーム処理 |
| **データベース** | SQLite | 3.x | データストア |
| **データ処理** | Pandas | 2.2.0+ | データ分析 |
| | NumPy | 1.26.0+ | 数値計算 |
| **外部API** | yfinance | 0.2.33+ | 株価・配当データ取得 |
| | forex-python | 1.8 | 為替レート取得 |
| **可視化** | Plotly | 5.18.0 | グラフ描画 |
| **テスト** | pytest | 7.4.3+ | ユニットテスト |
| | pytest-cov | 4.1.0+ | カバレッジ測定 |

### 主要機能

1. **CSV取り込み**: 証券会社の取引履歴CSVをアップロード
2. **損益計算**: 移動平均法による取得単価計算と損益管理
3. **株価更新**: Yahoo Finance APIを使用した自動株価取得
4. **配当管理**: 配当データの取得と配当金履歴管理
5. **パフォーマンス分析**: ポートフォリオのリターン計算
6. **ベンチマーク比較**: 日経平均・S&P500との比較
7. **株式評価指標**: PER、PBR、EPS、ROEなどの表示
8. **REST API**: フロントエンドとのデータ連携

---

## アーキテクチャ

### アプリケーション構造

```
┌─────────────────────────────────────┐
│        フロントエンド (HTML/JS)      │
│   - Jinja2テンプレート               │
│   - Plotly.js                        │
│   - Bootstrap CSS                    │
└──────────────┬──────────────────────┘
               │ HTTP/JSON
┌──────────────▼──────────────────────┐
│         Flask アプリケーション        │
│  ┌─────────────────────────────┐   │
│  │   Blueprint (routes)         │   │
│  │  - main (表示)               │   │
│  │  - upload (CSV)              │   │
│  │  - api (REST API)            │   │
│  └──────────┬──────────────────┘   │
│             │                        │
│  ┌──────────▼──────────────────┐   │
│  │   Services (ビジネスロジック) │   │
│  │  - transaction_service       │   │
│  │  - stock_price_fetcher       │   │
│  │  - dividend_fetcher          │   │
│  │  - stock_metrics_fetcher     │   │
│  │  - benchmark_fetcher         │   │
│  │  - performance_service       │   │
│  └──────────┬──────────────────┘   │
│             │                        │
│  ┌──────────▼──────────────────┐   │
│  │   Models (データモデル)       │   │
│  │  - Transaction               │   │
│  │  - Holding                   │   │
│  │  - RealizedPnl              │   │
│  │  - Dividend                 │   │
│  │  - StockPrice               │   │
│  │  - StockMetrics             │   │
│  │  - BenchmarkPrice           │   │
│  └──────────┬──────────────────┘   │
└─────────────┼──────────────────────┘
              │
┌─────────────▼──────────────────────┐
│        SQLite データベース           │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│       外部API                        │
│  - Yahoo Finance (yfinance)         │
│  - Forex API (forex-python)         │
└─────────────────────────────────────┘
```

### デザインパターン

1. **アプリケーションファクトリー**: `create_app()`で環境別設定を適用
2. **Blueprint**: 機能別にルーティングを分離
3. **サービス層**: ビジネスロジックをコントローラーから分離
4. **ORM**: SQLAlchemyでデータベース抽象化
5. **依存性注入**: 設定ファイルから環境変数を注入

---

## 開発環境のセットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd stock-pnl-manager
```

### 2. 仮想環境の作成

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数の設定

```bash
# .envファイルを作成
cp .env.example .env

# .envファイルを編集
FLASK_ENV=development
SECRET_KEY=dev-secret-key
DATABASE_URL=sqlite:///data/stock_pnl.db
```

### 5. データベースの初期化

```bash
# マイグレーションディレクトリがない場合
flask db init

# マイグレーションファイルの作成
flask db migrate -m "Initial migration"

# マイグレーション適用
flask db upgrade
```

### 6. 開発サーバーの起動

```bash
python run.py
```

ブラウザで `http://localhost:5000` にアクセス

---

## プロジェクト構造

```
stock-pnl-manager/
├── app/                      # アプリケーション本体
│   ├── __init__.py          # アプリケーションファクトリー
│   ├── models/              # データモデル
│   │   ├── __init__.py
│   │   ├── transaction.py   # 取引履歴モデル
│   │   ├── holding.py       # 保有銘柄モデル
│   │   ├── realized_pnl.py  # 確定損益モデル
│   │   ├── dividend.py      # 配当モデル
│   │   ├── stock_price.py   # 株価モデル
│   │   ├── stock_metrics.py # 株式評価指標モデル
│   │   └── benchmark_price.py # ベンチマーク価格モデル
│   ├── routes/              # ルーティング
│   │   ├── __init__.py
│   │   ├── main.py         # メイン画面ルート
│   │   ├── upload.py       # CSVアップロードルート
│   │   └── api.py          # REST APIルート
│   ├── services/            # ビジネスロジック
│   │   ├── __init__.py
│   │   ├── transaction_service.py    # 取引処理サービス
│   │   ├── stock_price_fetcher.py    # 株価取得サービス
│   │   ├── dividend_fetcher.py       # 配当取得サービス
│   │   ├── stock_metrics_fetcher.py  # 評価指標取得サービス
│   │   ├── benchmark_fetcher.py      # ベンチマーク取得サービス
│   │   ├── performance_service.py    # パフォーマンス計算サービス
│   │   ├── exchange_rate_fetcher.py  # 為替レート取得サービス
│   │   └── csv_parser.py             # CSV解析サービス
│   ├── templates/           # HTMLテンプレート
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── holdings.html
│   │   ├── transactions.html
│   │   ├── dividends.html
│   │   ├── performance.html
│   │   ├── benchmarks.html
│   │   └── upload.html
│   ├── static/              # 静的ファイル
│   │   ├── css/
│   │   └── js/
│   └── utils/               # ユーティリティ
│       ├── __init__.py
│       ├── logger.py        # ロギング設定
│       └── errors.py        # エラーハンドリング
├── tests/                   # テストコード
│   ├── __init__.py
│   ├── conftest.py         # pytest設定
│   ├── test_models.py      # モデルテスト
│   ├── test_services.py    # サービステスト
│   ├── test_api.py         # APIテスト
│   ├── test_error_handling.py
│   └── test_stock_metrics.py
├── migrations/              # データベースマイグレーション
├── data/                    # データファイル
│   ├── stock_pnl.db        # SQLiteデータベース (gitignore)
│   ├── uploads/            # アップロードファイル (gitignore)
│   ├── sample_transactions.csv      # サンプルCSV（日本語）
│   └── sample_transactions_en.csv   # サンプルCSV（英語）
├── docs/                    # ドキュメント
│   ├── README.md           # ドキュメント目次
│   ├── USER_GUIDE.md       # ユーザーガイド
│   ├── DEVELOPER_GUIDE.md  # 開発者ガイド（本ファイル）
│   ├── FAQ.md              # よくある質問
│   ├── DEPLOYMENT.md       # デプロイガイド
│   ├── MONITORING.md       # 監視・運用ガイド
│   └── dev/                # 開発履歴ドキュメント
│       ├── PHASE_10_STOCK_METRICS.md
│       ├── PHASE_11_BENCHMARK_COMPARISON.md
│       ├── PHASE_12_DOCUMENTATION_DEPLOY.md
│       ├── PHASE_12_SUMMARY.md
│       ├── ERROR_HANDLING.md
│       ├── PERFORMANCE_OPTIMIZATION.md
│       └── その他の技術ドキュメント
├── scripts/                 # 運用スクリプト
│   ├── backup_database.py   # データベースバックアップ
│   ├── restore_database.py  # データベース復元
│   ├── update_all_data.py   # 全データ更新
│   ├── cleanup_old_data.py  # 古いデータクリーンアップ
│   ├── init_db.py           # データベース初期化
│   ├── recalculate_all.py   # 全データ再計算
│   ├── update_dividends.py  # 配当データ更新
│   ├── update_metrics_returns.py  # 評価指標更新
│   ├── update_prices_manual.py    # 株価手動更新
│   ├── start_production.sh  # 本番起動スクリプト（Linux/macOS）
│   └── start_production.bat # 本番起動スクリプト（Windows）
├── .github/                 # GitHub Actions設定
│   └── workflows/
│       ├── test.yml        # テスト自動化
│       └── docker.yml      # Docker自動ビルド
├── config.py               # 設定ファイル
├── run.py                  # 起動スクリプト
├── requirements.txt        # 依存パッケージ
├── .env.example            # 環境変数サンプル
├── .gitignore              # Git除外設定
├── Dockerfile              # Dockerイメージ設定
├── docker-compose.yml      # Docker開発環境
├── docker-compose.prod.yml # Docker本番環境
├── .dockerignore           # Docker除外設定
├── DOCKER.md               # Docker利用ガイド
├── FOLDER_STRUCTURE.md     # フォルダ構成説明
└── README.md               # プロジェクト概要
```

---

## データベース設計

### ER図

```
┌─────────────────┐
│  Transaction    │
│  (取引履歴)      │
├─────────────────┤
│ id (PK)         │
│ transaction_date│──┐
│ ticker_symbol   │  │
│ security_name   │  │
│ transaction_type│  │  (計算)
│ currency        │  │
│ quantity        │  ├─────────┐
│ unit_price      │  │         │
│ commission      │  │         ▼
│ settlement_amt  │  │  ┌─────────────┐
│ exchange_rate   │  │  │  Holding    │
│ created_at      │  │  │  (保有銘柄) │
│ updated_at      │  │  ├─────────────┤
└─────────────────┘  │  │ id (PK)     │
                     │  │ ticker      │◄──┐
                     │  │ total_qty   │   │
                     │  │ avg_cost    │   │
                     │  │ current_prc │   │
                     │  │ unrealzd_pnl│   │
                     │  │ last_updated│   │
                     │  └─────────────┘   │
                     │                     │
                     │  ┌─────────────┐   │
                     │  │ RealizedPnl │   │
                     └─►│ (確定損益)   │   │
                        ├─────────────┤   │
                        │ id (PK)     │   │
                        │ ticker      │   │
                        │ sell_date   │   │
                        │ quantity    │   │
                        │ avg_cost    │   │
                        │ sell_price  │   │
                        │ realized_pnl│   │
                        │ created_at  │   │
                        └─────────────┘   │
                                          │
        ┌─────────────┐                  │
        │  Dividend   │                  │
        │  (配当)      │                  │
        ├─────────────┤                  │
        │ id (PK)     │                  │
        │ ticker      │──────────────────┤
        │ ex_date     │                  │
        │ pay_date    │                  │
        │ amount      │                  │
        │ currency    │                  │
        │ created_at  │                  │
        └─────────────┘                  │
                                          │
        ┌─────────────┐                  │
        │ StockPrice  │                  │
        │ (株価)       │                  │
        ├─────────────┤                  │
        │ id (PK)     │                  │
        │ ticker      │──────────────────┤
        │ date        │                  │
        │ close       │                  │
        │ volume      │                  │
        │ created_at  │                  │
        └─────────────┘                  │
                                          │
        ┌──────────────┐                 │
        │ StockMetrics │                 │
        │ (評価指標)    │                 │
        ├──────────────┤                 │
        │ id (PK)      │                 │
        │ ticker       │─────────────────┘
        │ market_cap   │
        │ per          │
        │ pbr          │
        │ eps          │
        │ roe          │
        │ updated_at   │
        └──────────────┘
```

### 主要テーブル

#### 1. transactions (取引履歴)

| カラム名 | 型 | 制約 | 説明 |
|---------|------|------|------|
| id | Integer | PK | ID |
| transaction_date | Date | NOT NULL | 取引日 |
| ticker_symbol | String(20) | NOT NULL | ティッカーシンボル |
| security_name | String(200) | | 銘柄名 |
| transaction_type | String(10) | NOT NULL | BUY/SELL |
| currency | String(3) | NOT NULL | 通貨 (JPY/USD) |
| quantity | Numeric(15,4) | NOT NULL | 数量 |
| unit_price | Numeric(15,4) | NOT NULL | 単価 |
| commission | Numeric(15,4) | | 手数料 |
| settlement_amount | Numeric(15,4) | | 受渡金額 |
| exchange_rate | Numeric(10,4) | | 為替レート |
| created_at | DateTime | | 作成日時 |
| updated_at | DateTime | | 更新日時 |

**インデックス**:
- `transaction_date`
- `ticker_symbol`

#### 2. holdings (保有銘柄)

| カラム名 | 型 | 制約 | 説明 |
|---------|------|------|------|
| id | Integer | PK | ID |
| ticker_symbol | String(20) | UNIQUE | ティッカー |
| total_quantity | Numeric(15,4) | NOT NULL | 保有数量 |
| average_cost | Numeric(15,4) | NOT NULL | 平均取得単価 |
| currency | String(3) | NOT NULL | 通貨 |
| total_cost | Numeric(15,4) | NOT NULL | 総取得コスト |
| current_price | Numeric(15,4) | | 現在株価 |
| previous_close | Numeric(15,4) | | 前日終値 |
| day_change_pct | Numeric(10,4) | | 前日比変動率 |
| current_value | Numeric(15,4) | | 現在評価額 |
| unrealized_pnl | Numeric(15,4) | | 未実現損益 |
| unrealized_pnl_pct | Numeric(10,4) | | 未実現損益率 |
| last_updated | DateTime | | 最終更新日時 |

**インデックス**:
- `ticker_symbol` (UNIQUE)

#### 3. realized_pnls (確定損益)

| カラム名 | 型 | 制約 | 説明 |
|---------|------|------|------|
| id | Integer | PK | ID |
| ticker_symbol | String(20) | NOT NULL | ティッカー |
| sell_date | Date | NOT NULL | 売却日 |
| quantity | Numeric(15,4) | NOT NULL | 売却数量 |
| average_cost | Numeric(15,4) | NOT NULL | 平均取得単価 |
| sell_price | Numeric(15,4) | NOT NULL | 売却単価 |
| realized_pnl | Numeric(15,4) | NOT NULL | 確定損益 |
| realized_pnl_pct | Numeric(10,4) | | 確定損益率 |
| commission | Numeric(15,4) | | 手数料 |
| currency | String(3) | NOT NULL | 通貨 |

**インデックス**:
- `ticker_symbol`
- `sell_date`

---

## ビジネスロジック

### 1. 移動平均法による取得単価計算

**実装**: [transaction_service.py:82-151](app/services/transaction_service.py#L82-L151)

```python
# 買付時
def _update_holding(transaction):
    if transaction.transaction_type == 'BUY':
        transaction_cost = transaction.settlement_amount

        if holding:
            # 既存保有: 加重平均
            total_cost = holding.total_cost + transaction_cost
            total_quantity = holding.total_quantity + transaction.quantity
            holding.average_cost = total_cost / total_quantity
        else:
            # 新規保有
            holding = Holding(
                average_cost=transaction_cost / transaction.quantity,
                total_cost=transaction_cost
            )
```

**計算式**:
```
新平均単価 = (既存総取得コスト + 新規取得コスト) / (既存数量 + 新規数量)
```

### 2. 確定損益の計算

**実装**: [transaction_service.py:112-143](app/services/transaction_service.py#L112-L143)

```python
# 売却時
def _update_holding(transaction):
    if transaction.transaction_type == 'SELL':
        # 確定損益 = 売却金額 - (平均取得単価 × 売却数量)
        sell_proceeds_jpy = transaction.settlement_amount
        cost_basis_jpy = holding.average_cost * transaction.quantity
        realized_pnl = sell_proceeds_jpy - cost_basis_jpy

        # 確定損益率
        realized_pnl_pct = (realized_pnl / cost_basis) * 100
```

**計算式**:
```
確定損益 = 売却金額 - (平均取得単価 × 売却数量)
確定損益率 = (確定損益 / 取得コスト) × 100
```

### 3. 未実現損益の計算

**実装**: [holding.py:49-73](app/models/holding.py#L49-L73)

```python
def update_current_price(self, price, exchange_rate=1.0):
    self.current_price = price
    # 評価額 (円換算)
    self.current_value = (self.total_quantity * price) * exchange_rate

    # 未実現損益
    self.unrealized_pnl = self.current_value - self.total_cost

    # 未実現損益率
    self.unrealized_pnl_pct = (self.unrealized_pnl / self.total_cost) * 100
```

**計算式**:
```
現在評価額 = 保有数量 × 現在株価 × 為替レート
未実現損益 = 現在評価額 - 総取得コスト
未実現損益率 = (未実現損益 / 総取得コスト) × 100
```

### 4. パフォーマンス計算

**実装**: [performance_service.py](app/services/performance_service.py)

```python
# 総リターン = 確定損益 + 未実現損益 + 配当金
total_return = realized_pnl + unrealized_pnl + total_dividends

# リターン率 = 総リターン / 総投資額
return_rate = (total_return / total_invested) * 100
```

---

## API設計

### エンドポイント一覧

詳細は [API_REFERENCE.md](API_REFERENCE.md) を参照

#### 株価関連

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| GET | `/api/stock-price/<ticker>` | 株価取得 |
| POST | `/api/stock-price/update` | 株価更新 |

#### 保有銘柄関連

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| GET | `/api/holdings` | 保有銘柄一覧 |
| GET | `/api/holdings/<ticker>` | 銘柄詳細 |
| POST | `/api/holdings/<ticker>/recalculate` | 再計算 |

#### 取引履歴関連

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| GET | `/api/transactions` | 取引履歴一覧 |
| DELETE | `/api/transactions/<id>` | 取引削除 |

### レスポンス形式

**成功時**:
```json
{
  "success": true,
  "data": { ... }
}
```

**エラー時**:
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "エラーメッセージ"
  }
}
```

---

## テスト

### テストの実行

```bash
# 全テスト実行
pytest

# カバレッジ付き実行
pytest --cov=app --cov-report=html

# 特定のテストファイルのみ実行
pytest tests/test_models.py

# 特定のテスト関数のみ実行
pytest tests/test_models.py::test_transaction_creation

# 詳細な出力
pytest -v
```

### テスト構成

#### 1. モデルテスト ([test_models.py](../tests/test_models.py))

- データモデルのCRUD操作
- バリデーション
- リレーションシップ

```python
def test_transaction_creation(test_client):
    """取引作成テスト"""
    transaction = Transaction(
        transaction_date=date.today(),
        ticker_symbol='7203.T',
        transaction_type='BUY',
        quantity=100,
        unit_price=1000
    )
    db.session.add(transaction)
    db.session.commit()
    assert transaction.id is not None
```

#### 2. サービステスト ([test_services.py](../tests/test_services.py))

- ビジネスロジックのテスト
- 外部APIのモック

```python
@patch('yfinance.Ticker')
def test_stock_price_fetcher(mock_ticker):
    """株価取得テスト"""
    mock_ticker.return_value.history.return_value = mock_data

    price = StockPriceFetcher.get_current_price('7203.T')
    assert price is not None
```

#### 3. APIテスト ([test_api.py](../tests/test_api.py))

- エンドポイントのテスト
- レスポンス検証

```python
def test_get_holdings(test_client):
    """保有銘柄API取得テスト"""
    response = test_client.get('/api/holdings')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
```

### テストカバレッジ目標

- 全体: 80%以上
- ビジネスロジック (services): 90%以上
- モデル: 85%以上
- API: 80%以上

---

## コーディング規約

### Python コーディングスタイル

- **PEP 8準拠**: Python公式スタイルガイドに従う
- **命名規則**:
  - クラス: `PascalCase` (例: `TransactionService`)
  - 関数・変数: `snake_case` (例: `get_current_price`)
  - 定数: `UPPER_SNAKE_CASE` (例: `MAX_RETRY_COUNT`)
  - プライベート: 先頭アンダースコア (例: `_update_holding`)

### ドキュメント

```python
def calculate_realized_pnl(sell_price, quantity, average_cost):
    """
    確定損益を計算

    Args:
        sell_price (Decimal): 売却単価
        quantity (Decimal): 売却数量
        average_cost (Decimal): 平均取得単価

    Returns:
        Decimal: 確定損益

    Raises:
        ValueError: 数量が0以下の場合
    """
    if quantity <= 0:
        raise ValueError("数量は正の数である必要があります")

    return (sell_price - average_cost) * quantity
```

### エラーハンドリング

```python
from app.utils.errors import ValidationError, DatabaseError

try:
    result = process_transaction(data)
except ValueError as e:
    raise ValidationError(f"入力値エラー: {str(e)}")
except Exception as e:
    logger.error(f"予期しないエラー: {str(e)}")
    raise DatabaseError("処理中にエラーが発生しました")
```

### ロギング

```python
from app.utils.logger import get_logger

logger = get_logger('service_name')

logger.debug("デバッグ情報")
logger.info("情報メッセージ")
logger.warning("警告メッセージ")
logger.error("エラーメッセージ")
```

---

## デプロイ

### 本番環境の設定

1. **環境変数の設定**

```bash
# .envファイル
FLASK_ENV=production
SECRET_KEY=<強固なシークレットキー>
DATABASE_URL=sqlite:///data/stock_pnl.db
LOG_LEVEL=INFO
```

2. **シークレットキーの生成**

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

3. **Gunicorn での起動** (Linux/macOS)

```bash
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app('production')"
```

4. **Waitress での起動** (Windows)

```bash
waitress-serve --host 0.0.0.0 --port 8000 --call app:create_app
```

詳細は [DEPLOYMENT.md](DEPLOYMENT.md) を参照

---

## コントリビューション

### 開発フロー

1. **Issue作成**: 機能追加・バグ修正の内容を記述
2. **ブランチ作成**: `feature/機能名` または `bugfix/バグ名`
3. **実装**: コーディング規約に従って実装
4. **テスト**: 必ずテストを書く
5. **コミット**: 明確なコミットメッセージ
6. **Pull Request**: レビュー依頼

### ブランチ戦略

- `main`: 本番リリース可能な状態
- `develop`: 開発中の機能統合
- `feature/*`: 新機能開発
- `bugfix/*`: バグ修正
- `hotfix/*`: 緊急修正

### コミットメッセージ規約

```
<type>: <subject>

<body>

<footer>
```

**Type**:
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント
- `style`: フォーマット
- `refactor`: リファクタリング
- `test`: テスト追加
- `chore`: ビルド・設定変更

**例**:
```
feat: 配当データ自動取得機能を追加

Yahoo Finance APIを使用して、保有銘柄の配当データを
自動的に取得する機能を実装。

Closes #123
```

### Pull Request テンプレート

```markdown
## 変更内容
- 何を変更したか

## 変更理由
- なぜ変更したか

## テスト方法
- どうテストしたか

## チェックリスト
- [ ] テストが通る
- [ ] ドキュメント更新済み
- [ ] コーディング規約準拠
```

---

## 参考資料

### 公式ドキュメント

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [yfinance Documentation](https://pypi.org/project/yfinance/)

### プロジェクト内ドキュメント

- [API_REFERENCE.md](API_REFERENCE.md) - API仕様書
- [USER_GUIDE.md](USER_GUIDE.md) - ユーザーマニュアル
- [DEPLOYMENT.md](DEPLOYMENT.md) - デプロイガイド
- [FAQ.md](FAQ.md) - よくある質問

---

**最終更新**: 2026-01-11
**バージョン**: 1.0.0
**作成者**: Stock P&L Manager Development Team
