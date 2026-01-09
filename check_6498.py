from app import create_app, db
from app.models.transaction import Transaction
from app.models.holding import Holding
from decimal import Decimal

app = create_app()
ctx = app.app_context()
ctx.push()

print('=== Transactions for 6498 (Time Series) ===')
transactions = Transaction.query.filter_by(ticker_symbol='6498').order_by(Transaction.transaction_date).all()
for x in transactions:
    print(f'{x.transaction_date}: {x.transaction_type} Qty={x.quantity}, Price={x.unit_price}, Settlement={x.settlement_amount}')

print('\n=== Current Holdings for 6498 ===')
h = Holding.query.filter_by(ticker_symbol='6498').first()
if h:
    print(f'Total Quantity: {h.total_quantity}')
    print(f'Average Cost: {h.average_cost}')
    print(f'Total Cost: {h.total_cost}')

    print('\n=== Manual Moving Average Calculation (Step by Step) ===')
    qty = Decimal('0')
    cost = Decimal('0')
    avg = Decimal('0')

    for i, tr in enumerate(transactions, 1):
        print(f'\nStep {i}: {tr.transaction_date} {tr.transaction_type}')
        if tr.transaction_type == 'BUY':
            tr_cost = Decimal(str(tr.settlement_amount)) if tr.settlement_amount else (Decimal(str(tr.quantity)) * Decimal(str(tr.unit_price)))
            print(f'  Buy {tr.quantity} shares @ settlement {tr.settlement_amount}')
            cost += tr_cost
            qty += Decimal(str(tr.quantity))
            avg = cost / qty if qty > 0 else Decimal('0')
            print(f'  After: Qty={qty}, TotalCost={cost}, AvgCost={avg}')
        elif tr.transaction_type == 'SELL':
            print(f'  Sell {tr.quantity} shares @ current avg {avg}')
            sold_cost = Decimal(str(tr.quantity)) * avg
            cost -= sold_cost
            qty -= Decimal(str(tr.quantity))
            new_avg = cost / qty if qty > 0 else Decimal('0')
            print(f'  After: Qty={qty}, TotalCost={cost}, AvgCost={new_avg} (avg unchanged)')
            avg = new_avg

    print(f'\n=== Final Comparison ===')
    print(f'Expected (Moving Avg): Qty={qty}, TotalCost={cost}, AvgCost={avg}')
    print(f'Actual DB:             Qty={h.total_quantity}, TotalCost={h.total_cost}, AvgCost={h.average_cost}')
    print(f'\nUser Expected:         AvgCost=1196.54, TotalCost=957232')
else:
    print('No holding data')
