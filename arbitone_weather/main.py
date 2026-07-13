"""
Demo run of the Arbitone weather market maker pipeline using mock data.

This proves out the logic end-to-end: forecast -> fair value -> compare to
market -> signal -> paper trade -> P&L summary.

To go live with real data:
  1. Replace the MOCK_FORECASTS lookups with real NOAAClient calls (see
     noaa_client.py) for each city in config.CITIES.
  2. Replace MOCK_MARKETS lookups with real KalshiClient.get_orderbook()
     calls for each ticker (you'll need to look up current tickers from
     Kalshi's market list for each city's weather series).
  3. Keep KalshiClient pointed at KALSHI_DEMO_BASE_URL for paper trading
     against Kalshi's own demo environment before ever touching
     KALSHI_BASE_URL (production, real money).

Run: python -m arbitone_weather.main
"""

from .fair_value import prob_high_at_or_above
from .mock_data import MOCK_FORECASTS, MOCK_MARKETS, CITY_BY_MARKET
from .paper_trader import PaperLedger
from .signal_engine import evaluate_market, SignalAction


def run():
    ledger = PaperLedger()

    print("=" * 60)
    print("ARBITONE WEATHER MARKET MAKER -- demo run (mock data)")
    print("=" * 60)

    for ticker, (threshold_f, quote) in MOCK_MARKETS.items():
        city = CITY_BY_MARKET[ticker]
        forecast_f = MOCK_FORECASTS[city]

        model_prob = prob_high_at_or_above(forecast_f, threshold_f)
        signal = evaluate_market(ticker, model_prob, quote)

        print(f"\n{city} -- {ticker}")
        print(f"  NOAA forecast high: {forecast_f}F | Contract threshold: {threshold_f}F")
        print(f"  Model fair value (YES): {signal.model_prob_cents}c")
        print(f"  Market YES ask: {signal.market_yes_ask_cents}c | "
              f"Market NO ask: {signal.market_no_ask_cents}c")
        print(f"  Edge: {signal.edge_cents}c | Action: {signal.action.value}")

        if signal.action != SignalAction.NONE:
            ledger.process_signal(signal, contracts=5)

    print("\n" + "=" * 60)
    print("PAPER TRADING LOG")
    print("=" * 60)
    for line in ledger.trade_log:
        print(f"  {line}")

    print("\n" + "=" * 60)
    print("LEDGER SUMMARY")
    print("=" * 60)
    print(ledger.summary())


if __name__ == "__main__":
    run()
