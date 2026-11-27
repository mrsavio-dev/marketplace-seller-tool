import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from marketplace_tool.config import load_config
from marketplace_tool.guards import ConfigError
from marketplace_tool.sources import JsonFileSource

CONFIG = {
    "currency": "USD",
    "allowed_categories": ["Top Up"],
    "tick": "0.01",
    "poll_interval_seconds": 30,
    "endpoints_verified": False,
    "listings": [
        {
            "offer_id": "OF-123",
            "title": "1000 UC PUBG",
            "game": "PUBG Mobile",
            "category": "Top Up",
            "price": "12.50",
            "floor_price": "11.00",
            "ceiling_price": "18.00",
        }
    ],
}


class ConfigTest(unittest.TestCase):
    def test_loads_listings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(CONFIG), encoding="utf-8")
            cfg = load_config(path)
        self.assertEqual(len(cfg.listings), 1)
        self.assertEqual(cfg.listings[0].price, Decimal("12.50"))
        self.assertEqual(cfg.listings[0].ceiling_price, Decimal("18.00"))
        self.assertTrue(cfg.undercut_on_tie)
        self.assertEqual(cfg.tick, Decimal("0.01"))
        self.assertFalse(cfg.endpoints_verified)

    def test_missing_field_raises(self):
        broken = json.loads(json.dumps(CONFIG))
        del broken["listings"][0]["floor_price"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(broken), encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)


class JsonSourceTest(unittest.TestCase):
    def test_reads_competitor_prices(self):
        data = {"OF-123": [{"seller": "shop-a", "price": "12.10"}, {"seller": "shop-b", "price": "12.00"}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "competitors.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            source = JsonFileSource(path)
        listing = type("L", (), {"offer_id": "OF-123"})()
        offers = source.prices_for(listing)
        self.assertEqual(len(offers), 2)
        self.assertEqual(offers[1].price, Decimal("12.00"))

    def test_unknown_listing_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "competitors.json"
            path.write_text("{}", encoding="utf-8")
            source = JsonFileSource(path)
        listing = type("L", (), {"offer_id": "MISSING"})()
        self.assertEqual(source.prices_for(listing), [])


if __name__ == "__main__":
    unittest.main()
