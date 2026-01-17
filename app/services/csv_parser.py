import csv
import chardet
from datetime import datetime
from decimal import Decimal, InvalidOperation


class CSVParser:
    """SBI証券CSV解析クラス"""

    # SBI証券CSVカラムマッピング（日本語・英語両対応）
    COLUMN_MAPPING = {
        # 日本語ヘッダー
        "約定日": "transaction_date",
        "銘柄コード": "ticker_symbol",
        "ティッカーシンボル": "ticker_symbol",
        "銘柄名": "security_name",
        "取引": "transaction_type",
        "数量": "quantity",
        "単価": "unit_price",
        "約定単価": "unit_price",
        "手数料": "commission",
        "受渡金額": "settlement_amount",
        "通貨": "currency",
        "為替レート": "exchange_rate",
        # 英語ヘッダー
        "transaction_date": "transaction_date",
        "ticker_symbol": "ticker_symbol",
        "ticker": "ticker_symbol",
        "security_name": "security_name",
        "name": "security_name",
        "transaction_type": "transaction_type",
        "type": "transaction_type",
        "quantity": "quantity",
        "qty": "quantity",
        "unit_price": "unit_price",
        "price": "unit_price",
        "commission": "commission",
        "fee": "commission",
        "settlement_amount": "settlement_amount",
        "amount": "settlement_amount",
        "currency": "currency",
        "exchange_rate": "exchange_rate",
    }

    # 取引タイプマッピング
    TRANSACTION_TYPE_MAPPING = {"買付": "BUY", "買": "BUY", "BUY": "BUY", "売却": "SELL", "売": "SELL", "SELL": "SELL"}

    @staticmethod
    def detect_encoding(file_path):
        """文字コードを自動判定"""
        with open(file_path, "rb") as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            return result["encoding"]

    @staticmethod
    def parse_date(date_str):
        """日付文字列を解析"""
        if not date_str:
            return None

        # 複数の日付フォーマットに対応
        date_formats = ["%Y/%m/%d", "%Y-%m-%d", "%Y年%m月%d日", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        raise ValueError(f"無効な日付形式: {date_str}")

    @staticmethod
    def parse_number(num_str):
        """数値文字列を解析（カンマ除去対応）"""
        if not num_str or num_str.strip() == "":
            return None

        try:
            # カンマを除去
            cleaned = num_str.strip().replace(",", "")
            return Decimal(cleaned)
        except (ValueError, InvalidOperation):
            raise ValueError(f"無効な数値形式: {num_str}")

    @classmethod
    def parse_csv(cls, file_path):
        """
        CSVファイルを解析

        Returns:
            list: 解析された取引データのリスト
            list: エラーメッセージのリスト
        """
        # 文字コード判定
        encoding = cls.detect_encoding(file_path)

        transactions = []
        errors = []

        with open(file_path, "r", encoding=encoding) as f:
            # CSVリーダー
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):  # ヘッダー行をスキップ
                try:
                    transaction = cls._parse_row(row)
                    if transaction:
                        transactions.append(transaction)
                except Exception as e:
                    errors.append({"row": row_num, "error": str(e), "data": row})

        return transactions, errors

    @classmethod
    def _parse_row(cls, row):
        """CSV行を解析して取引データに変換"""
        # カラム名を正規化
        normalized_row = {}
        for key, value in row.items():
            if key in cls.COLUMN_MAPPING:
                normalized_row[cls.COLUMN_MAPPING[key]] = value

        # 必須項目チェック
        required_fields = ["transaction_date", "ticker_symbol", "transaction_type", "quantity", "unit_price"]

        for field in required_fields:
            if field not in normalized_row or not normalized_row[field]:
                raise ValueError(f"必須項目が不足: {field}")

        # ティッカーシンボルを正規化
        ticker_symbol = normalized_row["ticker_symbol"].strip().upper()

        # 通貨を判定（CSVに通貨カラムがあればそれを使用、なければティッカーから推測）
        if "currency" in normalized_row and normalized_row["currency"]:
            currency = normalized_row["currency"].strip().upper()
        else:
            currency = cls._detect_currency_from_ticker(ticker_symbol)

        # データ変換
        transaction_data = {
            "transaction_date": cls.parse_date(normalized_row["transaction_date"]),
            "ticker_symbol": ticker_symbol,
            "security_name": normalized_row.get("security_name", "").strip(),
            "transaction_type": cls._parse_transaction_type(normalized_row["transaction_type"]),
            "quantity": cls.parse_number(normalized_row["quantity"]),
            "unit_price": cls.parse_number(normalized_row["unit_price"]),
            "commission": cls.parse_number(normalized_row.get("commission", "0")),
            "settlement_amount": cls.parse_number(normalized_row.get("settlement_amount")),
            "currency": currency,
            "exchange_rate": cls.parse_number(normalized_row.get("exchange_rate")),
            "settlement_currency": currency,
        }

        # バリデーション
        cls._validate_transaction(transaction_data)

        return transaction_data

    @staticmethod
    def _detect_currency_from_ticker(ticker_symbol):
        """
        ティッカーシンボルから通貨を推測

        Args:
            ticker_symbol: ティッカーシンボル (e.g., 'AAPL', '7203.T', '6498.T')

        Returns:
            str: 通貨コード ('USD', 'JPY', etc.)
        """
        ticker_upper = ticker_symbol.upper()

        # 日本株の判定
        # 1. .T サフィックスがある
        # 2. 数字のみ（4桁または5桁）
        if ticker_upper.endswith(".T") or ticker_upper.replace(".", "").isdigit():
            return "JPY"

        # 韓国株の判定 (.KS, .KQ サフィックス)
        if ticker_upper.endswith(".KS") or ticker_upper.endswith(".KQ"):
            return "KRW"

        # 香港株の判定 (.HK サフィックス)
        if ticker_upper.endswith(".HK"):
            return "HKD"

        # 英国株の判定 (.L サフィックス)
        if ticker_upper.endswith(".L"):
            return "GBP"

        # その他はデフォルトでUSD（米国株）
        return "USD"

    @classmethod
    def _parse_transaction_type(cls, type_str):
        """取引タイプを解析"""
        type_str = type_str.strip()
        if type_str in cls.TRANSACTION_TYPE_MAPPING:
            return cls.TRANSACTION_TYPE_MAPPING[type_str]
        raise ValueError(f"無効な取引タイプ: {type_str}")

    @staticmethod
    def _validate_transaction(data):
        """取引データのバリデーション"""
        # 数量チェック
        if data["quantity"] <= 0:
            raise ValueError("数量は正の数である必要があります")

        # 単価チェック
        if data["unit_price"] <= 0:
            raise ValueError("単価は正の数である必要があります")

        # 手数料チェック
        if data["commission"] < 0:
            raise ValueError("手数料は0以上である必要があります")

        return True
