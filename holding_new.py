from datetime import datetime
from app import db


class Holding(db.Model):
    """保有銘柄モデル"""

    __tablename__ = 'holdings'

    id = db.Column(db.Integer, primary_key=True)
    ticker_symbol = db.Column(db.String(20), unique=True, nullable=False, index=True)
    security_name = db.Column(db.String(200))
    total_quantity = db.Column(db.Numeric(15, 4), nullable=False)  # 現在保有数量
    average_cost = db.Column(db.Numeric(15, 4), nullable=False)  # 平均取得単価（移動平均法）
    currency = db.Column(db.String(3), nullable=False)
    total_cost = db.Column(db.Numeric(15, 4), nullable=False)  # 総取得コスト
    current_price = db.Column(db.Numeric(15, 4))  # 最新株価
    previous_close = db.Column(db.Numeric(15, 4))  # 前日終値
    day_change_pct = db.Column(db.Numeric(10, 4))  # 対前日変動率（%）
    current_value = db.Column(db.Numeric(15, 4))  # 現在評価額
    unrealized_pnl = db.Column(db.Numeric(15, 4))  # 未実現損益
    unrealized_pnl_pct = db.Column(db.Numeric(10, 4))  # 未実現損益率（%）
    last_updated = db.Column(db.DateTime)  # 最終更新日時
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Holding {self.ticker_symbol} {self.total_quantity}@{self.average_cost}>'

    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'ticker_symbol': self.ticker_symbol,
            'security_name': self.security_name,
            'total_quantity': float(self.total_quantity) if self.total_quantity else 0,
            'average_cost': float(self.average_cost) if self.average_cost else 0,
            'currency': self.currency,
            'total_cost': float(self.total_cost) if self.total_cost else 0,
            'current_price': float(self.current_price) if self.current_price else None,
            'previous_close': float(self.previous_close) if self.previous_close else None,
            'day_change_pct': float(self.day_change_pct) if self.day_change_pct else None,
            'current_value': float(self.current_value) if self.current_value else None,
            'unrealized_pnl': float(self.unrealized_pnl) if self.unrealized_pnl else None,
            'unrealized_pnl_pct': float(self.unrealized_pnl_pct) if self.unrealized_pnl_pct else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def update_current_price(self, price, previous_close=None):
        """株価更新と損益計算"""
        from decimal import Decimal

        # Convert price to Decimal for consistent type handling
        price_decimal = Decimal(str(price))

        self.current_price = price_decimal
        self.current_value = self.total_quantity * price_decimal
        self.unrealized_pnl = self.current_value - self.total_cost
        if self.total_cost > 0:
            self.unrealized_pnl_pct = (self.unrealized_pnl / self.total_cost) * 100

        # Update previous close and day change if provided
        if previous_close is not None:
            self.previous_close = Decimal(str(previous_close))
            if previous_close > 0:
                day_change = ((float(price_decimal) - previous_close) / previous_close) * 100
                self.day_change_pct = Decimal(str(day_change))

        self.last_updated = datetime.utcnow()
