"""
Mock NOAA + Kalshi data so you can run and test the whole pipeline offline.
Swap these out for the real NOAAClient / KalshiClient calls once you're
running this with network access and real API credentials.
"""

from .kalshi_client import MarketQuote

MOCK_FORECASTS = {
    "New York": 78.0,
    "Chicago": 71.0,
    "Austin": 96.0,
    "Miami": 89.0,
}

# ticker -> (threshold_temp_f, quote)
MOCK_MARKETS = {
    "KXHIGHNY-25JUL13-T80": (80.0, MarketQuote(
        ticker="KXHIGHNY-25JUL13-T80", yes_bid=28, yes_ask=32, no_bid=68, no_ask=72, volume=1500)),
    "KXHIGHCHI-25JUL13-T70": (70.0, MarketQuote(
        ticker="KXHIGHCHI-25JUL13-T70", yes_bid=55, yes_ask=59, no_bid=41, no_ask=45, volume=800)),
    "KXHIGHAUS-25JUL13-T95": (95.0, MarketQuote(
        ticker="KXHIGHAUS-25JUL13-T95", yes_bid=40, yes_ask=44, no_bid=56, no_ask=60, volume=2200)),
    "KXHIGHMIA-25JUL13-T90": (90.0, MarketQuote(
        ticker="KXHIGHMIA-25JUL13-T90", yes_bid=25, yes_ask=29, no_bid=71, no_ask=75, volume=650)),
}

CITY_BY_MARKET = {
    "KXHIGHNY-25JUL13-T80": "New York",
    "KXHIGHCHI-25JUL13-T70": "Chicago",
    "KXHIGHAUS-25JUL13-T95": "Austin",
    "KXHIGHMIA-25JUL13-T90": "Miami",
}
