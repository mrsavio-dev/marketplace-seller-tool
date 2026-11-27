import unittest
from decimal import Decimal

from marketplace_tool.guards import (
    ConfigError,
    LiveModeRefused,
    require_live_ready,
    validate_config,
    validate_listing,
)
from marketplace_tool.models import Config, Listing


def listing(**kwargs):
    base = dict(
        offer_id="A1",
        title="1000 UC PUBG",
        category="Top Up",
        price=Decimal("12.50"),
        floor_price=Decimal("11.00"),
    )
    base.update(kwargs)
    return Listing(**base)


class ListingValidationTest(unittest.TestCase):
    def test_valid_listing_passes(self):
        validate_listing(listing())

    def test_placeholder_offer_id_rejected(self):
        with self.assertRaises(ConfigError):
            validate_listing(listing(offer_id="REPLACE_WITH_OFFER_ID"))

    def test_floor_above_price_rejected(self):
        with self.assertRaises(ConfigError):
            validate_listing(listing(floor_price=Decimal("13.00")))

    def test_zero_floor_rejected(self):
        with self.assertRaises(ConfigError):
            validate_listing(listing(floor_price=Decimal("0")))

    def test_ceiling_below_price_rejected(self):
        with self.assertRaises(ConfigError):
            validate_listing(listing(ceiling_price=Decimal("12.00")))

    def test_ceiling_below_floor_rejected(self):
        with self.assertRaises(ConfigError):
            validate_listing(listing(ceiling_price=Decimal("10.00")))

    def test_ceiling_above_price_ok(self):
        validate_listing(listing(ceiling_price=Decimal("15.00")))

    def test_three_decimals_rejected(self):
        with self.assertRaises(ConfigError):
            validate_listing(listing(price=Decimal("12.505"), floor_price=Decimal("11.00")))


class ConfigValidationTest(unittest.TestCase):
    def test_empty_listings_rejected(self):
        with self.assertRaises(ConfigError):
            validate_config(Config(listings=[]))

    def test_duplicate_offer_ids_rejected(self):
        with self.assertRaises(ConfigError):
            validate_config(Config(listings=[listing(), listing()]))

    def test_too_fast_polling_rejected(self):
        with self.assertRaises(ConfigError):
            validate_config(Config(listings=[listing()], poll_interval_seconds=1))

    def test_good_config_passes(self):
        validate_config(Config(listings=[listing()]))


class LiveGateTest(unittest.TestCase):
    def test_unverified_endpoints_refused(self):
        cfg = Config(listings=[listing()], endpoints_verified=False)
        with self.assertRaises(LiveModeRefused):
            require_live_ready(cfg, "id", "secret")

    def test_missing_credentials_refused(self):
        cfg = Config(
            listings=[listing()],
            endpoints_verified=True,
            offer_path="/x/{offer_id}",
            offer_price_path="/x/{offer_id}/price",
        )
        with self.assertRaises(LiveModeRefused):
            require_live_ready(cfg, None, None)

    def test_raise_without_ceiling_refused(self):
        cfg = Config(
            listings=[listing()],
            endpoints_verified=True,
            offer_path="/x/{offer_id}",
            offer_price_path="/x/{offer_id}/price",
        )
        with self.assertRaises(LiveModeRefused):
            require_live_ready(cfg, "id", "secret")

    def test_raise_without_ceiling_allowed_when_listing_opts_in(self):
        cfg = Config(
            listings=[listing(allow_uncapped_raise=True)],
            endpoints_verified=True,
            offer_path="/x/{offer_id}",
            offer_price_path="/x/{offer_id}/price",
        )
        require_live_ready(cfg, "id", "secret")

    def test_ready_config_passes(self):
        cfg = Config(
            listings=[listing(ceiling_price=Decimal("15.00"))],
            endpoints_verified=True,
            offer_path="/x/{offer_id}",
            offer_price_path="/x/{offer_id}/price",
        )
        require_live_ready(cfg, "id", "secret")


if __name__ == "__main__":
    unittest.main()
