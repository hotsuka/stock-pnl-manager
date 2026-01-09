# エラーハンドリング実装ガイド

Stock P&L Managerのエラーハンドリング機能に関するドキュメント

## 概要

アプリケーション全体で一貫したエラー処理を実現するため、カスタムエラークラス、グローバルエラーハンドラー、ロギング機能を実装しています。

## カスタムエラークラス

### 基底クラス: `AppError`

すべてのカスタムエラーの基底クラス

```python
from app.utils.errors import AppError

raise AppError(
    message="エラーメッセージ",
    status_code=500,
    payload={'additional': 'data'}
)
```

### エラークラス一覧

| エラークラス | ステータスコード | 用途 |
|------------|----------------|------|
| `ValidationError` | 400 | バリデーションエラー（入力データの不正） |
| `NotFoundError` | 404 | リソースが見つからない |
| `DatabaseError` | 500 | データベース操作エラー |
| `ExternalAPIError` | 503 | 外部API呼び出しエラー |
| `DataConversionError` | 500 | データ変換エラー |

## バリデーション関数

### 必須フィールドの検証

```python
from app.utils.errors import validate_required_fields

data = {'name': 'Test', 'email': 'test@example.com'}
validate_required_fields(data, ['name', 'email', 'age'])
# 不足フィールドがある場合、ValidationErrorを発生
```

### 正の数値の検証

```python
from app.utils.errors import validate_positive_number

validate_positive_number(100, '金額')
# 0以下の値や無効な値の場合、ValidationErrorを発生
```

### 日付フォーマットの検証

```python
from app.utils.errors import validate_date_format

date_obj = validate_date_format('2024-01-15', '取引日')
# 無効な日付形式の場合、ValidationErrorを発生
```

### 通貨コードの検証

```python
from app.utils.errors import validate_currency

validate_currency('JPY')  # OK
validate_currency('EUR')  # ValidationErrorを発生
```

### 取引タイプの検証

```python
from app.utils.errors import validate_transaction_type

validate_transaction_type('BUY')   # OK
validate_transaction_type('SELL')  # OK
validate_transaction_type('買付')   # OK
validate_transaction_type('INVALID')  # ValidationErrorを発生
```

## APIエンドポイントでの使用例

### 基本的なエラーハンドリング

```python
from flask import Blueprint, jsonify, request
from app.utils.errors import ValidationError, NotFoundError
from app.utils.logger import get_logger, log_api_call

bp = Blueprint('api', __name__)
logger = get_logger('api')

@bp.route('/resource/<int:resource_id>', methods=['GET'])
def get_resource(resource_id):
    try:
        log_api_call(logger, '/resource/<id>', 'GET', {'id': resource_id})

        resource = Resource.query.get(resource_id)

        if not resource:
            raise NotFoundError(f'リソースが見つかりません (ID: {resource_id})')

        log_api_call(logger, '/resource/<id>', 'GET', response_code=200)
        return jsonify({
            'success': True,
            'data': resource.to_dict()
        })

    except (ValidationError, NotFoundError):
        raise  # グローバルハンドラーで処理
    except Exception as e:
        logger.error(f"予期しないエラー: {str(e)}")
        raise DatabaseError(f'データ取得に失敗しました: {str(e)}')
```

### バリデーション付きPOSTエンドポイント

```python
from app.utils.errors import validate_required_fields, validate_positive_number

@bp.route('/resource', methods=['POST'])
def create_resource():
    try:
        data = request.get_json()

        if not data:
            raise ValidationError("リクエストボディが空です")

        # 必須フィールドの検証
        validate_required_fields(data, ['name', 'amount'])

        # 金額の検証
        validate_positive_number(data['amount'], '金額')

        # リソース作成
        resource = Resource(**data)
        db.session.add(resource)
        db.session.commit()

        return jsonify({
            'success': True,
            'data': resource.to_dict()
        })

    except ValidationError:
        db.session.rollback()
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f"リソース作成エラー: {str(e)}")
        raise DatabaseError(f'リソースの作成に失敗しました: {str(e)}')
```

## ロギング機能

### ロガーの取得

```python
from app.utils.logger import get_logger

logger = get_logger('my_module')
logger.info("情報メッセージ")
logger.warning("警告メッセージ")
logger.error("エラーメッセージ")
```

