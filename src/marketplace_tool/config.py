"""Load and validate the JSON config."""

from __future__ import annotations

import json
from pathlib import Path

from .guards import ConfigError
from .models import Config, Listing
from .pricing import parse_price


def _optional_price(value: object) -> object:
    return None if value in (None, "", "null") else parse_price(value)


def load_config(path: str | Path) -> Config:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigError("config root must be a JSON object")

    listings: list[Listing] = []
    for item in raw.get("listings", []):
        if not isinstance(item, dict):
            raise ConfigError("each listing must be a JSON object")
        try:
            listings.append(
                Listing(
                    offer_id=str(item["offer_id"]),
                    title=str(item.get("title", "")),
                    category=str(item.get("category", "")),
                    game=str(item.get("game", "")),
                    currency=str(item.get("currency", raw.get("currency", "USD"))),
                    price=parse_price(item["price"]),
                    floor_price=parse_price(item["floor_price"]),
                    ceiling_price=_optional_price(item.get("ceiling_price")),
                    allow_uncapped_raise=bool(item.get("allow_uncapped_raise", False)),
                )
            )
        except KeyError as exc:
            raise ConfigError(f"listing missing required field {exc.args[0]}") from exc

    return Config(
        currency=str(raw.get("currency", "USD")),
        allowed_categories=[str(c) for c in raw.get("allowed_categories", ["Top Up"])],
        tick=parse_price(raw.get("tick", "0.01")),
        poll_interval_seconds=int(raw.get("poll_interval_seconds", 30)),
        undercut_on_tie=bool(raw.get("undercut_on_tie", True)),
        endpoints_verified=bool(raw.get("endpoints_verified", False)),
        listings=listings,
        offer_path=str(raw.get("offer_path", "")),
        offer_price_path=str(raw.get("offer_price_path", "")),
    )
