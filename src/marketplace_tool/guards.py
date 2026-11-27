"""Validation and the gate that separates a dry run from a live price change."""

from __future__ import annotations

from decimal import Decimal

from .models import Config, Listing


class ConfigError(ValueError):
    """Raised when the configuration would let the bot do something unsafe."""


class LiveModeRefused(RuntimeError):
    """Raised when live mode is requested but the safety conditions are not met."""


def validate_listing(listing: Listing) -> None:
    if not listing.offer_id or listing.offer_id.startswith("REPLACE"):
        raise ConfigError(f"{listing.title or listing.offer_id!r}: a real offer_id is required")
    if listing.price <= 0:
        raise ConfigError(f"{listing.offer_id}: price must be positive, got {listing.price}")
    if listing.floor_price <= 0:
        raise ConfigError(f"{listing.offer_id}: floor_price must be positive, got {listing.floor_price}")
    if listing.floor_price > listing.price:
        raise ConfigError(
            f"{listing.offer_id}: floor_price {listing.floor_price} is above the current price "
            f"{listing.price}; the bot would only ever hold, fix the floor first"
        )
    if listing.ceiling_price is not None:
        if listing.ceiling_price < listing.price:
            raise ConfigError(
                f"{listing.offer_id}: ceiling_price {listing.ceiling_price} is below the current "
                f"price {listing.price}; a raise would immediately cut your own price"
            )
        if listing.ceiling_price < listing.floor_price:
            raise ConfigError(
                f"{listing.offer_id}: ceiling_price {listing.ceiling_price} is below floor_price "
                f"{listing.floor_price}"
            )
    if listing.price.quantize(Decimal("0.01")) != listing.price:
        raise ConfigError(f"{listing.offer_id}: price {listing.price} has more than 2 decimals")


def validate_config(config: Config) -> None:
    if not config.listings:
        raise ConfigError("config has no listings")
    if not config.allowed_categories:
        raise ConfigError("allowed_categories is empty; the bot would refuse every listing")
    if config.tick <= 0:
        raise ConfigError("tick must be positive")
    if config.poll_interval_seconds < 5:
        raise ConfigError("poll_interval_seconds below 5 would hammer the marketplace API")
    seen: set[str] = set()
    for listing in config.listings:
        validate_listing(listing)
        if listing.offer_id in seen:
            raise ConfigError(f"duplicate offer_id {listing.offer_id}")
        seen.add(listing.offer_id)


def require_live_ready(config: Config, client_id: str | None, client_secret: str | None) -> None:
    """Refuse live mode unless endpoints are confirmed, credentials exist, and
    every listing that can raise has a ceiling (or explicitly opted out)."""

    if not config.endpoints_verified:
        raise LiveModeRefused(
            "refusing live mode: config.endpoints_verified is false. Eldorado's offer endpoint "
            "paths are not published publicly; confirm them with api@eldorado.gg and record them "
            "in the config before changing real prices."
        )
    if not config.offer_path or not config.offer_price_path:
        raise LiveModeRefused("refusing live mode: offer_path / offer_price_path are not configured")
    if not client_id or not client_secret:
        raise LiveModeRefused(
            "refusing live mode: set ELDORADO_CLIENT_ID and ELDORADO_CLIENT_SECRET in the environment"
        )
    uncapped = [
        listing.offer_id
        for listing in config.listings
        if listing.ceiling_price is None and not listing.allow_uncapped_raise
    ]
    if uncapped:
        raise LiveModeRefused(
            "refusing live mode: these listings can raise but have no ceiling_price and no "
            f"allow_uncapped_raise: {', '.join(uncapped)}. Set the highest price you are willing "
            "to charge before letting the bot raise a live price."
        )
