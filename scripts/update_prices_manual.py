"""Manually update all stock prices with progress display"""
import ssl
import os
import sys

# Add app to path
sys.path.insert(0, 'C:\\projects\\stock-pnl-manager')

# Disable SSL verification
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context

# Initialize Flask app
from app import create_app, db
from app.models.holding import Holding
from app.services.stock_price_fetcher import StockPriceFetcher

app = create_app()

with app.app_context():
    print("=" * 70)
    print("Updating stock prices for all holdings")
    print("=" * 70)

    holdings = Holding.query.all()
    print(f"\nTotal holdings: {len(holdings)}\n")

    success_count = 0
    failed_count = 0
    errors = []

    for idx, holding in enumerate(holdings, 1):
        ticker = holding.ticker_symbol
        name = holding.security_name or ticker

        print(f"[{idx}/{len(holdings)}] {ticker} - {name[:30]:<30} ", end='', flush=True)

        try:
            price_data = StockPriceFetcher.get_current_price(ticker, use_cache=False)

            if price_data:
                # Update holding with new price
                holding.update_current_price(price_data['price'])
                print(f"OK - {price_data['currency']} {price_data['price']:.2f}")
                success_count += 1
            else:
                print(f"FAILED - No data")
                failed_count += 1
                errors.append({'ticker': ticker, 'name': name, 'error': 'No data'})

        except Exception as e:
            print(f"ERROR - {str(e)[:40]}")
            failed_count += 1
            errors.append({'ticker': ticker, 'name': name, 'error': str(e)})

    # Commit all changes
    try:
        db.session.commit()
        print("\n" + "=" * 70)
        print("Database updated successfully!")
    except Exception as e:
        db.session.rollback()
        print("\n" + "=" * 70)
        print(f"ERROR: Database commit failed: {e}")

    print("=" * 70)
    print(f"\nResults:")
    print(f"  Success: {success_count}")
    print(f"  Failed:  {failed_count}")

    if errors:
        print(f"\nFailed tickers:")
        for error in errors:
            print(f"  - {error['ticker']} ({error['name'][:30]}): {error['error'][:50]}")

    print()
