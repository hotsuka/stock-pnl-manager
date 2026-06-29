from datetime import datetime

from app import db


class StockSplit(db.Model):
    """株式分割/併合モデル"""

    __tablename__ = "stock_splits"

    id = db.Column(db.Integer, primary_key=True)
    ticker_symbol = db.Column(db.String(20), nullable=False, index=True)
    effective_date = db.Column(db.Date, nullable=False)
    ratio = db.Column(db.Numeric(10, 4), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "ticker_symbol", "effective_date", name="uix_split_ticker_date"
        ),
    )

    def __repr__(self):
        return (
            f"<StockSplit {self.ticker_symbol} 1:{self.ratio} on {self.effective_date}>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "ticker_symbol": self.ticker_symbol,
            "effective_date": (
                self.effective_date.isoformat() if self.effective_date else None
            ),
            "ratio": float(self.ratio) if self.ratio else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
