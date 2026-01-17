from datetime import datetime
from app import db


class Transaction(db.Model):
    """取引履歴モデル"""

    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    transaction_date = db.Column(db.Date, nullable=False, index=True)
    ticker_symbol = db.Column(db.String(20), nullable=False, index=True)
    security_name = db.Column(db.String(200))
    transaction_type = db.Column(db.String(10), nullable=False)  # 'BUY' or 'SELL'
    currency = db.Column(db.String(3), nullable=False)  # 'JPY', 'USD', etc.
    quantity = db.Column(db.Numeric(15, 4), nullable=False)
    unit_price = db.Column(db.Numeric(15, 4), nullable=False)
    commission = db.Column(db.Numeric(15, 4), default=0)
    settlement_amount = db.Column(db.Numeric(15, 4))
    exchange_rate = db.Column(db.Numeric(10, 4))  # 為替レート（外国株の場合）
    settlement_currency = db.Column(db.String(3))  # 受渡通貨
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Transaction {self.ticker_symbol} {self.transaction_type} {self.quantity}@{self.unit_price}>"

    def to_dict(self):
        """辞書形式に変換"""
        return {
            "id": self.id,
            "transaction_date": self.transaction_date.isoformat() if self.transaction_date else None,
            "ticker_symbol": self.ticker_symbol,
            "security_name": self.security_name,
            "transaction_type": self.transaction_type,
            "currency": self.currency,
            "quantity": float(self.quantity) if self.quantity else 0,
            "unit_price": float(self.unit_price) if self.unit_price else 0,
            "commission": float(self.commission) if self.commission else 0,
            "settlement_amount": float(self.settlement_amount) if self.settlement_amount else 0,
            "exchange_rate": float(self.exchange_rate) if self.exchange_rate else None,
            "settlement_currency": self.settlement_currency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
