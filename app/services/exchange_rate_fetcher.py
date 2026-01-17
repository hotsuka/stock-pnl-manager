"""
Exchange Rate Fetcher Service

Fetches currency exchange rates from Yahoo Finance
Uses Forex pairs like USDJPY=X
"""

# Disable SSL verification to work around Japanese username path issue
import os
import ssl
from datetime import datetime, timedelta

import yfinance as yf

os.environ["PYTHONHTTPSVERIFY"] = "0"
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
os.environ["SSL_CERT_FILE"] = ""
ssl._create_default_https_context = ssl._create_unverified_context


class ExchangeRateFetcher:
    """Fetch currency exchange rates"""

    # Common currency pairs to JPY
    CURRENCY_PAIRS = {
        "USD": "USDJPY=X",
        "EUR": "EURJPY=X",
        "GBP": "GBPJPY=X",
        "CNY": "CNYJPY=X",
        "KRW": "KRWJPY=X",
        "TWD": "TWDJPY=X",
        "HKD": "HKDJPY=X",
        "AUD": "AUDJPY=X",
        "CAD": "CADJPY=X",
        "CHF": "CHFJPY=X",
    }

    @staticmethod
    def get_exchange_rate(from_currency, to_currency="JPY"):
        """
        Get current exchange rate

        Args:
            from_currency: Source currency code (e.g., 'USD')
            to_currency: Target currency code (default: 'JPY')

        Returns:
            dict: {'rate': float, 'from': str, 'to': str, 'timestamp': datetime}
            None: If fetch fails
        """
        # Same currency
        if from_currency == to_currency:
            return {
                "rate": 1.0,
                "from": from_currency,
                "to": to_currency,
                "timestamp": datetime.now(),
            }

        # JPY to other currency (inverse)
        if from_currency == "JPY" and to_currency in ExchangeRateFetcher.CURRENCY_PAIRS:
            rate_data = ExchangeRateFetcher.get_exchange_rate(to_currency, "JPY")
            if rate_data:
                return {
                    "rate": 1.0 / rate_data["rate"],
                    "from": from_currency,
                    "to": to_currency,
                    "timestamp": rate_data["timestamp"],
                }
            return None

        # Get pair symbol
        if to_currency == "JPY":
            pair_symbol = ExchangeRateFetcher.CURRENCY_PAIRS.get(from_currency)
        else:
            # For non-JPY pairs, construct the symbol
            pair_symbol = f"{from_currency}{to_currency}=X"

        if not pair_symbol:
            print(f"Unsupported currency pair: {from_currency}/{to_currency}")
            return None

        try:
            ticker = yf.Ticker(pair_symbol)

            # Try to get current price
            try:
                rate = ticker.info.get("regularMarketPrice") or ticker.info.get("ask")
            except:
                # Fallback to history
                hist = ticker.history(period="1d")
                if hist.empty:
                    return None
                rate = float(hist["Close"].iloc[-1])

            if rate is None:
                return None

            return {
                "rate": float(rate),
                "from": from_currency,
                "to": to_currency,
                "timestamp": datetime.now(),
                "pair": pair_symbol,
            }

        except Exception as e:
            print(
                f"Error fetching exchange rate for {from_currency}/{to_currency}: {e}"
            )
            return None

    @staticmethod
    def get_multiple_rates(currency_list, to_currency="JPY"):
        """
        Get exchange rates for multiple currencies

        Args:
            currency_list: List of currency codes
            to_currency: Target currency (default: 'JPY')

        Returns:
            dict: {currency: {'rate': float, ...}}
        """
        results = {}
        for currency in currency_list:
            rate_data = ExchangeRateFetcher.get_exchange_rate(currency, to_currency)
            if rate_data:
                results[currency] = rate_data
        return results

    @staticmethod
    def convert_amount(amount, from_currency, to_currency="JPY"):
        """
        Convert an amount from one currency to another

        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code (default: 'JPY')

        Returns:
            dict: {'amount': float, 'rate': float, 'from': str, 'to': str}
            None: If conversion fails
        """
        if amount is None or amount == 0:
            return {"amount": 0, "rate": 0, "from": from_currency, "to": to_currency}

        rate_data = ExchangeRateFetcher.get_exchange_rate(from_currency, to_currency)

        if not rate_data:
            return None

        converted_amount = float(amount) * rate_data["rate"]

        return {
            "amount": converted_amount,
            "original_amount": float(amount),
            "rate": rate_data["rate"],
            "from": from_currency,
            "to": to_currency,
            "timestamp": rate_data["timestamp"],
        }

    @staticmethod
    def get_historical_rate(from_currency, to_currency, date):
        """
        Get historical exchange rate for a specific date

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            date: Date (datetime or string 'YYYY-MM-DD')

        Returns:
            dict: {'rate': float, 'date': datetime, ...}
            None: If fetch fails
        """
        # Same currency
        if from_currency == to_currency:
            return {"rate": 1.0, "from": from_currency, "to": to_currency, "date": date}

        # Get pair symbol
        if to_currency == "JPY":
            pair_symbol = ExchangeRateFetcher.CURRENCY_PAIRS.get(from_currency)
        else:
            pair_symbol = f"{from_currency}{to_currency}=X"

        if not pair_symbol:
            print(f"Unsupported currency pair: {from_currency}/{to_currency}")
            return None

        try:
            ticker = yf.Ticker(pair_symbol)

            # Get history for the date
            # Add a buffer to ensure we get the date
            if isinstance(date, str):
                date = datetime.strptime(date, "%Y-%m-%d").date()

            start_date = date
            end_date = date + timedelta(days=5)  # Buffer for weekends/holidays

            hist = ticker.history(start=start_date, end=end_date)

            if hist.empty:
                return None

            # Get the first available rate on or after the date
            rate = float(hist["Close"].iloc[0])

            return {
                "rate": rate,
                "from": from_currency,
                "to": to_currency,
                "date": hist.index[0].date(),
                "pair": pair_symbol,
            }

        except Exception as e:
            print(
                f"Error fetching historical rate for {from_currency}/{to_currency} on {date}: {e}"
            )
            return None
