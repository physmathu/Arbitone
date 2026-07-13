"""
Configuration for the Arbitone weather market maker.

Add/remove cities here. `noaa_point` is the lat/lon NOAA uses to look up
the forecast grid; `kalshi_series` is the Kalshi series ticker prefix for
that city's daily high-temperature markets (you'll need to confirm exact
tickers against Kalshi's current market list, since these change).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CityConfig:
    name: str
    noaa_lat: float
    noaa_lon: float
    kalshi_series_ticker: str  # e.g. "KXHIGHNY" - confirm on kalshi.com


CITIES = [
    CityConfig(name="New York", noaa_lat=40.7128, noaa_lon=-74.0060, kalshi_series_ticker="KXHIGHNY"),
    CityConfig(name="Chicago", noaa_lat=41.8781, noaa_lon=-87.6298, kalshi_series_ticker="KXHIGHCHI"),
    CityConfig(name="Austin", noaa_lat=30.2672, noaa_lon=-97.7431, kalshi_series_ticker="KXHIGHAUS"),
    CityConfig(name="Miami", noaa_lat=25.7617, noaa_lon=-80.1918, kalshi_series_ticker="KXHIGHMIA"),
]

# --- API config ---
NOAA_BASE_URL = "https://api.weather.gov"
NOAA_USER_AGENT = "arbitone-weather-mm ([email protected])"  # NOAA requires a UA with contact info

KALSHI_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"  # production
KALSHI_DEMO_BASE_URL = "https://demo-api.kalshi.co/trade-api/v2"   # paper trading

# --- Strategy config ---
EDGE_THRESHOLD_CENTS = 4          # minimum model-vs-market gap (in cents of probability) to act on
MAX_POSITION_PER_MARKET = 10      # contracts
MAX_DAILY_LOSS_CENTS = 5000       # kill switch trigger, in cents ($50)
FORECAST_STD_DEV_F = 3.5          # assumed std dev (°F) around NOAA point forecast, used to build a probability curve
