"""株式評価指標モデル

Yahoo Financeから取得した財務指標を保存するモデル
"""

from datetime import datetime
from app import db


class StockMetrics(db.Model):
    """株式評価指標モデル

    12種類の財務・株価指標を保存:
    - バリュエーション指標 (時価総額、Beta、PER、EPS、PBR)
    - 企業価値指標 (EV/Revenue、EV/EBITDA)
    - 財務指標 (売上、利益率)
    - 株価レンジ (52週高値・安値)
    - リターン指標 (YTD、1年)
    """

    __tablename__ = "stock_metrics"

    id = db.Column(db.Integer, primary_key=True)
    ticker_symbol = db.Column(db.String(20), nullable=False, unique=True, index=True)

    # バリュエーション指標
    market_cap = db.Column(db.Numeric(20, 2))  # 時価総額
    beta = db.Column(db.Numeric(10, 4))  # Beta (5Y Monthly)
    pe_ratio = db.Column(db.Numeric(10, 2))  # PE Ratio (TTM)
    eps = db.Column(db.Numeric(15, 4))  # EPS (TTM)
    pb_ratio = db.Column(db.Numeric(10, 2))  # Price/Book (mrq)

    # 企業価値指標
    ev_to_revenue = db.Column(db.Numeric(10, 2))  # Enterprise Value/Revenue
    ev_to_ebitda = db.Column(db.Numeric(10, 2))  # Enterprise Value/EBITDA

    # 財務指標
    revenue = db.Column(db.Numeric(20, 2))  # Revenue (TTM)
    profit_margin = db.Column(db.Numeric(10, 4))  # Profit Margin

    # 株価レンジ
    fifty_two_week_low = db.Column(db.Numeric(15, 4))  # 52週安値
    fifty_two_week_high = db.Column(db.Numeric(15, 4))  # 52週高値

    # リターン指標
    ytd_return = db.Column(db.Numeric(10, 4))  # YTD Return（小数形式）
    one_year_return = db.Column(db.Numeric(10, 4))  # 1-Year Return（小数形式）

    # メタデータ
    currency = db.Column(db.String(3))  # 通貨コード
    last_updated = db.Column(db.DateTime)  # 最終更新日時
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 作成日時

    def to_dict(self):
        """辞書形式に変換（Nullチェック付き）

        Returns:
            dict: 評価指標データの辞書
        """
        return {
            "ticker_symbol": self.ticker_symbol,
            "market_cap": float(self.market_cap) if self.market_cap else None,
            "beta": float(self.beta) if self.beta else None,
            "pe_ratio": float(self.pe_ratio) if self.pe_ratio else None,
            "eps": float(self.eps) if self.eps else None,
            "pb_ratio": float(self.pb_ratio) if self.pb_ratio else None,
            "ev_to_revenue": float(self.ev_to_revenue) if self.ev_to_revenue else None,
            "ev_to_ebitda": float(self.ev_to_ebitda) if self.ev_to_ebitda else None,
            "revenue": float(self.revenue) if self.revenue else None,
            "profit_margin": float(self.profit_margin) if self.profit_margin else None,
            "fifty_two_week_low": (
                float(self.fifty_two_week_low) if self.fifty_two_week_low else None
            ),
            "fifty_two_week_high": (
                float(self.fifty_two_week_high) if self.fifty_two_week_high else None
            ),
            "ytd_return": float(self.ytd_return) if self.ytd_return else None,
            "one_year_return": (
                float(self.one_year_return) if self.one_year_return else None
            ),
            "currency": self.currency,
            "last_updated": (
                self.last_updated.isoformat() if self.last_updated else None
            ),
        }

    def __repr__(self):
        return f"<StockMetrics {self.ticker_symbol}>"
