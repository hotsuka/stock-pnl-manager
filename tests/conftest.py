"""
pytest設定ファイル
テスト用のフィクスチャを定義します
"""

import pytest
import tempfile
import os
from pathlib import Path
from app import create_app, db
from app.models import Transaction, Holding, RealizedPnl, Dividend
from datetime import datetime, date
from decimal import Decimal


# 本番DBのパス（テスト実行前にバックアップを作成するため）
PRODUCTION_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "stock_pnl.db"


def _backup_production_db():
    """
    テスト実行前に本番DBのバックアップを作成

    テスト中に誤って本番DBを操作してしまった場合に備えて、
    テスト開始前にバックアップを作成する
    """
    if PRODUCTION_DB_PATH.exists():
        try:
            from app.utils.backup import create_backup, get_backup_dir

            backup_dir = get_backup_dir()
            create_backup(PRODUCTION_DB_PATH, backup_dir, prefix="test_safety_backup")
            print(f"\n[TEST SAFETY] 本番DBのバックアップを作成しました: {backup_dir}")
        except Exception as e:
            print(f"\n[TEST SAFETY] バックアップ作成失敗（テストは続行）: {e}")


def _verify_test_db_isolation(db_uri):
    """
    テスト用DBが本番DBと分離されていることを確認

    Args:
        db_uri: テスト用のデータベースURI

    Raises:
        AssertionError: 本番DBに接続しようとした場合
    """
    # 本番DBパスを正規化して比較
    prod_db_str = str(PRODUCTION_DB_PATH).replace("\\", "/").lower()

    # URIからパスを抽出
    if db_uri.startswith("sqlite:///"):
        test_db_path = db_uri.replace("sqlite:///", "").replace("\\", "/").lower()
    else:
        test_db_path = db_uri.lower()

    # 本番DBへの接続を防止
    if prod_db_str in test_db_path or "stock_pnl.db" in test_db_path:
        raise AssertionError(
            f"テストが本番DBに接続しようとしています！\n"
            f"テストDB: {db_uri}\n"
            f"本番DB: {PRODUCTION_DB_PATH}\n"
            f"テスト設定を確認してください。"
        )


@pytest.fixture(scope="session")
def app():
    """
    テスト用のFlaskアプリケーションを作成
    """
    # テスト実行前に本番DBのバックアップを作成
    _backup_production_db()

    # テスト用の一時データベースファイルを作成
    db_fd, db_path = tempfile.mkstemp()

    # 環境変数でテストモードを明示
    os.environ["TESTING"] = "1"

    # アプリケーションを作成（テスト設定を使用）
    app = create_app("testing")

    # テスト用の設定を上書き
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "WTF_CSRF_ENABLED": False,
            "AUTO_BACKUP_ENABLED": False,
        }
    )

    # 本番DBとの分離を確認
    _verify_test_db_isolation(app.config["SQLALCHEMY_DATABASE_URI"])

    # アプリケーションコンテキストを設定
    with app.app_context():
        db.create_all()

    yield app

    # クリーンアップ
    os.close(db_fd)
    os.unlink(db_path)

    # 環境変数をクリア
    if "TESTING" in os.environ:
        del os.environ["TESTING"]


@pytest.fixture(scope="function")
def client(app):
    """
    テスト用のFlaskクライアントを作成
    """
    return app.test_client()


@pytest.fixture(scope="function")
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
            ticker_symbol="AAPL",
            security_name="Apple Inc.",
            transaction_type="BUY",
            quantity=10,
            unit_price=180.0,
            currency="USD",
            commission=5.0,
            settlement_amount=26705.0,  # 1,800 USD * 150 JPY/USD + 手数料
        ),
        Transaction(
            transaction_date=date(2024, 3, 20),
            ticker_symbol="1475",
            security_name="iシェアーズ TOPIXコアETF",
            transaction_type="SELL",
            quantity=50,
            unit_price=2100.0,
            currency="JPY",
            commission=50.0,
            settlement_amount=104950.0,
        ),
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
            ticker_symbol="1475",
            security_name="iシェアーズ TOPIXコアETF",
            total_quantity=50,
            average_cost=2000.0,
            total_cost=100050.0,
            currency="JPY",
            current_price=2150.0,
            current_value=107500.0,
            unrealized_pnl=7450.0,
            unrealized_pnl_pct=7.45,
            day_change_pct=2.38,
        ),
        Holding(
            ticker_symbol="AAPL",
            security_name="Apple Inc.",
            total_quantity=10,
            average_cost=180.0,
            total_cost=26705.0,
            currency="USD",
            current_price=190.0,
            current_value=28500.0,
            unrealized_pnl=1795.0,
            unrealized_pnl_pct=6.72,
            day_change_pct=1.05,
        ),
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
            ticker_symbol="1475",
            sell_date=date(2024, 3, 20),
            quantity=50,
            average_cost=2000.0,
            sell_price=2100.0,
            realized_pnl=4900.0,
            realized_pnl_pct=4.90,
            currency="JPY",
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
            ticker_symbol="AAPL",
            ex_dividend_date=date(2024, 5, 15),
            payment_date=date(2024, 5, 25),
            dividend_amount=0.24,
            quantity_held=10,
            total_dividend=360.0,  # 0.24 * 10 * 150 JPY/USD (JPY換算済み)
            currency="USD",
            source="manual",
        )
    ]

    for d in dividends:
        db_session.add(d)

    db_session.commit()

    return dividends
