"""
Thin client around Kalshi's Trade API v2.

Market-data endpoints (get markets, get orderbook) are public and need no
auth. Order placement requires an API key + RSA-signed requests.

Docs: https://trading-api.readme.io/reference/getting-started
Get your API key + private key from your Kalshi account settings.
Use KALSHI_DEMO_BASE_URL while paper trading -- same interface, fake money.
"""

import base64
import time
from dataclasses import dataclass

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from .config import KALSHI_BASE_URL


@dataclass
class OrderbookLevel:
    price_cents: int
    quantity: int


@dataclass
class MarketQuote:
    ticker: str
    yes_bid: int | None   # cents
    yes_ask: int | None   # cents
    no_bid: int | None
    no_ask: int | None
    volume: int


class KalshiClient:
    def __init__(self, api_key_id: str | None = None, private_key_path: str | None = None,
                 base_url: str = KALSHI_BASE_URL):
        self.base_url = base_url
        self.api_key_id = api_key_id
        self.session = requests.Session()

        self._private_key = None
        if private_key_path:
            with open(private_key_path, "rb") as f:
                self._private_key = serialization.load_pem_private_key(f.read(), password=None)

    # ---------- auth ----------

    def _signed_headers(self, method: str, path: str) -> dict:
        """Builds Kalshi's required auth headers for private endpoints."""
        if not (self.api_key_id and self._private_key):
            raise RuntimeError("API key + private key required for this endpoint (order placement).")

        timestamp_ms = str(int(time.time() * 1000))
        message = f"{timestamp_ms}{method}{path}".encode("utf-8")

        signature = self._private_key.sign(
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
            hashes.SHA256(),
        )

        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode("utf-8"),
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
        }

    # ---------- public market data (no auth needed) ----------

    def get_markets(self, series_ticker: str, status: str = "open") -> list[dict]:
        path = "/markets"
        resp = self.session.get(f"{self.base_url}{path}",
                                 params={"series_ticker": series_ticker, "status": status},
                                 timeout=10)
        resp.raise_for_status()
        return resp.json()["markets"]

    def get_orderbook(self, ticker: str) -> MarketQuote:
        path = f"/markets/{ticker}/orderbook"
        resp = self.session.get(f"{self.base_url}{path}", timeout=10)
        resp.raise_for_status()
        book = resp.json()["orderbook"]

        yes_levels = book.get("yes") or []
        no_levels = book.get("no") or []

        return MarketQuote(
            ticker=ticker,
            yes_bid=max((lvl[0] for lvl in yes_levels), default=None),
            yes_ask=(100 - max((lvl[0] for lvl in no_levels), default=100)) if no_levels else None,
            no_bid=max((lvl[0] for lvl in no_levels), default=None),
            no_ask=(100 - max((lvl[0] for lvl in yes_levels), default=100)) if yes_levels else None,
            volume=sum(lvl[1] for lvl in yes_levels) + sum(lvl[1] for lvl in no_levels),
        )

    # ---------- private: order placement (needs auth) ----------

    def place_order(self, ticker: str, side: str, action: str, count: int, price_cents: int) -> dict:
        """
        side: "yes" or "no"
        action: "buy" or "sell"
        price_cents: limit price in cents (1-99)

        NOTE: this hits whatever base_url the client was configured with --
        point it at KALSHI_DEMO_BASE_URL to paper trade, KALSHI_BASE_URL to
        go live. Never hardcode live trading in code you're still testing.
        """
        path = "/portfolio/orders"
        headers = self._signed_headers("POST", path)
        body = {
            "ticker": ticker,
            "side": side,
            "action": action,
            "count": count,
            "type": "limit",
            "yes_price" if side == "yes" else "no_price": price_cents,
        }
        resp = self.session.post(f"{self.base_url}{path}", json=body, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
