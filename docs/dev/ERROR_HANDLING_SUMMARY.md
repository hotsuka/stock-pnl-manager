# エラーハンドリング強化 - 実装サマリー

## 実装日

2026-01-09

## 概要

Stock P&L Managerアプリケーション全体のエラーハンドリングを強化し、以下を実現しました:

- ✅ 一貫したエラーレスポンス形式
- ✅ カスタムエラークラスによる適切なエラー分類
- ✅ グローバルエラーハンドラーによる統一的なエラー処理
- ✅ 包括的なロギング機能
- ✅ 詳細なバリデーション機能
- ✅ ユーザーフレンドリーな日本語エラーメッセージ

## 実装内容

### 1. カスタムエラークラス (`app/utils/errors.py`)

**実装したエラークラス:**

| クラス名 | ステータスコード | 用途 |
|---------|----------------|------|
| `AppError` | 500 | 基底エラークラス |
| `ValidationError` | 400 | バリデーションエラー |
| `NotFoundError` | 404 | リソースが見つからない |
| `DatabaseError` | 500 | データベース操作エラー |
| `ExternalAPIError` | 503 | 外部API呼び出しエラー |
| `DataConversionError` | 500 | データ変換エラー |

**バリデーション関数:**

- `validate_required_fields()` - 必須フィールドの検証
- `validate_positive_number()` - 正の数値の検証
- `validate_date_format()` - 日付フォーマットの検証
- `validate_currency()` - 通貨コードの検証
- `validate_transaction_type()` - 取引タイプの検証

### 2. ロギング機能 (`app/utils/logger.py`)

**主要機能:**

- 日付別ログファイル管理 (`logs/`)
- 複数のロガーサポート (api, transaction_service, stock_price_fetcher等)
- ログレベル別出力 (DEBUG, INFO, WARNING, ERROR)
- 構造化ロギング関数:
  - `log_api_call()` - API呼び出しのログ記録
  - `log_database_operation()` - データベース操作のログ記録
  - `log_external_api_call()` - 外部API呼び出しのログ記録

### 3. グローバルエラーハンドラー (`app/__init__.py`)

**実装内容:**

- すべてのカスタムエラーを自動的にJSONレスポンスに変換
- 予期しないエラーの捕捉と適切な500エラーレスポンス
- エラー詳細の自動ログ記録

### 4. APIエンドポイントの強化 (`app/routes/api.py`)

**強化したエンドポイント:**

1. `/api/stock-price/<ticker>` - 株価取得
   - ティッカーシンボルのバリデーション
   - エラーハンドリングとロギング追加

2. `/api/stock-price/update-all` - 株価一括更新
   - エラーハンドリングとロギング追加

3. `/api/exchange-rate/convert` - 通貨変換
   - 必須フィールドのバリデーション
   - 金額の正の数値チェック
   - 詳細なエラーメッセージ

4. `/api/transactions/<id>` - 取引更新
   - 全フィールドのバリデーション
   - 通貨・取引タイプの検証
   - 日付フォーマットの検証
   - データベースロールバック処理

5. `/api/holdings/<ticker>` - 保有銘柄取得
   - NotFoundエラーハンドリング
   - 日本語エラーメッセージ

### 5. サービス層の強化

**`app/services/stock_price_fetcher.py`:**
- 株価取得エラーの詳細ログ記録
- 外部API呼び出しのログ記録
- フォールバック処理時の警告ログ

**`app/services/transaction_service.py`:**
- 取引保存処理の開始/完了ログ
- 重複取引の警告ログ
- データベース操作のログ記録
- エラー時の詳細情報ログ

### 6. テスト (`tests/test_error_handling.py`)

**テスト内容:**

- カスタムエラークラスのテスト (5テスト)
- バリデーション関数のテスト (13テスト)
- APIエンドポイントのエラーハンドリングテスト (6テスト)

**テスト結果:**
```
24 passed, 0 failed
```

## ファイル構成

