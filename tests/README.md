# テストスイート

## 概要

このディレクトリには、Stock P&L Managerのユニットテストと統合テストが含まれています。

## テストファイル構成

```
tests/
├── __init__.py               # パッケージ初期化ファイル
├── conftest.py              # pytestフィクスチャ定義
├── test_models.py           # モデルのユニットテスト
├── test_services.py         # サービス層のユニットテスト
├── test_api.py              # APIエンドポイントの統合テスト
└── README.md                # このファイル
```

## テストの実行

### Windows
```bash
run_tests.bat
```

または

```bash
python -m pytest
```

### Unix/Linux/Mac
```bash
./run_tests.sh
```

または

```bash
python -m pytest
```

### 特定のテストファイルのみ実行
```bash
pytest tests/test_models.py
pytest tests/test_services.py
pytest tests/test_api.py
```

### カバレッジレポート付きで実行
```bash
pytest --cov=app --cov-report=html
```

カバレッジレポートは `htmlcov/index.html` で確認できます。

## テストカテゴリ

### 1. モデルのテスト (`test_models.py`)

- **Transaction（取引）モデル**
  - 作成、読取、更新、削除（CRUD操作）
  - クエリ機能

- **Holding（保有銘柄）モデル**
  - CRUD操作
  - 損益計算の検証

- **RealizedPnl（実現損益）モデル**
  - CRUD操作
  - 損益率の計算

- **Dividend（配当）モデル**
  - CRUD操作
  - 配当金計算の検証

### 2. サービス層のテスト (`test_services.py`)

- **TransactionService**
  - 平均取得単価の計算（加重平均）
  - 複数回買付の処理
  - 売却処理と保有数量の減少
  - 全売却時の実現損益記録
  - 部分売却の処理
  - 通貨の正しい扱い

### 3. APIエンドポイントのテスト (`test_api.py`)

- **保有銘柄API** (`/api/holdings`)
- **取引履歴API** (`/api/transactions`)
- **実現損益API** (`/api/realized-pnl`)
- **配当金API** (`/api/dividends`)
- **ダッシュボードAPI** (`/api/dashboard/*`)
- **損益推移API** (`/api/performance/*`)
- **エラーハンドリング**

## 既知の問題

### モデルフィールド名の不一致

テストファイルで使用しているフィールド名と実際のモデルで定義されているフィールド名に不一致があります：

#### Transaction モデル
- テスト: `price` → 実際: `unit_price` ✅ 修正必要

#### RealizedPnl モデル
- テスト: `total_quantity_sold` → 実際: `quantity`
- テスト: `average_sell_price` → 実際: `sell_price`
- テスト: `total_cost` → 実際: フィールドなし（削除必要）
- テスト: `total_proceeds` → 実際: フィールドなし（削除必要）

### 修正が必要な箇所

1. **conftest.py**
   - sample_realized_pnlフィクスチャのフィールド名を修正

2. **test_models.py**
   - Transactionテストでの`saved.price`を`saved.unit_price`に修正
   - RealizedPnlテストのフィールド名を修正
   - Holdingテストの`current_unit_price`を`current_price`に修正

3. **test_services.py**
   - すべての`price`を`unit_price`に修正

## テスト環境

- **Python**: 3.14+
- **テストフレームワーク**: pytest 7.4.3+
- **カバレッジツール**: pytest-cov 4.1.0+
- **データベース**: SQLite (メモリ内データベース)

## テスト設定

テスト用の設定は `config.py` の `TestingConfig` クラスで定義されています：

```python
class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
```

## 今後の改善点

1. ✅ テストフィクスチャのフィールド名を実際のモデルに合わせる
2. ⬜ yfinanceなど外部APIのモック化
3. ⬜ パフォーマンステストの追加
4. ⬜ エンドツーエンド（E2E）テストの追加
5. ⬜ CI/CDパイプラインへの統合
6. ⬜ テストカバレッジを80%以上に向上

## トラブルシューティング

### テストが失敗する場合

1. 仮想環境がアクティベートされているか確認
2. 依存パッケージがインストールされているか確認: `pip install -r requirements.txt`
3. データベースマイグレーションが最新か確認
4. pytest.iniの設定を確認

### カバレッジレポートが生成されない場合

```bash
pip install pytest-cov
pytest --cov=app --cov-report=html --cov-report=term-missing
```
