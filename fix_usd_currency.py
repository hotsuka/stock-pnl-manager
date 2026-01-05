"""Fix currency for GD and MSFT"""
from app import create_app, db
from app.models.holding import Holding
from app.models.transaction import Transaction

app = create_app()

with app.app_context():
    # Fix GD and MSFT currency
    for ticker in ['GD', 'MSFT']:
        print(f"\nFixing {ticker}...")

        # Update transactions
        transactions = Transaction.query.filter_by(ticker_symbol=ticker).all()
        for t in transactions:
            t.currency = 'USD'
        print(f"  Updated {len(transactions)} transactions to USD")

        # Update holding
        holding = Holding.query.filter_by(ticker_symbol=ticker).first()
        if holding:
            holding.currency = 'USD'
            print(f"  Updated holding to USD")

    # Commit changes
    db.session.commit()
    print("\nChanges committed successfully!")

    # Verify
    print("\nVerification:")
    for ticker in ['GD', 'TSM', 'MSFT']:
        holding = Holding.query.filter_by(ticker_symbol=ticker).first()
        if holding:
            print(f"  {ticker}: {holding.currency}")
