from app import create_app, db
from app.models.transaction import Transaction
from app.models.holding import Holding

app = create_app()
ctx = app.app_context()
ctx.push()

print('=== Transactions for 9418 (Time Series) ===')
transactions = Transaction.query.filter_by(ticker_symbol='9418').order_by(Transaction.transaction_date).all()
for x in transactions:
    print(f'{x.transaction_date}: {x.transaction_type} Qty={x.quantity}, Price={x.unit_price}, Settlement={x.settlement_amount}')

print('\n=== Current Holdings for 9418 ===')
h = Holding.query.filter_by(ticker_symbol='9418').first()
if h:
    print(f'Total Quantity: {h.total_quantity}')
    print(f'Average Cost: {h.average_cost}')
    print(f'Total Cost: {h.total_cost}')

    print('\n=== Manual Moving Average Calculation ===')
    qty = 0
    cost = 0
    avg = 0

    for tr in transactions:
        print(f'  {tr.transaction_date} {tr.transaction_type}: ', end='')
        if tr.transaction_type == 'BUY':
            tr_cost = float(tr.settlement_amount) if tr.settlement_amount else (float(tr.quantity) * float(tr.unit_price))
            cost += tr_cost
            qty += float(tr.quantity)
            avg = cost / qty if qty > 0 else 0
            print(f'Buy {tr.quantity} @ settlement {tr.settlement_amount} -> Qty={qty}, TotalCost={cost:.2f}, AvgCost={avg:.2f}')
        elif tr.transaction_type == 'SELL':
            sold_cost = float(tr.quantity) * avg
            cost -= sold_cost
            qty -= float(tr.quantity)
            print(f'Sell {tr.quantity} @ avg {avg:.2f} -> Qty={qty}, TotalCost={cost:.2f}, AvgCost={cost/qty if qty > 0 else 0:.2f}')

    print(f'\n=== Comparison ===')
    print(f'Expected (Moving Avg): Qty={qty}, TotalCost={cost:.2f}, AvgCost={cost/qty if qty > 0 else 0:.2f}')
    print(f'Actual DB:             Qty={h.total_quantity}, TotalCost={h.total_cost}, AvgCost={h.average_cost}')
else:
    print('No holding data')
