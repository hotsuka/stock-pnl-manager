import os
from datetime import datetime
from decimal import Decimal
from app import create_app, db
from app.models.dividend import Dividend
from app.models.holding import Holding
from app.models.transaction import Transaction

app = create_app(os.getenv('FLASK_ENV', 'development'))

def recalculate_dividends():
    with app.app_context():
        print("Starting dividend recalculation...")
        all_dividends = Dividend.query.all()
        
        # Cache transactions by ticker
        ticker_transactions = {}
        
        updated_count = 0
        for div in all_dividends:
            ticker = div.ticker_symbol
            if ticker not in ticker_transactions:
                ticker_transactions[ticker] = Transaction.query.filter_by(ticker_symbol=ticker).order_by(Transaction.transaction_date).all()
            
            # Calculate quantity held at ex_dividend_date
            qty_at_date = Decimal('0')
            for tx in ticker_transactions[ticker]:
                if tx.transaction_date <= div.ex_dividend_date:
                    if tx.transaction_type == 'BUY':
                        qty_at_date += Decimal(str(tx.quantity))
                    elif tx.transaction_type == 'SELL':
                        qty_at_date -= Decimal(str(tx.quantity))
                else:
                    break
            
            # Update record
            div.quantity_held = qty_at_date
            # total_dividend should be in LOCAL CURRENCY
            # Because our API logic in api.py converts it to JPY
            new_total = Decimal(str(div.dividend_amount or 0)) * qty_at_date
            
            if float(div.total_dividend or 0) != float(new_total) or float(div.quantity_held or 0) != float(qty_at_date):
                print(f"Update {ticker} at {div.ex_dividend_date}: Qty {div.quantity_held} -> {qty_at_date}, Total {div.total_dividend} -> {new_total} {div.currency}")
                div.total_dividend = new_total
                div.quantity_held = qty_at_date
                updated_count += 1
        
        db.session.commit()
        print(f"Finished. Updated {updated_count} records.")

if __name__ == '__main__':
    recalculate_dividends()
