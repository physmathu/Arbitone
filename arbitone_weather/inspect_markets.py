"""
Run this FIRST, before live_run.py, to see the actual shape of Kalshi's API
responses. Field names for strike price / threshold can vary or change, so
don't trust live_run.py's parsing blindly -- verify against real output here.

Usage:
    python -m arbitone_weather.inspect_markets

No API key needed -- this only hits public market-data endpoints.
"""

import json
from .config import CITIES
from .kalshi_client import KalshiClient


def run():
    client = KalshiClient()  # no auth needed for public market data

    for city in CITIES:
        print("=" * 60)
        print(f"{city.name} -- series {city.kalshi_series_ticker}")
        print("=" * 60)
        try:
            markets = client.get_markets(city.kalshi_series_ticker)
        except Exception as e:
            print(f"  ERROR fetching markets: {e}")
            print(f"  (This likely means '{city.kalshi_series_ticker}' isn't a real "
                  f"current series ticker -- look up the correct one on kalshi.com "
                  f"and update config.py)")
            continue

        if not markets:
            print("  No open markets found for this series right now.")
            continue

        # Print the first market's full raw structure so you can see every
        # field Kalshi actually returns (strike price field name varies).
        print(json.dumps(markets[0], indent=2))
        print(f"\n  ...({len(markets)} total open markets in this series)")


if __name__ == "__main__":
    run()
