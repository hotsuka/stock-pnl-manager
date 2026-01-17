from datetime import datetime

from app import db


class RealizedPnl(db.Model):
    """確定損益モデル"""

    __tablename__ = "realized_pnl"

    id = db.Column(db.Integer, primary_key=True)
    ticker_symbol = db.Column(db.String(20), nullable=False, index=True)
    sell_date = db.Column(db.Date, nullable=False, index=True)
    quantity = db.Column(db.Numeric(15, 4), nullable=False)
    average_cost = db.Column(db.Numeric(15, 4), nullable=False)  # 売却時の平均取得単価
    sell_price = db.Column(db.Numeric(15, 4), nullable=False)  # 売却単価
    realized_pnl = db.Column(db.Numeric(15, 4), nullable=False)  # 確定損益
    realized_pnl_pct = db.Column(db.Numeric(10, 4))  # 確定損益率
    commission = db.Column(db.Numeric(15, 4))  # 手数料
    currency = db.Column(db.String(3))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<RealizedPnl {self.ticker_symbol} {self.sell_date} {self.realized_pnl}>"
        )

    def to_dict(self):
        """辞書形式に変換"""
        return {
            "id": self.id,
            "ticker_symbol": self.ticker_symbol,
            "sell_date": self.sell_date.isoformat() if self.sell_date else None,
            "quantity": float(self.quantity) if self.quantity else 0,
            "average_cost": float(self.average_cost) if self.average_cost else 0,
            "sell_price": float(self.sell_price) if self.sell_price else 0,
            "realized_pnl": float(self.realized_pnl) if self.realized_pnl else 0,
            "realized_pnl_pct": (
                float(self.realized_pnl_pct) if self.realized_pnl_pct else None
            ),
            "commission": float(self.commission) if self.commission else 0,
            "currency": self.currency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
