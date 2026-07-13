"""
Compares the model's fair-value probability against what the market is
currently pricing, and flags actionable gaps.
"""

from dataclasses import dataclass
from enum import Enum

from .config import EDGE_THRESHOLD_CENTS
from .kalshi_client import MarketQuote


class SignalAction(Enum):
    BUY_YES = "buy_yes"    # market underprices YES relative to our model
    BUY_NO = "buy_no"      # market underprices NO (i.e. overprices YES)
    NONE = "none"


@dataclass
class Signal:
    ticker: str
    model_prob_cents: int      # our fair value, in cents (0-100)
    market_yes_ask_cents: int | None
    market_no_ask_cents: int | None
    edge_cents: int
    action: SignalAction


def evaluate_market(ticker: str, model_prob: float, quote: MarketQuote,
                     edge_threshold: int = EDGE_THRESHOLD_CENTS) -> Signal:
    """
    model_prob: our fair-value probability of YES resolving true (0.0-1.0)
    quote: current Kalshi orderbook snapshot for this market

    Logic: if buying YES at the current ask is cheaper than our fair value,
    that's edge. Same check on the NO side.
    """
    model_cents = round(model_prob * 100)

    edge_on_yes = (model_cents - quote.yes_ask) if quote.yes_ask is not None else -999
    edge_on_no = ((100 - model_cents) - quote.no_ask) if quote.no_ask is not None else -999

    if edge_on_yes >= edge_threshold and edge_on_yes >= edge_on_no:
        action = SignalAction.BUY_YES
        edge = edge_on_yes
    elif edge_on_no >= edge_threshold:
        action = SignalAction.BUY_NO
        edge = edge_on_no
    else:
        action = SignalAction.NONE
        edge = max(edge_on_yes, edge_on_no)

    return Signal(
        ticker=ticker,
        model_prob_cents=model_cents,
        market_yes_ask_cents=quote.yes_ask,
        market_no_ask_cents=quote.no_ask,
        edge_cents=edge,
        action=action,
    )
