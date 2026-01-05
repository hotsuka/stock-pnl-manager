"""Update stock prices with previous close and day change percentage"""
import ssl
import yfinance as yf
from decimal import Decimal
from app import create_app, db
from app.models.holding import Holding

# Disable SSL verification
import os
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context

def format_ticker(ticker_symbol):
    """Format ticker symbol for Yahoo Finance"""
    if ticker_symbol.isdigit():
        return f"{ticker_symbol}.T"
    return ticker_symbol

app = create_app()

with app.app_context():
    holdings = Holding.query.all()

    print(f"Updating prices for {len(holdings)} holdings...")

    for holding in holdings:
        try:
            yf_ticker = format_ticker(holding.ticker_symbol)
            stock = yf.Ticker(yf_ticker)

            # Try to get current price and previous close from info
            try:
                info = stock.info
                current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                previous_close = info.get('previousClose')
            except:
                # Fallback to history
                hist = stock.history(period='2d')
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                    previous_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else None
                else:
                    print(f"  [SKIP] {holding.ticker_symbol}: No data available")
                    continue

            if current_price is None:
                print(f"  [SKIP] {holding.ticker_symbol}: No current price")
                continue

            # Update current price
            holding.current_price = Decimal(str(current_price))
            holding.current_value = holding.total_quantity * holding.current_price
            holding.unrealized_pnl = holding.current_value - holding.total_cost
            if holding.total_cost > 0:
                holding.unrealized_pnl_pct = (holding.unrealized_pnl / holding.total_cost) * 100

            # Update previous close and day change percentage
            if previous_close is not None:
                holding.previous_close = Decimal(str(previous_close))
                if previous_close > 0:
                    day_change = ((current_price - previous_close) / previous_close) * 100
                    holding.day_change_pct = Decimal(str(day_change))
                    print(f"  [OK] {holding.ticker_symbol}: {current_price:,.2f} ({day_change:+.2f}%)")
                else:
                    holding.day_change_pct = None
                    print(f"  [OK] {holding.ticker_symbol}: {current_price:,.2f}")
            else:
                holding.previous_close = None
                holding.day_change_pct = None
                print(f"  [OK] {holding.ticker_symbol}: {current_price:,.2f} (no previous close)")

        except Exception as e:
            print(f"  [ERROR] {holding.ticker_symbol}: {e}")
            continue

    try:
        db.session.commit()
        print("\n[SUCCESS] All prices updated!")
    except Exception as e:
        db.session.rollback()
        print(f"\n[ERROR] Database save failed: {e}")
