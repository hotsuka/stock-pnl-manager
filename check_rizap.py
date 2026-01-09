"""Check RIZAP holding data"""
from app import create_app, db
from app.models.holding import Holding
from app.models.transaction import Transaction

app = create_app()

with app.app_context():
    # Get RIZAP holding - try different ticker formats
    holding = Holding.query.filter_by(ticker_symbol='2928').first()
    if not holding:
        holding = Holding.query.filter_by(ticker_symbol='2928@S.T').first()
    if not holding:
        # Search by name
        holding = Holding.query.filter(Holding.security_name.like('%RIZAP%')).first()

    if holding:
        print("=" * 60)
        print("RIZAP Group Holding Data")
        print("=" * 60)
        print(f"Ticker: {holding.ticker_symbol}")
        print(f"Name: {holding.security_name}")
        print(f"Quantity: {holding.total_quantity}")
        print(f"Average Cost: {holding.average_cost}")
        print(f"Total Cost: {holding.total_cost}")
        print(f"Currency: {holding.currency}")
        print()

        # Get all transactions using the actual ticker from the holding
        ticker = holding.ticker_symbol
        transactions = Transaction.query.filter_by(ticker_symbol=ticker).order_by(Transaction.transaction_date).all()
        print(f"Total Transactions: {len(transactions)}")
        print("=" * 60)
        print("Transactions:")
        print("=" * 60)

        for t in transactions:
            print(f"Date: {t.transaction_date}")
            print(f"  Type: {t.transaction_type}")
            print(f"  Quantity: {t.quantity}")
            print(f"  Unit Price: {t.unit_price}")
            print(f"  Settlement Amount: {t.settlement_amount}")
            print(f"  Commission: {t.commission}")
            print()
    else:
        print("No holding found for ticker 2928")
