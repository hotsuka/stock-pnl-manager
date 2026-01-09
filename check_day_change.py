"""Check day change data in database"""
from app import create_app
from app.models.holding import Holding

app = create_app()

with app.app_context():
    holdings = Holding.query.limit(5).all()

    print("Checking day change data in database:\n")
    for h in holdings:
        print(f"{h.ticker_symbol}:")
        print(f"  Current Price: {h.current_price}")
        print(f"  Previous Close: {h.previous_close}")
        print(f"  Day Change %: {h.day_change_pct}")

        # Check to_dict
        data = h.to_dict()
        print(f"  In API (to_dict): day_change_pct = {data.get('day_change_pct')}")
        print()
