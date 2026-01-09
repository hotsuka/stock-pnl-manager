"""Test holdings API response"""
from app import create_app
from app.models.holding import Holding

app = create_app()

with app.app_context():
    holdings = Holding.query.limit(3).all()

    print("Testing holdings data...")
    for h in holdings:
        print(f"\n{h.ticker_symbol}:")
        print(f"  current_price: {h.current_price}")

        # Check if previous_close and day_change_pct exist
        if hasattr(h, 'previous_close'):
            print(f"  previous_close: {h.previous_close}")
        else:
            print("  previous_close: NOT FOUND IN MODEL")

        if hasattr(h, 'day_change_pct'):
            print(f"  day_change_pct: {h.day_change_pct}")
        else:
            print("  day_change_pct: NOT FOUND IN MODEL")

        # Test to_dict
        print(f"\n  to_dict() keys: {h.to_dict().keys()}")

        if 'day_change_pct' in h.to_dict():
            print(f"  day_change_pct in dict: {h.to_dict()['day_change_pct']}")
        else:
            print("  day_change_pct: NOT IN TO_DICT()")
