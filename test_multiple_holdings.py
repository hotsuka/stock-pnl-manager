"""Test fetching multiple holdings prices"""
import ssl
import os
import sys
import time

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
    # Get ALL holdings
    holdings = Holding.query.all()

    print("Testing multiple holdings price fetch...")
    print(f"Testing with {len(holdings)} holdings")
    print("=" * 60)

    success_count = 0
    fail_count = 0
    total_time = 0

    for holding in holdings:
        ticker = holding.ticker_symbol
        name = holding.security_name or ticker

        print(f"\n[{ticker}] {name}")
        start_time = time.time()

        try:
            price_data = StockPriceFetcher.get_current_price(ticker, use_cache=False)
            elapsed = time.time() - start_time
            total_time += elapsed

            if price_data:
                print(f"  Success: {price_data['currency']} {price_data['price']:.2f}")
                print(f"  Time: {elapsed:.2f}s")
                success_count += 1
            else:
                print(f"  Failed: No data returned")
                print(f"  Time: {elapsed:.2f}s")
                fail_count += 1
        except Exception as e:
            elapsed = time.time() - start_time
            total_time += elapsed
            print(f"  Error: {e}")
            print(f"  Time: {elapsed:.2f}s")
            fail_count += 1

    print("\n" + "=" * 60)
    print(f"Results: {success_count} success, {fail_count} failed")
    print(f"Total time: {total_time:.2f}s")
    print(f"Average time per stock: {total_time/len(holdings):.2f}s")
