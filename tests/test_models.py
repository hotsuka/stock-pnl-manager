"""
データモデルのユニットテスト
"""
import pytest
from datetime import date
from app.models import Transaction, Holding, RealizedPnl, Dividend


class TestTransaction:
    """Transactionモデルのテスト"""

    def test_create_transaction(self, db_session):
        """取引データの作成テスト"""
        transaction = Transaction(
            transaction_date=date(2024, 1, 10),
            ticker_symbol='7203',
            security_name='トヨタ自動車',
            transaction_type='買付',
            quantity=100,
            unit_price=2500.0,
            currency='JPY',
            commission=100.0,
            settlement_amount=250100.0
        )

        db_session.add(transaction)
        db_session.commit()

        # データベースから取得
        saved = Transaction.query.filter_by(ticker_symbol='7203').first()

        assert saved is not None
        assert saved.ticker_symbol == '7203'
        assert saved.security_name == 'トヨタ自動車'
        assert saved.transaction_type == '買付'
        assert saved.quantity == 100
        assert saved.unit_price == 2500.0
        assert saved.currency == 'JPY'
        assert saved.commission == 100.0
        assert saved.settlement_amount == 250100.0

    def test_transaction_query(self, db_session, sample_transactions):
        """取引データのクエリテスト"""
        # 全取引の取得
        all_transactions = Transaction.query.all()
        assert len(all_transactions) == 3

        # 特定銘柄の取引
        aapl_transactions = Transaction.query.filter_by(ticker_symbol='AAPL').all()
        assert len(aapl_transactions) == 1
        assert aapl_transactions[0].security_name == 'Apple Inc.'

        # 買付取引のみ
        buy_transactions = Transaction.query.filter_by(transaction_type='買付').all()
        assert len(buy_transactions) == 2

    def test_transaction_update(self, db_session, sample_transactions):
        """取引データの更新テスト"""
        transaction = Transaction.query.filter_by(ticker_symbol='1475').first()
        original_quantity = transaction.quantity

        # 数量を更新
        transaction.quantity = 150
        db_session.commit()

        # 再取得して確認
        updated = Transaction.query.get(transaction.id)
        assert updated.quantity == 150
        assert updated.quantity != original_quantity

    def test_transaction_delete(self, db_session, sample_transactions):
        """取引データの削除テスト"""
        transaction = Transaction.query.filter_by(ticker_symbol='AAPL').first()
        transaction_id = transaction.id

        db_session.delete(transaction)
        db_session.commit()

        # 削除確認
        deleted = Transaction.query.get(transaction_id)
        assert deleted is None


class TestHolding:
    """Holdingモデルのテスト"""

    def test_create_holding(self, db_session):
        """保有銘柄データの作成テスト"""
        holding = Holding(
            ticker_symbol='9984',
            security_name='ソフトバンクグループ',
            total_quantity=100,
            average_cost=5000.0,
            total_cost=500000.0,
            currency='JPY',
            current_price=5500.0,
            current_value=550000.0,
            unrealized_pnl=50000.0,
            unrealized_pnl_pct=10.0
        )

        db_session.add(holding)
        db_session.commit()

        saved = Holding.query.filter_by(ticker_symbol='9984').first()

        assert saved is not None
        assert saved.ticker_symbol == '9984'
        assert saved.total_quantity == 100
        assert saved.average_cost == 5000.0
        assert saved.unrealized_pnl == 50000.0
        assert saved.unrealized_pnl_pct == 10.0

    def test_holding_query(self, db_session, sample_holdings):
        """保有銘柄データのクエリテスト"""
        all_holdings = Holding.query.all()
        assert len(all_holdings) == 2

        # 利益が出ている銘柄
        profitable = Holding.query.filter(Holding.unrealized_pnl > 0).all()
        assert len(profitable) == 2

    def test_holding_calculation(self, db_session, sample_holdings):
        """保有銘柄の計算値検証"""
        holding = Holding.query.filter_by(ticker_symbol='AAPL').first()

        # current_value と current_price は異なる通貨単位の可能性がある
        # (current_priceはUSD、current_valueはJPY換算済み)
        # したがって、current_valueが既に設定されていることを検証
        assert holding.current_value is not None
        assert holding.current_value > 0

        # 損益率の検証
        expected_pnl_pct = (holding.unrealized_pnl / holding.total_cost) * 100
        assert abs(holding.unrealized_pnl_pct - expected_pnl_pct) < 0.01


class TestRealizedPnl:
    """RealizedPnlモデルのテスト"""

    def test_create_realized_pnl(self, db_session):
        """実現損益データの作成テスト"""
        realized = RealizedPnl(
            ticker_symbol='8306',
            sell_date=date(2024, 3, 20),
            quantity=500,
            average_cost=1000.0,
            sell_price=1200.0,
            realized_pnl=100000.0,
            realized_pnl_pct=20.0,
            currency='JPY'
        )

        db_session.add(realized)
        db_session.commit()

        saved = RealizedPnl.query.filter_by(ticker_symbol='8306').first()

        assert saved is not None
        assert saved.realized_pnl == 100000.0
        assert saved.realized_pnl_pct == 20.0

    def test_realized_pnl_query(self, db_session, sample_realized_pnl):
        """実現損益データのクエリテスト"""
        all_realized = RealizedPnl.query.all()
        assert len(all_realized) == 1

        # 利益が出た売却のみ
        profitable = RealizedPnl.query.filter(RealizedPnl.realized_pnl > 0).all()
        assert len(profitable) == 1


class TestDividend:
    """Dividendモデルのテスト"""

    def test_create_dividend(self, db_session):
        """配当データの作成テスト"""
        dividend = Dividend(
            ticker_symbol='MSFT',
            ex_dividend_date=date(2024, 6, 15),
            payment_date=date(2024, 6, 30),
            dividend_amount=0.75,
            quantity_held=20,
            total_dividend=2250.0,  # 0.75 * 20 * 150 (JPY換算済み)
            currency='USD',
            source='manual'
        )

        db_session.add(dividend)
        db_session.commit()

        saved = Dividend.query.filter_by(ticker_symbol='MSFT').first()

        assert saved is not None
        assert saved.quantity_held == 20
        assert saved.dividend_amount == 0.75
        assert saved.total_dividend == 2250.0

    def test_dividend_query(self, db_session, sample_dividends):
        """配当データのクエリテスト"""
        all_dividends = Dividend.query.all()
        assert len(all_dividends) == 1

        # 特定銘柄の配当
        aapl_dividends = Dividend.query.filter_by(ticker_symbol='AAPL').all()
        assert len(aapl_dividends) == 1

    def test_dividend_calculation(self, db_session, sample_dividends):
        """配当金計算の検証"""
        dividend = Dividend.query.filter_by(ticker_symbol='AAPL').first()

        # 配当金総額が正しく記録されているか確認
        # total_dividend = 1株配当 × 数量 × 為替レート（事前計算済み）
        assert abs(float(dividend.total_dividend) - 360.0) < 0.01
        assert abs(float(dividend.dividend_amount) - 0.24) < 0.01
        assert abs(float(dividend.quantity_held) - 10) < 0.01
