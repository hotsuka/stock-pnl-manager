"""Test fetching a single stock price"""
import ssl
import os

# Disable SSL verification
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context

import yfinance as yf

print("Testing single stock price fetch...")
print("-" * 50)

# Test US stock
print("\n[US Stock] AAPL:")
try:
    ticker = yf.Ticker("AAPL")
    hist = ticker.history(period="1d")
    if not hist.empty:
        price = hist['Close'].iloc[-1]
        print(f"  Price: ${price:.2f}")
    else:
        print("  Failed: No data")
except Exception as e:
    print(f"  Error: {e}")

# Test Japanese stock
print("\n[Japanese Stock] 7203.T (Toyota):")
try:
    ticker = yf.Ticker("7203.T")
    hist = ticker.history(period="1d")
    if not hist.empty:
        price = hist['Close'].iloc[-1]
        print(f"  Price: JPY {price:.2f}")
    else:
        print("  Failed: No data")
except Exception as e:
    print(f"  Error: {e}")

print("\n" + "=" * 50)
print("Test complete")
