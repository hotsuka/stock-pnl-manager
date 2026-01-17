"""株式評価指標モデルのテスト"""

from datetime import datetime

import pytest

from app import create_app, db
from app.models import StockMetrics


@pytest.fixture
def app():
    """テスト用アプリケーション"""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """テストクライアント"""
    return app.test_client()


class TestStockMetricsModel:
    """StockMetricsモデルのテスト"""

    def test_create_stock_metrics(self, app):
        """評価指標の作成テスト"""
        with app.app_context():
            metrics = StockMetrics(
                ticker_symbol="AAPL",
                market_cap=3000000000000,  # 3兆ドル
                beta=1.2,
                pe_ratio=28.5,
                eps=6.12,
                pb_ratio=45.3,
                ev_to_revenue=7.5,
                ev_to_ebitda=22.1,
                revenue=394000000000,  # 3940億ドル
                profit_margin=0.265,  # 26.5%
                fifty_two_week_low=124.17,
                fifty_two_week_high=199.62,
                ytd_return=0.125,  # 12.5%
                one_year_return=0.35,  # 35%
                currency="USD",
                last_updated=datetime.utcnow(),
            )
            db.session.add(metrics)
            db.session.commit()

            # データベースから取得
            saved_metrics = StockMetrics.query.filter_by(ticker_symbol="AAPL").first()
            assert saved_metrics is not None
            assert saved_metrics.ticker_symbol == "AAPL"
            assert float(saved_metrics.market_cap) == 3000000000000
            assert float(saved_metrics.beta) == 1.2
            assert float(saved_metrics.pe_ratio) == 28.5

    def test_stock_metrics_to_dict(self, app):
        """to_dict()メソッドのテスト"""
        with app.app_context():
            metrics = StockMetrics(
                ticker_symbol="GOOGL",
                market_cap=1800000000000,
                beta=1.05,
                pe_ratio=25.3,
                eps=5.61,
                currency="USD",
                last_updated=datetime.utcnow(),
            )
            db.session.add(metrics)
            db.session.commit()

            # to_dict()の検証
            metrics_dict = metrics.to_dict()
            assert metrics_dict["ticker_symbol"] == "GOOGL"
            assert metrics_dict["market_cap"] == 1800000000000
            assert metrics_dict["beta"] == 1.05
            assert metrics_dict["pe_ratio"] == 25.3
            assert metrics_dict["eps"] == 5.61
            assert metrics_dict["currency"] == "USD"
            assert metrics_dict["last_updated"] is not None

    def test_stock_metrics_null_values(self, app):
        """Null値を含む評価指標のテスト"""
        with app.app_context():
            metrics = StockMetrics(
                ticker_symbol="TSLA",
                market_cap=800000000000,
                beta=2.1,
                # PER, EPS, その他の指標はNull
                currency="USD",
                last_updated=datetime.utcnow(),
            )
            db.session.add(metrics)
            db.session.commit()

            # to_dict()でNullチェック
            metrics_dict = metrics.to_dict()
            assert metrics_dict["ticker_symbol"] == "TSLA"
            assert metrics_dict["market_cap"] == 800000000000
            assert metrics_dict["beta"] == 2.1
            assert metrics_dict["pe_ratio"] is None
            assert metrics_dict["eps"] is None
            assert metrics_dict["ytd_return"] is None

    def test_stock_metrics_unique_ticker(self, app):
        """ティッカーシンボルのユニーク制約テスト"""
        with app.app_context():
            metrics1 = StockMetrics(
                ticker_symbol="MSFT",
                market_cap=2500000000000,
                beta=0.9,
                currency="USD",
                last_updated=datetime.utcnow(),
            )
            db.session.add(metrics1)
            db.session.commit()

            # 同じティッカーで2つ目を作成（エラーになるはず）
            metrics2 = StockMetrics(
                ticker_symbol="MSFT",
                market_cap=2600000000000,
                beta=0.95,
                currency="USD",
                last_updated=datetime.utcnow(),
            )
            db.session.add(metrics2)

            with pytest.raises(Exception):
                db.session.commit()

    def test_stock_metrics_japanese_stock(self, app):
        """日本株の評価指標テスト"""
        with app.app_context():
            metrics = StockMetrics(
                ticker_symbol="7203.T",
                market_cap=40000000000000,  # 40兆円
                beta=1.1,
                pe_ratio=9.5,
                eps=850,
                currency="JPY",
                last_updated=datetime.utcnow(),
            )
            db.session.add(metrics)
            db.session.commit()

            saved_metrics = StockMetrics.query.filter_by(ticker_symbol="7203.T").first()
            assert saved_metrics.currency == "JPY"
            assert float(saved_metrics.market_cap) == 40000000000000
