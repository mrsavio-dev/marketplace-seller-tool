"""The repricing rule.

Pure functions only: no network, no clock, no file system. That keeps the rule
easy to test and impossible to trigger by accident.

The rule, in order:

1. Ignore any listing whose category is not on the allowlist.
2. Take the cheapest competitor price.
3. Aim for ``cheapest - tick`` (one cent by default).
4. Never aim below the listing's floor: if the target would cross it, use the floor.
5. Never aim above the listing's ceiling, when one is set.
6. If the target equals the current price, hold.

The result is bidirectional: the bot drops when competitors drop, and raises when
they rise, always keeping the one-cent undercut. A raise with no ceiling
configured is reported as ``raise_uncapped`` so the caller can refuse it in live
mode rather than guess how high the seller is willing to go.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .models import CompetitorOffer, Listing, PriceDecision

CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _normalise(value: str) -> str:
    return value.strip().lower()


def category_allowed(listing: Listing, allowed_categories: list[str]) -> bool:
    allowed = {_normalise(c) for c in allowed_categories}
    return _normalise(listing.category) in allowed


def decide(
    listing: Listing,
    competitors: list[CompetitorOffer],
    allowed_categories: list[str],
    tick: Decimal = CENT,
    undercut_on_tie: bool = True,
) -> PriceDecision:
    """Return the single pricing decision for ``listing``."""

    def hold(reason: str, detail: str, best: Decimal | None = None) -> PriceDecision:
        return PriceDecision(
            offer_id=listing.offer_id,
            action="hold",
            current_price=listing.price,
            target_price=listing.price,
            reason=reason,
            detail=detail,
            best_competitor=best,
        )

    if tick <= 0:
        raise ValueError("tick must be positive")

    if not category_allowed(listing, allowed_categories):
        return hold(
            "category_not_allowed",
            f"category {listing.category!r} is not on the allowlist",
        )

    prices = sorted(c.price for c in competitors if c.price and c.price > 0)
    if not prices:
        return hold("no_competitors", "no competitor prices available")

    best = _money(prices[0])

    if not undercut_on_tie and listing.price == best:
        return hold(
            "tied_with_cheapest",
            f"our price {listing.price} equals the cheapest competitor; undercut_on_tie is off",
            best,
        )

    target = _money(best - tick)

    floor_clamped = False
    if target < listing.floor_price:
        target = _money(listing.floor_price)
        floor_clamped = True

    ceiling_clamped = False
    if listing.ceiling_price is not None and target > listing.ceiling_price:
        target = _money(listing.ceiling_price)
        ceiling_clamped = True

    if target <= 0:
        return hold("invalid_target", f"computed target {target} is not a valid price", best)

    if target == listing.price:
        return hold("no_change", f"target {target} equals our current price", best)

    if target < listing.price:
        detail = (
            f"undercut {best} by {tick}, clamped to floor {listing.floor_price}"
            if floor_clamped
            else f"undercut {best} by {tick}"
        )
        return PriceDecision(
            offer_id=listing.offer_id,
            action="drop",
            current_price=listing.price,
            target_price=target,
            reason="undercut_floor_clamped" if floor_clamped else "undercut",
            detail=detail,
            best_competitor=best,
        )

    if listing.ceiling_price is None:
        reason = "raise_uncapped"
        detail = f"competitor rose to {best}; raising to keep the undercut, but no ceiling is set"
    elif ceiling_clamped:
        reason = "raise_ceiling_clamped"
        detail = f"competitor rose to {best}; raise clamped to ceiling {listing.ceiling_price}"
    else:
        reason = "raise_to_undercut"
        detail = f"competitor rose to {best}; raising to stay {tick} below"
    return PriceDecision(
        offer_id=listing.offer_id,
        action="raise",
        current_price=listing.price,
        target_price=target,
        reason=reason,
        detail=detail,
        best_competitor=best,
    )


def parse_price(value: object) -> Decimal:
    """Parse a price from JSON (string or number) into a 2-decimal Decimal."""

    if isinstance(value, Decimal):
        return _money(value)
    if isinstance(value, bool):
        raise InvalidOperation("boolean is not a price")
    try:
        return _money(Decimal(str(value)))
    except (InvalidOperation, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError(f"invalid price: {value!r}") from exc
