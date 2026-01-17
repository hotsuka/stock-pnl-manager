"""
エラーハンドリングのテスト
"""

from datetime import date

import pytest

from app.utils.errors import (
    DatabaseError,
    ExternalAPIError,
    NotFoundError,
    ValidationError,
    validate_currency,
    validate_date_format,
    validate_positive_number,
    validate_required_fields,
    validate_transaction_type,
)


class TestValidationErrors:
    """バリデーションエラーのテスト"""

    def test_validation_error_basic(self):
        """基本的なValidationErrorのテスト"""
        error = ValidationError("テストエラー")
        assert error.status_code == 400
        assert error.message == "テストエラー"

        error_dict = error.to_dict()
        assert error_dict["success"] is False
        assert error_dict["error"] == "テストエラー"

    def test_validation_error_with_payload(self):
        """ペイロード付きValidationErrorのテスト"""
        error = ValidationError(
            message="必須フィールドが不足しています",
            payload={"missing_fields": ["name", "email"]},
        )

        error_dict = error.to_dict()
        assert error_dict["missing_fields"] == ["name", "email"]


class TestNotFoundError:
    """NotFoundErrorのテスト"""

    def test_not_found_error(self):
        """NotFoundErrorのテスト"""
        error = NotFoundError("リソースが見つかりません")
        assert error.status_code == 404
        assert error.message == "リソースが見つかりません"


class TestDatabaseError:
    """DatabaseErrorのテスト"""

    def test_database_error(self):
        """DatabaseErrorのテスト"""
        error = DatabaseError("データベースエラー")
        assert error.status_code == 500
        assert error.message == "データベースエラー"


class TestExternalAPIError:
    """ExternalAPIErrorのテスト"""

    def test_external_api_error(self):
        """ExternalAPIErrorのテスト"""
        error = ExternalAPIError("外部APIエラー")
        assert error.status_code == 503
        assert error.message == "外部APIエラー"


class TestValidationFunctions:
    """バリデーション関数のテスト"""

    def test_validate_required_fields_success(self):
        """必須フィールドバリデーション成功"""
        data = {"name": "Test", "email": "test@example.com"}
        # エラーが発生しなければ成功
        validate_required_fields(data, ["name", "email"])

    def test_validate_required_fields_failure(self):
        """必須フィールドバリデーション失敗"""
        data = {"name": "Test"}
        with pytest.raises(ValidationError) as exc_info:
            validate_required_fields(data, ["name", "email"])

        assert "email" in str(exc_info.value.payload["missing_fields"])

    def test_validate_positive_number_success(self):
        """正の数値バリデーション成功"""
        validate_positive_number(100, "金額")
        validate_positive_number(0.01, "金額")
        validate_positive_number("123.45", "金額")

    def test_validate_positive_number_failure_zero(self):
        """正の数値バリデーション失敗（ゼロ）"""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_number(0, "金額")

        assert "正の数値である必要があります" in str(exc_info.value.message)

    def test_validate_positive_number_failure_negative(self):
        """正の数値バリデーション失敗（負の数）"""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_number(-100, "金額")

        assert "正の数値である必要があります" in str(exc_info.value.message)

    def test_validate_positive_number_failure_invalid(self):
        """正の数値バリデーション失敗（無効な値）"""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_number("invalid", "金額")

        assert "数値である必要があります" in str(exc_info.value.message)

    def test_validate_date_format_success(self):
        """日付フォーマットバリデーション成功"""
        result = validate_date_format("2024-01-15", "取引日")
        assert result == date(2024, 1, 15)

    def test_validate_date_format_failure(self):
        """日付フォーマットバリデーション失敗"""
        with pytest.raises(ValidationError) as exc_info:
            validate_date_format("2024/01/15", "取引日")

        assert "YYYY-MM-DD形式で指定してください" in str(exc_info.value.message)

    def test_validate_date_format_failure_invalid(self):
        """日付フォーマットバリデーション失敗（無効な日付）"""
        with pytest.raises(ValidationError):
            validate_date_format("invalid-date", "取引日")

    def test_validate_currency_success(self):
        """通貨バリデーション成功"""
        validate_currency("JPY")
        validate_currency("USD")
        validate_currency("KRW")
        validate_currency("日本円")

    def test_validate_currency_failure(self):
        """通貨バリデーション失敗"""
        with pytest.raises(ValidationError) as exc_info:
            validate_currency("EUR")

        assert "サポートされていない通貨です" in str(exc_info.value.message)
        assert exc_info.value.payload["currency"] == "EUR"

    def test_validate_transaction_type_success(self):
        """取引タイプバリデーション成功"""
        validate_transaction_type("BUY")
        validate_transaction_type("SELL")
        validate_transaction_type("買付")
        validate_transaction_type("売却")

    def test_validate_transaction_type_failure(self):
        """取引タイプバリデーション失敗"""
        with pytest.raises(ValidationError) as exc_info:
            validate_transaction_type("INVALID")

        assert "サポートされていない取引タイプです" in str(exc_info.value.message)
        assert exc_info.value.payload["transaction_type"] == "INVALID"


class TestAPIErrorHandling:
    """APIエラーハンドリングのテスト"""

    def test_stock_price_not_found(self, client):
        """存在しない銘柄の株価取得エラー"""
        response = client.get("/api/stock-price/INVALID_TICKER")
        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "error" in data

    def test_exchange_rate_convert_missing_params(self, client):
        """通貨変換APIのパラメータ不足エラー"""
        response = client.post(
            "/api/exchange-rate/convert", json={"amount": 100}
        )  # 'from' パラメータが不足
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "from" in str(data["error"])

    def test_exchange_rate_convert_invalid_amount(self, client):
        """通貨変換APIの無効な金額エラー"""
        response = client.post(
            "/api/exchange-rate/convert", json={"amount": -100, "from": "USD"}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_transaction_update_not_found(self, client):
        """存在しない取引の更新エラー"""
        response = client.put("/api/transactions/99999", json={"quantity": 100})
        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "見つかりません" in data["error"]

    def test_transaction_update_invalid_data(
        self, client, db_session, sample_transactions
    ):
        """無効なデータでの取引更新エラー"""
        # 最初の取引を使用
        transaction = sample_transactions[0]
        db_session.add(transaction)
        db_session.commit()

        response = client.put(
            f"/api/transactions/{transaction.id}", json={"quantity": -100}
        )  # 負の数量は無効
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_holding_not_found(self, client):
        """存在しない保有銘柄の取得エラー"""
        response = client.get("/api/holdings/INVALID_TICKER")
        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "見つかりません" in data["error"]
