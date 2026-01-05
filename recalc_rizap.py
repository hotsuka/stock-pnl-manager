"""Recalculate RIZAP holdings"""
from app import create_app
from app.services.transaction_service import TransactionService
from app.models.holding import Holding

app = create_app()

with app.app_context():
    print("Recalculating RIZAP (2928@S.T)...")

    try:
        TransactionService.recalculate_holding('2928@S.T')
        print("Recalculation completed!")

        # Check the updated holding
        holding = Holding.query.filter_by(ticker_symbol='2928@S.T').first()
        if holding:
            print(f"\nUpdated holding:")
            print(f"  Quantity: {holding.total_quantity}")
            print(f"  Average Cost: {holding.average_cost}")
            print(f"  Total Cost: {holding.total_cost}")
        else:
            print("Warning: No holding found after recalculation")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
