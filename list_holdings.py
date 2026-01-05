"""List all holdings"""
from app import create_app
from app.models.holding import Holding

app = create_app()

with app.app_context():
    holdings = Holding.query.all()
    print(f"Total holdings: {len(holdings)}")
    print("=" * 80)

    for h in holdings:
        print(f"{h.ticker_symbol:10} {h.security_name:40} Cost: {float(h.total_cost):>12,.0f}")
