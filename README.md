# Arbitone Weather Market Maker

A weather-focused market maker for Kalshi: pulls NOAA forecasts, converts
them into a fair-value probability for temperature threshold contracts,
compares that to what Kalshi's market is currently pricing, and flags/paper
trades the gaps.

## How it works

```
NOAA forecast  ─┐
                 ├──> fair_value.py (probability model) ──┐
Kalshi orderbook┘                                          ├──> signal_engine.py ──> paper_trader.py
                                                             │
                                                    (compares model vs market)
```

## Project structure

- `config.py` — cities tracked, API URLs, strategy thresholds (edit this first)
- `noaa_client.py` — pulls forecast data from NOAA's free public API
- `kalshi_client.py` — pulls Kalshi orderbooks + places orders (RSA-signed)
- `fair_value.py` — turns a forecast into a probability curve
- `signal_engine.py` — compares model probability to market price, flags edge
- `paper_trader.py` — simulated ledger with position limits + kill switch
- `mock_data.py` — fake data so you can run/test everything offline
- `main.py` — wires it all together (currently using mock data)

## Running the demo (no API keys needed)

```bash
pip install requests cryptography
python -m arbitone_weather.main
```

This runs the full pipeline against mock forecasts and mock Kalshi quotes
so you can see the logic work end-to-end before touching any real APIs.

## Going live with real data

### 1. NOAA (no signup needed)
`noaa_client.py` is ready to use as-is. Just update `NOAA_USER_AGENT` in
`config.py` with your real contact info (NOAA asks for this, it's not
authentication, just courtesy/rate-limit tracking).

### 2. Kalshi
1. Create a Kalshi account, generate an API key + private key from account
   settings.
2. Look up the actual current market tickers for each city's weather
   series — the ones in `config.py`/`mock_data.py` are illustrative
   placeholders, Kalshi's real tickers change as new contracts open.
3. Point `KalshiClient` at `KALSHI_DEMO_BASE_URL` first (paper trading on
   Kalshi's own demo environment, not just this local simulation) before
   ever using `KALSHI_BASE_URL` (real money).

### 3. Replace mock calls in `main.py`
Swap `MOCK_FORECASTS`/`MOCK_MARKETS` lookups for real `NOAAClient` and
`KalshiClient` calls, looping over `config.CITIES`.

## Before risking real money

- Calibrate `FORECAST_STD_DEV_F` in `config.py` against actual historical
  NOAA forecast error for each city — 3.5°F is a rough placeholder, not a
  real number.
- Run the paper-trading ledger for at least a few weeks of real (not mock)
  data before considering live capital.
- Tune `EDGE_THRESHOLD_CENTS`, `MAX_POSITION_PER_MARKET`, and
  `MAX_DAILY_LOSS_CENTS` in `config.py` to your actual risk tolerance.
- This fair-value model is intentionally simple (a normal distribution
  around a single point forecast). A stronger version would use NOAA's
  probabilistic/ensemble products directly rather than approximating a
  distribution from one number.

## Disclaimer

This is a starting framework, not a validated trading strategy. Past
mock/paper performance proves nothing about real-money performance. Treat
the paper-trading phase as mandatory, not optional.
