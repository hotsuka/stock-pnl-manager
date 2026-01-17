from datetime import datetime
from app import db


class StockPrice(db.Model):
    """株価キャッシュモデル"""

    __tablename__ = "stock_prices"

    id = db.Column(db.Integer, primary_key=True)
    ticker_symbol = db.Column(db.String(20), nullable=False, index=True)
    price_date = db.Column(db.Date, nullable=False, index=True)
    close_price = db.Column(db.Numeric(15, 4), nullable=False)
    currency = db.Column(db.String(3))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 複合ユニーク制約
    __table_args__ = (
        db.UniqueConstraint("ticker_symbol", "price_date", name="uix_ticker_date"),
    )

    def __repr__(self):
        return f"<StockPrice {self.ticker_symbol} {self.price_date} {self.close_price}>"

    def to_dict(self):
        """辞書形式に変換"""
        return {
            "id": self.id,
            "ticker_symbol": self.ticker_symbol,
            "price_date": self.price_date.isoformat() if self.price_date else None,
            "close_price": float(self.close_price) if self.close_price else 0,
            "currency": self.currency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
