from datetime import datetime
from app import db


class Dividend(db.Model):
    """配当履歴モデル"""

    __tablename__ = 'dividends'

    id = db.Column(db.Integer, primary_key=True)
    ticker_symbol = db.Column(db.String(20), nullable=False, index=True)
    ex_dividend_date = db.Column(db.Date, nullable=False, index=True)  # 権利落ち日
    payment_date = db.Column(db.Date)  # 支払日
    dividend_amount = db.Column(db.Numeric(15, 6))  # 1株あたり配当額
    currency = db.Column(db.String(3))
    total_dividend = db.Column(db.Numeric(15, 4))  # 総配当額
    quantity_held = db.Column(db.Numeric(15, 4))  # 配当時の保有数量
    source = db.Column(db.String(50))  # データソース（yahoo/tradingview/manual）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Dividend {self.ticker_symbol} {self.ex_dividend_date} {self.dividend_amount}>'

    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'ticker_symbol': self.ticker_symbol,
            'ex_dividend_date': self.ex_dividend_date.isoformat() if self.ex_dividend_date else None,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'dividend_amount': float(self.dividend_amount) if self.dividend_amount else 0,
            'currency': self.currency,
            'total_dividend': float(self.total_dividend) if self.total_dividend else 0,
            'quantity_held': float(self.quantity_held) if self.quantity_held else 0,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
