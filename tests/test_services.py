"""
サービス層のユニットテスト
"""

import pytest
from datetime import date
from decimal import Decimal
from app.models import Transaction, Holding, RealizedPnl
from app.services.transaction_service import TransactionService


class TestTransactionService:
    """TransactionServiceのテスト"""

    def test_calculate_average_cost_single_transaction(self, db_session):
        """単一取引の平均取得単価計算テスト"""
        transaction = Transaction(
            transaction_date=date(2024, 1, 10),
            ticker_symbol="7203",
            security_name="トヨタ自動車",
            transaction_type="BUY",
            quantity=100,
            unit_price=2500.0,
            currency="JPY",
            commission=100.0,
            settlement_amount=250100.0,
        )

        db_session.add(transaction)
        db_session.commit()

        # 保有銘柄の再計算
        TransactionService.recalculate_holding("7203")

        # 検証
        holding = Holding.query.filter_by(ticker_symbol="7203").first()
        assert holding is not None
        assert holding.total_quantity == 100
        assert float(holding.total_cost) == 250100.0
        assert abs(float(holding.average_cost) - 2501.0) < 0.01

    def test_calculate_average_cost_multiple_buys(self, db_session):
        """複数回買付の平均取得単価計算テスト（加重平均）"""
        transactions = [
            Transaction(
                transaction_date=date(2024, 1, 10),
                ticker_symbol="1475",
                security_name="iシェアーズ TOPIXコアETF",
                transaction_type="BUY",
                quantity=100,
                unit_price=2000.0,
                currency="JPY",
                commission=100.0,
                settlement_amount=200100.0,
            ),
            Transaction(
                transaction_date=date(2024, 2, 15),
                ticker_symbol="1475",
                security_name="iシェアーズ TOPIXコアETF",
                transaction_type="BUY",
                quantity=50,
                unit_price=2200.0,
                currency="JPY",
                commission=50.0,
                settlement_amount=110050.0,
            ),
        ]

        for t in transactions:
            db_session.add(t)
        db_session.commit()

        TransactionService.recalculate_holding("1475")

        holding = Holding.query.filter_by(ticker_symbol="1475").first()
        assert holding is not None
        assert holding.total_quantity == 150
        # 総コスト = 200,100 + 110,050 = 310,150
        assert abs(float(holding.total_cost) - 310150.0) < 0.01
        # 平均単価 = 310,150 / 150 = 2,067.67
        assert abs(float(holding.average_cost) - 2067.67) < 0.01

    def test_sell_transaction_reduces_holding(self, db_session):
        """売却取引で保有数量が減少することをテスト"""
        # 買付
        buy = Transaction(
            transaction_date=date(2024, 1, 10),
            ticker_symbol="AAPL",
            security_name="Apple Inc.",
            transaction_type="BUY",
            quantity=100,
            unit_price=150.0,
            currency="USD",
            commission=10.0,
            settlement_amount=2251510.0,
        )
        db_session.add(buy)
        db_session.commit()

        TransactionService.recalculate_holding("AAPL")

        # 売却前の保有数
        holding_before = Holding.query.filter_by(ticker_symbol="AAPL").first()
        assert holding_before.total_quantity == 100

        # 売却
        sell = Transaction(
            transaction_date=date(2024, 2, 15),
            ticker_symbol="AAPL",
            security_name="Apple Inc.",
            transaction_type="SELL",
            quantity=30,
            unit_price=160.0,
            currency="USD",
            commission=5.0,
            settlement_amount=720000.0,
        )
        db_session.add(sell)
        db_session.commit()

        TransactionService.recalculate_holding("AAPL")

        # 売却後の保有数
        holding_after = Holding.query.filter_by(ticker_symbol="AAPL").first()
        assert holding_after.total_quantity == 70

    def test_sell_all_creates_realized_pnl(self, db_session):
        """全売却で実現損益が記録されることをテスト"""
        # 買付
        buy = Transaction(
            transaction_date=date(2024, 1, 10),
            ticker_symbol="9984",
            security_name="ソフトバンクグループ",
            transaction_type="BUY",
            quantity=100,
            unit_price=5000.0,
            currency="JPY",
            commission=500.0,
            settlement_amount=500500.0,
        )
        db_session.add(buy)
        db_session.commit()

        TransactionService.recalculate_holding("9984")

        # 全売却
        sell = Transaction(
            transaction_date=date(2024, 3, 20),
            ticker_symbol="9984",
            security_name="ソフトバンクグループ",
            transaction_type="SELL",
            quantity=100,
            unit_price=5500.0,
            currency="JPY",
            commission=300.0,
            settlement_amount=549700.0,
        )
        db_session.add(sell)
        db_session.commit()

        TransactionService.recalculate_holding("9984")

        # 保有銘柄が削除されていることを確認
        holding = Holding.query.filter_by(ticker_symbol="9984").first()
        assert holding is None

        # 実現損益が記録されていることを確認
        realized = RealizedPnl.query.filter_by(ticker_symbol="9984").first()
        assert realized is not None
        assert realized.quantity == 100
        # 実現損益 = 売却額 - 取得コスト = 549,700 - 500,500 = 49,200
        assert abs(float(realized.realized_pnl) - 49200.0) < 0.01

    def test_partial_sell_updates_average_cost(self, db_session):
        """部分売却で平均取得単価が維持されることをテスト"""
        # 買付
        buy = Transaction(
            transaction_date=date(2024, 1, 10),
            ticker_symbol="8306",
            security_name="三菱UFJフィナンシャル・グループ",
            transaction_type="BUY",
            quantity=500,
            unit_price=1000.0,
            currency="JPY",
            commission=500.0,
            settlement_amount=500500.0,
        )
        db_session.add(buy)
        db_session.commit()

        TransactionService.recalculate_holding("8306")

        holding_before = Holding.query.filter_by(ticker_symbol="8306").first()
        avg_cost_before = holding_before.average_cost

        # 部分売却
        sell = Transaction(
            transaction_date=date(2024, 2, 15),
            ticker_symbol="8306",
            security_name="三菱UFJフィナンシャル・グループ",
            transaction_type="SELL",
            quantity=200,
            unit_price=1100.0,
            currency="JPY",
            commission=200.0,
            settlement_amount=219800.0,
        )
        db_session.add(sell)
        db_session.commit()

        TransactionService.recalculate_holding("8306")

        # 平均取得単価は変わらない
        holding_after = Holding.query.filter_by(ticker_symbol="8306").first()
        assert holding_after.total_quantity == 300
        # 平均単価は売却前と同じ
        assert abs(float(holding_after.average_cost) - float(avg_cost_before)) < 0.01

    def test_recalculate_multiple_transactions(self, db_session, sample_transactions):
        """複数取引がある場合の再計算テスト"""
        TransactionService.recalculate_holding("1475")

        holding = Holding.query.filter_by(ticker_symbol="1475").first()
        assert holding is not None
        # 買付100 - 売却50 = 50
        assert holding.total_quantity == 50

        # 実現損益も記録されている
        realized = RealizedPnl.query.filter_by(ticker_symbol="1475").first()
        assert realized is not None
        assert realized.quantity == 50

    def test_currency_handling(self, db_session):
        """通貨の正しい扱いをテスト"""
        # USD建て取引
        transaction = Transaction(
            transaction_date=date(2024, 1, 10),
            ticker_symbol="GOOGL",
            security_name="Alphabet Inc.",
            transaction_type="BUY",
            quantity=10,
            unit_price=140.0,
            currency="USD",
            commission=5.0,
            settlement_amount=210005.0,
        )

        db_session.add(transaction)
        db_session.commit()

        TransactionService.recalculate_holding("GOOGL")

        holding = Holding.query.filter_by(ticker_symbol="GOOGL").first()
        assert holding is not None
        assert holding.currency == "USD"
        assert holding.total_quantity == 10
        # 平均単価 = (140 * 10 + 5) / 10 = 140.5 USD
        # ただし、settlement_amountはJPY建てなので、実際の計算はDB側で行われる
        assert float(holding.total_cost) == 210005.0

    def test_empty_ticker_returns_none(self, db_session):
        """存在しない銘柄の再計算"""
        # 存在しない銘柄を再計算してもエラーにならない
        TransactionService.recalculate_holding("NONEXIST")

        holding = Holding.query.filter_by(ticker_symbol="NONEXIST").first()
        assert holding is None
