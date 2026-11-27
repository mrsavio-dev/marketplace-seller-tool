"""Core data types shared by the pricing engine, config and API layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class Listing:
    """One of your offers, as the bot sees it.

    ``price`` is what you charge now. ``floor_price`` is the hard minimum the bot
    may set; it is never crossed, whatever competitors do. ``ceiling_price`` is
    the highest price the bot may set when competitors rise; without one, a raise
    is treated as uncapped and live mode refuses it unless the listing explicitly
    opts in with ``allow_uncapped_raise``.
    """

    offer_id: str
    title: str
    category: str
    price: Decimal
    floor_price: Decimal
    ceiling_price: Decimal | None = None
    allow_uncapped_raise: bool = False
    game: str = ""
    currency: str = "USD"


@dataclass(frozen=True)
class CompetitorOffer:
    """A competing offer for the same listing."""

    seller: str
    price: Decimal
    quantity: int = 0


@dataclass(frozen=True)
class PriceDecision:
    """The outcome of one pricing evaluation.

    ``action`` is ``"drop"`` (move down), ``"raise"`` (move up) or ``"hold"``
    (leave the price alone). ``reason`` is a stable machine-readable code;
    ``detail`` is the human sentence.
    """

    offer_id: str
    action: str
    current_price: Decimal
    target_price: Decimal
    reason: str
    detail: str = ""
    best_competitor: Decimal | None = None

    @property
    def changed(self) -> bool:
        return self.action in ("drop", "raise") and self.target_price != self.current_price


@dataclass
class Config:
    """Parsed bot configuration."""

    currency: str = "USD"
    allowed_categories: list[str] = field(default_factory=lambda: ["Top Up"])
    tick: Decimal = Decimal("0.01")
    poll_interval_seconds: int = 30
    undercut_on_tie: bool = True
    endpoints_verified: bool = False
    listings: list[Listing] = field(default_factory=list)
    offer_path: str = ""
    offer_price_path: str = ""
