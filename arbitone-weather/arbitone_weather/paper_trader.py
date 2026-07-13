"""
A minimal paper-trading ledger. Simulates taking the signal engine's
recommended trades at the quoted price, tracks open positions and running
P&L, and enforces the same position/loss limits you'd want live.

This does NOT touch Kalshi's real order API -- it's purely a local
simulation, so you can validate the strategy's logic and see hypothetical
performance before risking anything (paper OR real money on Kalshi's demo
environment).
"""

from dataclasses import dataclass, field

from .config import MAX_POSITION_PER_MARKET, MAX_DAILY_LOSS_CENTS
from .signal_engine import Signal, SignalAction


@dataclass
class Position:
    ticker: str
    side: str          # "yes" or "no"
    contracts: int
    avg_price_cents: int


@dataclass
class PaperLedger:
    starting_balance_cents: int = 100_000  # $1,000 fake bankroll
    balance_cents: int = 100_000
    daily_pnl_cents: int = 0
    positions: dict[str, Position] = field(default_factory=dict)
    trade_log: list[str] = field(default_factory=list)
    halted: bool = False

    def _check_kill_switch(self):
        if self.daily_pnl_cents <= -MAX_DAILY_LOSS_CENTS:
            self.halted = True
            self.trade_log.append(
                f"KILL SWITCH TRIGGERED: daily loss {self.daily_pnl_cents}c "
                f"exceeded limit {MAX_DAILY_LOSS_CENTS}c. Trading halted."
            )

    def process_signal(self, signal: Signal, contracts: int = 1):
        if self.halted:
            self.trade_log.append(f"SKIPPED {signal.ticker}: trading halted by kill switch.")
            return

        if signal.action == SignalAction.NONE:
            return

        side = "yes" if signal.action == SignalAction.BUY_YES else "no"
        price = signal.market_yes_ask_cents if side == "yes" else signal.market_no_ask_cents
        if price is None:
            return

        existing = self.positions.get(signal.ticker)
        current_size = existing.contracts if existing else 0
        if current_size + contracts > MAX_POSITION_PER_MARKET:
            self.trade_log.append(
                f"SKIPPED {signal.ticker}: would exceed max position "
                f"({current_size + contracts} > {MAX_POSITION_PER_MARKET})."
            )
            return

        cost = price * contracts
        self.balance_cents -= cost
        self.positions[signal.ticker] = Position(
            ticker=signal.ticker, side=side,
            contracts=current_size + contracts,
            avg_price_cents=price,  # simplified: not volume-weighted across fills
        )
        self.trade_log.append(
            f"BOUGHT {contracts}x {side.upper()} on {signal.ticker} @ {price}c "
            f"(edge was {signal.edge_cents}c)"
        )

    def mark_daily_pnl(self, realized_pnl_cents: int):
        """Call at end of day once contracts resolve or you mark-to-market."""
        self.daily_pnl_cents += realized_pnl_cents
        self.balance_cents += realized_pnl_cents
        self._check_kill_switch()

    def summary(self) -> str:
        lines = [
            f"Balance: ${self.balance_cents / 100:,.2f} "
            f"(started at ${self.starting_balance_cents / 100:,.2f})",
            f"Open positions: {len(self.positions)}",
            f"Daily P&L: ${self.daily_pnl_cents / 100:,.2f}",
            f"Halted: {self.halted}",
        ]
        return "\n".join(lines)
