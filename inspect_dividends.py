from app import create_app, db
import os
from app.models.dividend import Dividend
from collections import Counter
from decimal import Decimal

app = create_app(os.getenv('FLASK_ENV', 'development'))
from collections import Counter
from decimal import Decimal

with app.app_context():
    from app.models.holding import Holding
    for ticker in ['MSFT', 'TSM']:
        h = Holding.query.filter_by(ticker_symbol=ticker).first()
        divs = Dividend.query.filter_by(ticker_symbol=ticker).all()
        print(f"\n--- {ticker} ---")
        print(f"Current Qty in Holding: {h.total_quantity if h else 'N/A'}")
        print(f"Total Dividend Records: {len(divs)}")
        if divs:
            d = divs[0]
            print(f"Sample Div: Date={d.ex_dividend_date}, Div/Share={d.dividend_amount}, Qty_at_record={d.quantity_held}, Total_in_DB={d.total_dividend}, Curr={d.currency}")
            
    # Also check total JPY dividends
    jpy_divs = Dividend.query.filter(Dividend.currency.in_(['JPY', '日本円'])).all()
    print(f"\nTotal JPY Dividend Records: {len(jpy_divs)}")
    print(f"Total JPY Amount: {sum(float(d.total_dividend or 0) for d in jpy_divs)}")