```
app/
├── utils/
│   ├── __init__.py          # ユーティリティのエクスポート
│   ├── errors.py            # カスタムエラークラスとバリデーション
│   └── logger.py            # ロギング機能
├── routes/
│   └── api.py               # 強化されたAPIエンドポイント
├── services/
│   ├── stock_price_fetcher.py  # ロギング追加
│   └── transaction_service.py  # ロギング追加
└── __init__.py              # グローバルエラーハンドラー登録

tests/
└── test_error_handling.py   # エラーハンドリングテスト

logs/                         # ログファイルディレクトリ (自動生成)
├── app_YYYYMMDD.log
├── api_YYYYMMDD.log
├── transaction_service_YYYYMMDD.log
└── stock_price_fetcher_YYYYMMDD.log

ERROR_HANDLING.md            # 詳細ドキュメント
ERROR_HANDLING_SUMMARY.md    # このファイル
```

## エラーレスポンス形式

### 成功時
```json
{
  "success": true,
  "data": { ... }
}
```

### エラー時
```json
{
  "success": false,
  "error": "エラーメッセージ (日本語)",
  "field": "フィールド名",  // オプション
  "missing_fields": ["field1", "field2"]  // オプション
}
```

## ログ出力例

### APIログ
```
2026-01-09 14:30:15 - api - INFO - GET /api/stock-price/<ticker> - Params: {'ticker': 'AAPL'}
2026-01-09 14:30:16 - stock_price_fetcher - INFO - 株価取得成功: AAPL = 150.25 USD
2026-01-09 14:30:16 - api - INFO - GET /api/stock-price/<ticker> - Response: 200
```

### エラーログ
```
2026-01-09 14:35:20 - api - ERROR - 株価取得エラー (INVALID): Ticker not found
2026-01-09 14:35:20 - stock_price_fetcher - ERROR - External API call to yfinance - get_price/INVALID - FAILED - Ticker not found
```

### データベースログ
```
2026-01-09 14:40:10 - transaction_service - INFO - 取引データ保存開始: 5件
2026-01-09 14:40:11 - transaction_service - INFO - Database INSERT on transactions - AAPL - BUY
2026-01-09 14:40:11 - transaction_service - INFO - 取引データ保存完了: 成功=5, 失敗=0
```

## 改善効果

### 1. エラートラッキングの向上
- すべてのエラーがログファイルに記録される
- エラー発生時のコンテキスト情報が保存される
- デバッグ時間の短縮

### 2. ユーザーエクスペリエンスの向上
- 日本語のエラーメッセージ
- 具体的な修正方法の提示
- 一貫したエラーレスポンス形式

### 3. 開発効率の向上
- エラーハンドリングコードの再利用
- バリデーション関数の統一
- テストカバレッジの向上

### 4. 運用性の向上
- 問題の早期発見
- エラー傾向の分析が容易
- 監視・アラートの基盤

## 使用方法

### バリデーション付きAPIエンドポイント例

```python
from app.utils.errors import validate_required_fields, ValidationError
from app.utils.logger import get_logger, log_api_call

logger = get_logger('my_api')

@bp.route('/resource', methods=['POST'])
def create_resource():
    try:
        log_api_call(logger, '/resource', 'POST')

        data = request.get_json()
        validate_required_fields(data, ['name', 'amount'])

        # 処理...

        log_api_call(logger, '/resource', 'POST', response_code=200)
        return jsonify({'success': True, 'data': result})

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"エラー: {str(e)}")
        raise DatabaseError(f"処理失敗: {str(e)}")
```

## 今後の拡張案

1. **メトリクス収集**
   - エラー発生頻度の統計
   - レスポンスタイムの測定
   - API呼び出し数の追跡

2. **アラート機能**
   - 重大エラーの自動通知
   - エラー率の監視
   - 異常検知

3. **エラーレポート**
   - 日次/週次エラーサマリー
   - エラー傾向分析
   - ダッシュボード連携

4. **より詳細なバリデーション**
   - カスタムバリデータの追加
   - 複雑なビジネスルールの検証
   - クロスフィールドバリデーション

## 参照ドキュメント

- 詳細ガイド: [ERROR_HANDLING.md](ERROR_HANDLING.md)
- テストコード: [tests/test_error_handling.py](tests/test_error_handling.py)
- README: [README.md](README.md)

## まとめ

このエラーハンドリング強化により、Stock P&L Managerアプリケーションは:

✅ **堅牢性**: 適切なエラー処理による安定動作
✅ **保守性**: 統一されたエラー処理パターン
✅ **運用性**: 詳細なログによる問題解決の容易化
✅ **ユーザビリティ**: 分かりやすい日本語エラーメッセージ

を実現しました。
