"""
カスタムエラークラスとエラーハンドラー
"""


class AppError(Exception):
    """アプリケーション基底エラークラス"""

    status_code = 500
    message = "内部サーバーエラーが発生しました"

    def __init__(self, message=None, status_code=None, payload=None):
        super().__init__()
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        """エラー情報を辞書形式で返す"""
        rv = {"success": False, "error": self.message}
        if self.payload:
            rv.update(self.payload)
        return rv


class ValidationError(AppError):
    """バリデーションエラー"""

    status_code = 400
    message = "入力データが正しくありません"


class NotFoundError(AppError):
    """リソースが見つからないエラー"""

    status_code = 404
    message = "リソースが見つかりません"


class DatabaseError(AppError):
    """データベースエラー"""

    status_code = 500
    message = "データベースエラーが発生しました"


class ExternalAPIError(AppError):
    """外部API呼び出しエラー"""

    status_code = 503
    message = "外部APIとの通信に失敗しました"


class DataConversionError(AppError):
    """データ変換エラー"""

    status_code = 500
    message = "データ変換処理に失敗しました"


def handle_app_error(error):
    """アプリケーションエラーハンドラー"""
    from flask import jsonify

    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def handle_generic_error(error):
    """一般的なエラーハンドラー"""
    from flask import jsonify
    import traceback

    # ログに詳細を記録（本番環境では適切なロギングシステムを使用）
    print(f"Unhandled error: {str(error)}")
    print(traceback.format_exc())

    response = jsonify({"success": False, "error": "予期しないエラーが発生しました"})
    response.status_code = 500
    return response


def handle_404_error(error):
    """404エラーハンドラー"""
    from flask import jsonify, request

    # APIリクエストの場合はJSONで返す
    if request.path.startswith("/api/"):
        response = jsonify({"success": False, "error": "リソースが見つかりません"})
        response.status_code = 404
        return response

    # それ以外は通常の404エラー
    return error


def handle_405_error(error):
    """405エラーハンドラー"""
    from flask import jsonify, request

    # APIリクエストの場合はJSONで返す
    if request.path.startswith("/api/"):
        response = jsonify(
            {"success": False, "error": "許可されていないHTTPメソッドです"}
        )
        response.status_code = 405
        return response

    # それ以外は通常の405エラー
    return error


def validate_required_fields(data, required_fields):
    """
    必須フィールドのバリデーション

    Args:
        data: チェックするデータ（辞書）
        required_fields: 必須フィールドのリスト

    Raises:
        ValidationError: 必須フィールドが不足している場合
    """
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)

    if missing_fields:
        raise ValidationError(
            message=f"必須フィールドが不足しています: {', '.join(missing_fields)}",
            payload={"missing_fields": missing_fields},
        )


def validate_positive_number(value, field_name):
    """
    正の数値のバリデーション

    Args:
        value: チェックする値
        field_name: フィールド名

    Raises:
        ValidationError: 値が正の数値でない場合
    """
    try:
        num = float(value)
        if num <= 0:
            raise ValidationError(
                message=f"{field_name}は正の数値である必要があります",
                payload={"field": field_name, "value": value},
            )
    except (TypeError, ValueError):
        raise ValidationError(
            message=f"{field_name}は数値である必要があります",
            payload={"field": field_name, "value": value},
        )


def validate_date_format(date_string, field_name):
    """
    日付フォーマットのバリデーション

    Args:
        date_string: チェックする日付文字列
        field_name: フィールド名

    Returns:
        datetime.date: パースされた日付

    Raises:
        ValidationError: 日付フォーマットが正しくない場合
    """
    from datetime import datetime

    try:
        return datetime.strptime(date_string, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValidationError(
            message=f"{field_name}の日付フォーマットが正しくありません (YYYY-MM-DD形式で指定してください)",
            payload={"field": field_name, "value": date_string},
        )


def validate_currency(currency):
    """
    通貨コードのバリデーション

    Args:
        currency: チェックする通貨コード

    Raises:
        ValidationError: 通貨コードが正しくない場合
    """
    valid_currencies = ["JPY", "USD", "KRW", "日本円"]

    if currency not in valid_currencies:
        raise ValidationError(
            message=f"サポートされていない通貨です: {currency}",
            payload={"currency": currency, "valid_currencies": valid_currencies},
        )


def validate_transaction_type(transaction_type):
    """
    取引タイプのバリデーション

    Args:
        transaction_type: チェックする取引タイプ

    Raises:
        ValidationError: 取引タイプが正しくない場合
    """
    valid_types = ["BUY", "SELL", "買付", "売却"]

    if transaction_type not in valid_types:
        raise ValidationError(
            message=f"サポートされていない取引タイプです: {transaction_type}",
            payload={"transaction_type": transaction_type, "valid_types": valid_types},
        )
