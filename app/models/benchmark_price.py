"""ベンチマーク指数の価格キャッシュモデル"""

from datetime import datetime
from app import db


class BenchmarkPrice(db.Model):
    """ベンチマーク指数の日次価格キャッシュ"""

    __tablename__ = "benchmark_prices"

    id = db.Column(db.Integer, primary_key=True)
    benchmark_key = db.Column(
        db.String(10), nullable=False, index=True
    )  # 'TOPIX', 'SP500'
    price_date = db.Column(db.Date, nullable=False, index=True)
    close_price = db.Column(db.Numeric(15, 4), nullable=False)
    previous_close = db.Column(db.Numeric(15, 4))
    currency = db.Column(db.String(3), default="JPY")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("benchmark_key", "price_date", name="uix_benchmark_date"),
    )

    def to_dict(self):
        """辞書形式に変換"""
        return {
            "benchmark_key": self.benchmark_key,
            "price_date": self.price_date.isoformat(),
            "close_price": float(self.close_price),
            "previous_close": (
                float(self.previous_close) if self.previous_close else None
            ),
            "currency": self.currency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<BenchmarkPrice {self.benchmark_key} {self.price_date} {self.close_price}>"
