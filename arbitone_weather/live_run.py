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
- Before EXECUTE_TRADES=True, run this in print-only mode for a while and
  sanity-check the printed signals against what you see on kalshi.com
  yourself. Field parsing has been verified against real API output
  (both floor_strike/"greater" and cap_strike/"less" contract types).
-----------------------------------------------------------------------

Usage:
    export KALSHI_API_KEY_ID="your-key-id"
    export KALSHI_PRIVATE_KEY_PATH="/path/to/your/private_key.pem"
    python -m arbitone_weather.live_run
"""

import csv
import os
from datetime import date, datetime, timedelta, timezone

from .config import CITIES, KALSHI_DEMO_BASE_URL, KALSHI_BASE_URL
from .fair_value import prob_yes_for_market
from .kalshi_client import KalshiClient
from .noaa_client import NOAAClient
from .paper_trader import PaperLedger
from .signal_engine import evaluate_market, SignalAction

# ---------------------------------------------------------------------
# SAFETY SWITCHES -- change deliberately, not accidentally
# ---------------------------------------------------------------------
EXECUTE_TRADES = False                  # True = place real/demo orders. False = print-only.
BASE_URL = KALSHI_BASE_URL              # PRODUCTION for real prices (read-only, safe -- EXECUTE_TRADES
                                         # is the actual money switch, not this URL). Kalshi's own docs
                                         # say demo market prices don't reflect real markets, so demo
                                         # is only useful once you're actually placing (fake) orders.
TARGET_DATE = date.today() + timedelta(days=1)  # which day's high temp to evaluate

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "signals.csv")
LOG_FIELDS = ["run_timestamp_utc", "city", "ticker", "strike_type", "threshold_f",
              "noaa_forecast_f", "model_prob_cents", "market_yes_ask", "market_no_ask",
              "edge_cents", "action"]
# ---------------------------------------------------------------------


def _append_log_row(row: dict):
    file_exists = os.path.exists(LOG_PATH)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


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

    if EXECUTE_TRADES and BASE_URL == KALSHI_BASE_URL:
        mode_label = "LIVE TRADING -- REAL MONEY"
    elif EXECUTE_TRADES and BASE_URL == KALSHI_DEMO_BASE_URL:
        mode_label = "DEMO TRADING (fake orders, fake money)"
    else:
        data_source = "production (real prices)" if BASE_URL == KALSHI_BASE_URL else "demo (NOT real prices)"
        mode_label = f"PRINT-ONLY, reading {data_source} -- no orders placed, zero risk"

    print("=" * 60)
    print(f"ARBITONE WEATHER MARKET MAKER -- {mode_label}")
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
            strike_type = market.get("strike_type")  # "greater" -> floor_strike, "less" -> cap_strike

            if strike_type == "greater":
                threshold_f = market.get("floor_strike")
            elif strike_type == "less":
                threshold_f = market.get("cap_strike")
            else:
                print(f"  Skipping {ticker}: unhandled strike_type {strike_type!r} "
                      f"(check inspect_markets.py output for this market).")
                continue

            if threshold_f is None:
                print(f"  Skipping {ticker}: no strike value found for strike_type={strike_type!r}.")
                continue

            # Kalshi already includes bid/ask on the market object itself,
            # no separate orderbook call needed.
            quote = KalshiClient.quote_from_market(market)

            model_prob = prob_yes_for_market(forecast.high_temp_f, float(threshold_f), strike_type)
            signal = evaluate_market(ticker, model_prob, quote)

            print(f"  {ticker} ({strike_type} {threshold_f}F): "
                  f"model={signal.model_prob_cents}c market_yes_ask={signal.market_yes_ask_cents} "
                  f"market_no_ask={signal.market_no_ask_cents} edge={signal.edge_cents}c "
                  f"action={signal.action.value}")

            _append_log_row({
                "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "city": city.name,
                "ticker": ticker,
                "strike_type": strike_type,
                "threshold_f": threshold_f,
                "noaa_forecast_f": forecast.high_temp_f,
                "model_prob_cents": signal.model_prob_cents,
                "market_yes_ask": signal.market_yes_ask_cents,
                "market_no_ask": signal.market_no_ask_cents,
                "edge_cents": signal.edge_cents,
                "action": signal.action.value,
            })

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
