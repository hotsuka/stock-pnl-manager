"""Check USD stocks currency data"""
from app import create_app
from app.models.holding import Holding

app = create_app()

with app.app_context():
    # Check GD, TSM, MSFT
    for ticker in ['GD', 'TSM', 'MSFT']:
        holding = Holding.query.filter_by(ticker_symbol=ticker).first()
        if holding:
            print(f"{ticker}:")
            print(f"  Currency: {holding.currency}")
            print(f"  Current Price: {holding.current_price}")
            print(f"  Current Value: {holding.current_value}")
            print()
