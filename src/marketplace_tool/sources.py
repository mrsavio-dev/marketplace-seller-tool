"""Where competitor prices come from.

The repricing engine does not care. Today the only source that can run is a JSON
file you fill in (or that a scraper writes). The marketplace-backed source is
left as an explicit gap rather than a guess, because Eldorado does not publish a
competitor-offer endpoint in its public documentation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from .models import CompetitorOffer, Listing
from .pricing import parse_price


class CompetitorSource(Protocol):
    def prices_for(self, listing: Listing) -> list[CompetitorOffer]: ...


class JsonFileSource:
    """Read competitor prices from a JSON file keyed by offer_id.

    Shape::

        {"OFFER-ID": [{"seller": "shop-a", "price": "12.34", "quantity": 10}]}
    """

    def __init__(self, path: str | Path) -> None:
        self._data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(self._data, dict):
            raise ValueError("competitor file root must be a JSON object")

    def prices_for(self, listing: Listing) -> list[CompetitorOffer]:
        rows = self._data.get(listing.offer_id, [])
        offers: list[CompetitorOffer] = []
        for row in rows:
            offers.append(
                CompetitorOffer(
                    seller=str(row.get("seller", "unknown")),
                    price=parse_price(row["price"]),
                    quantity=int(row.get("quantity", 0)),
                )
            )
        return offers


class MarketplaceSource:
    """Competitor prices read from the marketplace API.

    Not implemented: the endpoint that returns competing offers for a product is
    not in Eldorado's public API documentation. Until it is confirmed, this
    raises instead of guessing a path and hammering the live API with wrong calls.
    """

    def __init__(self, client: object) -> None:
        self._client = client

    def prices_for(self, listing: Listing) -> list[CompetitorOffer]:
        raise NotImplementedError(
            "marketplace competitor feed is not implemented yet; "
            "use --competitors with a JSON file, or confirm the endpoint with api@eldorado.gg"
        )