### API呼び出しのロギング

```python
from app.utils.logger import log_api_call

# 成功時
log_api_call(logger, '/api/endpoint', 'GET', {'param': 'value'}, response_code=200)

# エラー時
log_api_call(logger, '/api/endpoint', 'POST', error='エラーメッセージ')
```

### データベース操作のロギング

```python
from app.utils.logger import log_database_operation

# 成功時
log_database_operation(logger, 'INSERT', 'transactions', 'AAPL - BUY')

# エラー時
log_database_operation(logger, 'UPDATE', 'holdings', error='更新失敗')
```

### 外部API呼び出しのロギング

```python
from app.utils.logger import log_external_api_call

# 成功時
log_external_api_call(logger, 'yfinance', 'get_price/AAPL', success=True)

# エラー時
log_external_api_call(logger, 'yfinance', 'get_price/AAPL', success=False, error='タイムアウト')
```

## サービス層での使用例

```python
from app.utils.logger import get_logger, log_database_operation
from app.utils.errors import DatabaseError

logger = get_logger('transaction_service')

class TransactionService:
    @staticmethod
    def save_transaction(data):
        try:
            logger.info(f"取引保存開始: {data.get('ticker_symbol')}")

            transaction = Transaction(**data)
            db.session.add(transaction)
            db.session.commit()

            log_database_operation(logger, 'INSERT', 'transactions',
                                   f"{data.get('ticker_symbol')} - {data.get('transaction_type')}")
            logger.info("取引保存完了")

            return transaction

        except Exception as e:
            db.session.rollback()
            logger.error(f"取引保存エラー: {str(e)}")
            log_database_operation(logger, 'INSERT', 'transactions', error=str(e))
            raise DatabaseError(f'取引の保存に失敗しました: {str(e)}')
```

## グローバルエラーハンドラー

アプリケーション起動時に自動的に登録されるグローバルエラーハンドラーにより、
すべてのカスタムエラーが適切なHTTPレスポンスに変換されます。

### レスポンス形式

```json
{
  "success": false,
  "error": "エラーメッセージ",
  "field": "フィールド名",  // オプション
  "missing_fields": ["field1", "field2"]  // オプション
}
```

## ログファイル

ログは`logs/`ディレクトリに日付別に保存されます:

- `logs/app_YYYYMMDD.log` - アプリケーション全体のログ
- `logs/api_YYYYMMDD.log` - APIエンドポイントのログ
- `logs/transaction_service_YYYYMMDD.log` - 取引サービスのログ
- `logs/stock_price_fetcher_YYYYMMDD.log` - 株価取得サービスのログ

### ログレベル

- `DEBUG`: 開発環境のみ、詳細なデバッグ情報
- `INFO`: 通常の動作情報
- `WARNING`: 警告（処理は継続）
- `ERROR`: エラー（処理失敗）

## テスト

エラーハンドリング機能のテストは`tests/test_error_handling.py`に実装されています:

```bash
# エラーハンドリングテストのみ実行
pytest tests/test_error_handling.py -v

# 全テスト実行
pytest
```

## ベストプラクティス

1. **適切なエラークラスの使用**
   - ユーザー入力エラー → `ValidationError`
   - データが見つからない → `NotFoundError`
   - データベースエラー → `DatabaseError`
   - 外部API失敗 → `ExternalAPIError`

2. **エラーメッセージは日本語で**
   - ユーザーフレンドリーなメッセージを使用
   - 技術的な詳細はログに記録

3. **ロギングの活用**
   - すべての重要な操作をログに記録
   - エラー発生時は詳細情報を記録

4. **トランザクション管理**
   - データベースエラー時は必ずロールバック
   - try-exceptブロックで適切に処理

5. **レスポンスの一貫性**
   - すべてのAPIレスポンスに`success`フィールドを含める
   - エラー時は`error`フィールドにメッセージを設定

## まとめ

このエラーハンドリング実装により:
- ✅ 一貫したエラーレスポンス形式
- ✅ 詳細なログ記録
- ✅ ユーザーフレンドリーなエラーメッセージ
- ✅ 適切なHTTPステータスコード
- ✅ デバッグと問題解決の容易化

が実現されています。
