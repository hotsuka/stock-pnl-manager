"""
APIエンドポイントの統合テスト
"""

import pytest
import json
from datetime import date


class TestHoldingsAPI:
    """保有銘柄APIのテスト"""

    def test_get_holdings_empty(self, client, db_session):
        """保有銘柄が空の場合"""
        response = client.get("/api/holdings")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["holdings"]) == 0

    def test_get_holdings_with_data(self, client, db_session, sample_holdings):
        """保有銘柄がある場合"""
        response = client.get("/api/holdings")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["holdings"]) == 2

        # データ検証
        holdings = data["holdings"]
        tickers = [h["ticker_symbol"] for h in holdings]
        assert "1475" in tickers
        assert "AAPL" in tickers


class TestTransactionsAPI:
    """取引履歴APIのテスト"""

    def test_get_transactions_empty(self, client, db_session):
        """取引履歴が空の場合"""
        response = client.get("/api/transactions")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["transactions"]) == 0

    def test_get_transactions_with_data(self, client, db_session, sample_transactions):
        """取引履歴がある場合"""
        response = client.get("/api/transactions")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["transactions"]) == 3

    def test_get_transactions_with_limit(self, client, db_session, sample_transactions):
        """取引履歴を件数制限付きで取得"""
        response = client.get("/api/transactions?limit=2")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["transactions"]) <= 2

    def test_get_single_transaction(self, client, db_session, sample_transactions):
        """単一取引の取得"""
        # まず全取引を取得してIDを取得
        response = client.get("/api/transactions")
        data = json.loads(response.data)
        transaction_id = data["transactions"][0]["id"]

        # 単一取引を取得
        response = client.get(f"/api/transactions/{transaction_id}")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert data["transaction"]["id"] == transaction_id

    def test_get_nonexistent_transaction(self, client, db_session):
        """存在しない取引の取得"""
        response = client.get("/api/transactions/99999")
        assert response.status_code == 404

    def test_update_transaction(self, client, db_session, sample_transactions):
        """取引の更新"""
        # 取引IDを取得
        response = client.get("/api/transactions")
        data = json.loads(response.data)
        transaction_id = data["transactions"][0]["id"]

        # 更新データ
        update_data = {"quantity": 150, "price": 2100.0, "commission": 150.0}

        response = client.put(
            f"/api/transactions/{transaction_id}",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

    def test_update_nonexistent_transaction(self, client, db_session):
        """存在しない取引の更新"""
        update_data = {"quantity": 100}

        response = client.put(
            "/api/transactions/99999",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        assert response.status_code == 404


class TestRealizedPnlAPI:
    """実現損益APIのテスト"""

    def test_get_realized_pnl_empty(self, client, db_session):
        """実現損益が空の場合"""
        response = client.get("/api/realized-pnl")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["realized_pnl"]) == 0

    def test_get_realized_pnl_with_data(self, client, db_session, sample_realized_pnl):
        """実現損益がある場合"""
        response = client.get("/api/realized-pnl")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["realized_pnl"]) == 1

        # データ検証
        realized = data["realized_pnl"][0]
        assert realized["ticker_symbol"] == "1475"
        # realized_pnl の値は API の計算ロジックに依存するため、存在確認のみ
        assert "realized_pnl" in realized


class TestDividendsAPI:
    """配当金APIのテスト"""

    def test_get_dividends_empty(self, client, db_session):
        """配当金が空の場合"""
        response = client.get("/api/dividends")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["dividends"]) == 0

    def test_get_dividends_with_data(self, client, db_session, sample_dividends):
        """配当金がある場合"""
        response = client.get("/api/dividends")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["dividends"]) == 1

        # データ検証
        dividend = data["dividends"][0]
        assert dividend["ticker_symbol"] == "AAPL"
        assert dividend["total_dividend"] > 0


class TestDashboardAPI:
    """ダッシュボードAPIのテスト"""

    def test_get_dashboard_summary_empty(self, client, db_session):
        """ダッシュボードサマリー（データなし）"""
        response = client.get("/api/dashboard/summary")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "summary" in data

    def test_get_dashboard_summary_with_data(
        self, client, db_session, sample_holdings, sample_realized_pnl
    ):
        """ダッシュボードサマリー（データあり）"""
        response = client.get("/api/dashboard/summary")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True

        summary = data["summary"]
        assert "ticker_counts" in summary
        assert "investment" in summary
        assert "evaluation" in summary
        assert "total_pnl" in summary

        # 銘柄数の検証
        assert summary["ticker_counts"]["active"] == 2
        # realized は「売却済みで現在保有していない銘柄数」を表す
        # sample_realized_pnl の 1475 は sample_holdings にも存在するため、realized は 0
        assert summary["ticker_counts"]["realized"] == 0

    def test_get_yearly_stats_empty(self, client, db_session):
        """年別実績（データなし）"""
        response = client.get("/api/dashboard/yearly-stats")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["yearly_stats"]) == 0

    def test_get_yearly_stats_with_data(self, client, db_session, sample_realized_pnl):
        """年別実績（データあり）"""
        response = client.get("/api/dashboard/yearly-stats")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "yearly_stats" in data
        assert "total" in data


class TestPerformanceAPI:
    """損益推移APIのテスト"""

    def test_get_performance_history_default(self, client, db_session):
        """損益推移（デフォルトパラメータ）"""
        response = client.get("/api/performance/history")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "data" in data
        assert "portfolio" in data["data"]

    def test_get_performance_history_1m(self, client, db_session):
        """損益推移（1ヶ月）"""
        response = client.get("/api/performance/history?period=1m")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True

    def test_get_performance_history_1y(self, client, db_session):
        """損益推移（1年）"""
        response = client.get("/api/performance/history?period=1y")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True

    def test_get_performance_detail_no_date(self, client, db_session):
        """損益詳細（日付パラメータなし）"""
        response = client.get("/api/performance/detail")
        assert response.status_code == 400

    def test_get_performance_detail_with_date(self, client, db_session):
        """損益詳細（日付指定）"""
        response = client.get("/api/performance/detail?date=2024-01-10")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "details" in data
        assert data["date"] == "2024-01-10"


class TestExchangeRateAPI:
    """為替レートAPIのテスト"""

    def test_get_exchange_rate_single(self, client, db_session):
        """単一通貨の為替レート取得（モック）"""
        # 実際のyfinanceアクセスが必要なため、このテストはスキップまたはモック化が必要
        pass

    def test_get_exchange_rate_multiple(self, client, db_session):
        """複数通貨の為替レート取得（モック）"""
        # 実際のyfinanceアクセスが必要なため、このテストはスキップまたはモック化が必要
        pass


class TestErrorHandling:
    """エラーハンドリングのテスト"""

    def test_404_for_invalid_endpoint(self, client):
        """存在しないエンドポイント"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_405_for_wrong_method(self, client, db_session):
        """不正なHTTPメソッド"""
        response = client.post("/api/holdings")
        # POSTが許可されていない場合、405 Method Not Allowedが返る
        assert response.status_code == 405 or response.status_code == 404
