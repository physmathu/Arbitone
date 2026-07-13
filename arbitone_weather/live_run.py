"""
Real-data version of main.py -- pulls live NOAA forecasts and live Kalshi
orderbooks instead of mock data. Trading is OFF by default (dry-run: prints
signals only). Read the SAFETY section below before turning anything on.

-----------------------------------------------------------------------
SAFETY
-----------------------------------------------------------------------
- EXECUTE_TRADES is False by default. It will only place real orders if
  you explicitly set it to True below.
- BASE_URL defaults to Kalshi's DEMO environment (paper trading, fake
  money on their servers). To go live with real money, you must
  deliberately change BASE_URL to KALSHI_BASE_URL below -- this is a
  one-line change on purpose, so it's never accidental.
- Before EXECUTE_TRADES=True, run inspect_markets.py first to confirm the
  strike-price field name this code assumes ("floor_strike") actually
  matches what Kalshi returns for your markets -- API field names can
  differ or change.
-----------------------------------------------------------------------

Usage:
    export KALSHI_API_KEY_ID="your-key-id"
    export KALSHI_PRIVATE_KEY_PATH="/path/to/your/private_key.pem"
    python -m arbitone_weather.live_run
"""

import os
from datetime import date, timedelta

from .config import CITIES, KALSHI_DEMO_BASE_URL, KALSHI_BASE_URL
from .fair_value import prob_high_at_or_above
from .kalshi_client import KalshiClient
from .noaa_client import NOAAClient
from .paper_trader import PaperLedger
from .signal_engine import evaluate_market, SignalAction

# ---------------------------------------------------------------------
# SAFETY SWITCHES -- change deliberately, not accidentally
# ---------------------------------------------------------------------
EXECUTE_TRADES = False                  # True = place real/demo orders. False = print-only.
BASE_URL = KALSHI_DEMO_BASE_URL         # change to KALSHI_BASE_URL only when ready for real money
TARGET_DATE = date.today() + timedelta(days=1)  # which day's high temp to evaluate
# ---------------------------------------------------------------------


def run():
    api_key_id = os.environ.get("KALSHI_API_KEY_ID")
    private_key_path = os.environ.get("KALSHI_PRIVATE_KEY_PATH")

    if EXECUTE_TRADES and not (api_key_id and private_key_path):
        raise RuntimeError(
            "EXECUTE_TRADES is True but KALSHI_API_KEY_ID / KALSHI_PRIVATE_KEY_PATH "
            "aren't set. Set them as environment variables, or set EXECUTE_TRADES "
            "back to False to run in print-only mode."
        )

    kalshi = KalshiClient(api_key_id=api_key_id, private_key_path=private_key_path, base_url=BASE_URL)
    noaa = NOAAClient()
    ledger = PaperLedger()

    print("=" * 60)
    print(f"ARBITONE WEATHER MARKET MAKER -- LIVE DATA "
          f"({'DEMO' if BASE_URL == KALSHI_DEMO_BASE_URL else 'PRODUCTION -- REAL MONEY'})")
    print(f"Trade execution: {'ON' if EXECUTE_TRADES else 'OFF (print-only)'}")
    print(f"Target date: {TARGET_DATE}")
    print("=" * 60)

    for city in CITIES:
        print(f"\n--- {city.name} ---")

        try:
            forecast = noaa.get_daily_high_forecast(city.noaa_lat, city.noaa_lon, TARGET_DATE)
        except Exception as e:
            print(f"  NOAA fetch failed: {e}")
            continue
        if forecast is None:
            print(f"  No NOAA forecast available for {TARGET_DATE} (outside forecast window?).")
            continue
        print(f"  NOAA forecast high: {forecast.high_temp_f}F ({forecast.short_forecast})")

        try:
            markets = kalshi.get_markets(city.kalshi_series_ticker)
        except Exception as e:
            print(f"  Kalshi market fetch failed: {e}")
            print(f"  Check that '{city.kalshi_series_ticker}' is a real current series "
                  f"ticker (run inspect_markets.py to verify).")
            continue

        for market in markets:
            ticker = market["ticker"]

            # NOTE: verify this field name with inspect_markets.py -- Kalshi's
            # strike-price field name may differ (floor_strike, cap_strike,
            # strike_price, etc. depending on contract type).
            threshold_f = market.get("floor_strike")
            if threshold_f is None:
                print(f"  Skipping {ticker}: couldn't find strike price field "
                      f"(run inspect_markets.py to find the right field name).")
                continue

            try:
                quote = kalshi.get_orderbook(ticker)
            except Exception as e:
                print(f"  Orderbook fetch failed for {ticker}: {e}")
                continue

            model_prob = prob_high_at_or_above(forecast.high_temp_f, float(threshold_f))
            signal = evaluate_market(ticker, model_prob, quote)

            print(f"  {ticker} (threshold {threshold_f}F): "
                  f"model={signal.model_prob_cents}c market_yes_ask={signal.market_yes_ask_cents} "
                  f"market_no_ask={signal.market_no_ask_cents} edge={signal.edge_cents}c "
                  f"action={signal.action.value}")

            if signal.action == SignalAction.NONE:
                continue

            if EXECUTE_TRADES:
                side = "yes" if signal.action == SignalAction.BUY_YES else "no"
                price = signal.market_yes_ask_cents if side == "yes" else signal.market_no_ask_cents
                try:
                    result = kalshi.place_order(ticker, side=side, action="buy", count=1, price_cents=price)
                    print(f"    ORDER PLACED: {result}")
                except Exception as e:
                    print(f"    ORDER FAILED: {e}")
            else:
                ledger.process_signal(signal, contracts=1)

    if not EXECUTE_TRADES:
        print("\n" + "=" * 60)
        print("LOCAL PAPER LEDGER (simulated, not sent to Kalshi)")
        print("=" * 60)
        for line in ledger.trade_log:
            print(f"  {line}")
        print(ledger.summary())


if __name__ == "__main__":
    run()
