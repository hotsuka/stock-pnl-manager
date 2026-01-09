"""Check transactions for USD stocks"""
from app import create_app
from app.models.transaction import Transaction

app = create_app()

with app.app_context():
    # Check GD, TSM, MSFT transactions
    for ticker in ['GD', 'TSM', 'MSFT']:
        transactions = Transaction.query.filter_by(ticker_symbol=ticker).order_by(Transaction.transaction_date).all()
        if transactions:
            print(f"\n{ticker}: {len(transactions)} transactions")
            for t in transactions[:3]:  # Show first 3
                print(f"  {t.transaction_date}: {t.transaction_type} {t.quantity} @ {t.unit_price} {t.currency}")
