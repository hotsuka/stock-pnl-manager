"""
pytest設定ファイル
テスト用のフィクスチャを定義します
"""
import pytest
import tempfile
import os
from app import create_app, db
from app.models import Transaction, Holding, RealizedPnl, Dividend
from datetime import datetime, date
from decimal import Decimal


@pytest.fixture(scope='session')
def app():
    """
    テスト用のFlaskアプリケーションを作成
    """
    # テスト用の一時データベースファイルを作成
    db_fd, db_path = tempfile.mkstemp()

    # アプリケーションを作成（テスト設定を使用）
    app = create_app('testing')

    # テスト用の設定を上書き
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False
    })

    # アプリケーションコンテキストを設定
    with app.app_context():
        db.create_all()

    yield app

    # クリーンアップ
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope='function')
def client(app):
    """
    テスト用のFlaskクライアントを作成
    """
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """
    各テスト関数ごとに新しいデータベースセッションを作成
    テスト終了後にロールバック
    """
    with app.app_context():
        # テストデータをクリア
        db.session.remove()
        db.drop_all()
        db.create_all()

        yield db.session

        # テスト後にクリーンアップ
        db.session.remove()


@pytest.fixture
def sample_transactions(db_session):
    """
    サンプル取引データを作成
    """
    transactions = [
        Transaction(
            transaction_date=date(2024, 1, 10),
            ticker_symbol='1475',
            security_name='iシェアーズ TOPIXコアETF',
            transaction_type='買付',
            quantity=100,
            unit_price=2000.0,
            currency='JPY',
            commission=100.0,
            settlement_amount=200100.0
        ),
        Transaction(
            transaction_date=date(2024, 2, 15),
            ticker_symbol='AAPL',
            security_name='Apple Inc.',
            transaction_type='買付',
            quantity=10,
            unit_price=180.0,
            currency='USD',
            commission=5.0,
            settlement_amount=26705.0  # 1,800 USD * 150 JPY/USD + 手数料
        ),
        Transaction(
            transaction_date=date(2024, 3, 20),
            ticker_symbol='1475',
            security_name='iシェアーズ TOPIXコアETF',
            transaction_type='売付',
            quantity=50,
            unit_price=2100.0,
            currency='JPY',
            commission=50.0,
            settlement_amount=104950.0
        )
    ]

    for t in transactions:
        db_session.add(t)

    db_session.commit()

    return transactions


@pytest.fixture
def sample_holdings(db_session):
    """
    サンプル保有銘柄データを作成
    """
    holdings = [
        Holding(
            ticker_symbol='1475',
            security_name='iシェアーズ TOPIXコアETF',
            total_quantity=50,
            average_cost=2000.0,
            total_cost=100050.0,
            currency='JPY',
            current_price=2150.0,
            current_value=107500.0,
            unrealized_pnl=7450.0,
            unrealized_pnl_pct=7.45,
            day_change_pct=2.38
        ),
        Holding(
            ticker_symbol='AAPL',
            security_name='Apple Inc.',
            total_quantity=10,
            average_cost=180.0,
            total_cost=26705.0,
            currency='USD',
            current_price=190.0,
            current_value=28500.0,
            unrealized_pnl=1795.0,
            unrealized_pnl_pct=6.72,
            day_change_pct=1.05
        )
    ]

    for h in holdings:
        db_session.add(h)

    db_session.commit()

    return holdings


@pytest.fixture
def sample_realized_pnl(db_session):
    """
    サンプル実現損益データを作成
    """
    realized = [
        RealizedPnl(
            ticker_symbol='1475',
            sell_date=date(2024, 3, 20),
            quantity=50,
            average_cost=2000.0,
            sell_price=2100.0,
            realized_pnl=4900.0,
            realized_pnl_pct=4.90,
            currency='JPY'
        )
    ]

    for r in realized:
        db_session.add(r)

    db_session.commit()

    return realized


@pytest.fixture
def sample_dividends(db_session):
    """
    サンプル配当データを作成
    """
    dividends = [
        Dividend(
            ticker_symbol='AAPL',
            ex_dividend_date=date(2024, 5, 15),
            payment_date=date(2024, 5, 25),
            dividend_amount=0.24,
            quantity_held=10,
            total_dividend=360.0,  # 0.24 * 10 * 150 JPY/USD (JPY換算済み)
            currency='USD',
            source='manual'
        )
    ]

    for d in dividends:
        db_session.add(d)

    db_session.commit()

    return dividends
