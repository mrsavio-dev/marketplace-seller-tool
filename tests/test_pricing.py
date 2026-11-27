import unittest
from decimal import Decimal

from marketplace_tool.models import CompetitorOffer, Listing
from marketplace_tool.pricing import decide, parse_price

ALLOWED = ["Top Up"]


def listing(price="12.50", floor="11.00", ceiling=None, category="Top Up", offer_id="A1"):
    return Listing(
        offer_id=offer_id,
        title="1000 UC PUBG",
        category=category,
        price=Decimal(price),
        floor_price=Decimal(floor),
        ceiling_price=None if ceiling is None else Decimal(ceiling),
    )


def comps(*prices):
    return [CompetitorOffer(seller=f"s{i}", price=Decimal(p)) for i, p in enumerate(prices)]


class UndercutTest(unittest.TestCase):
    def test_drops_one_cent_under_cheapest(self):
        d = decide(listing(), comps("12.00", "12.40"), ALLOWED)
        self.assertEqual(d.action, "drop")
        self.assertEqual(d.target_price, Decimal("11.99"))
        self.assertEqual(d.reason, "undercut")
        self.assertTrue(d.changed)

    def test_uses_cheapest_competitor(self):
        d = decide(listing(price="20.00", floor="10.00"), comps("15.00", "14.00", "18.00"), ALLOWED)
        self.assertEqual(d.target_price, Decimal("13.99"))
        self.assertEqual(d.best_competitor, Decimal("14.00"))

    def test_no_competitors_holds(self):
        self.assertEqual(decide(listing(), comps(), ALLOWED).reason, "no_competitors")

    def test_zero_and_negative_prices_ignored(self):
        self.assertEqual(decide(listing(), comps("0", "-5"), ALLOWED).reason, "no_competitors")


class TieTest(unittest.TestCase):
    def test_tie_drops_one_cent_by_default(self):
        d = decide(listing(price="10.00", floor="9.00"), comps("10.00", "11.00"), ALLOWED)
        self.assertEqual(d.action, "drop")
        self.assertEqual(d.target_price, Decimal("9.99"))

    def test_tie_holds_when_undercut_on_tie_is_off(self):
        d = decide(listing(price="10.00", floor="9.00"), comps("10.00"), ALLOWED, undercut_on_tie=False)
        self.assertEqual(d.action, "hold")
        self.assertEqual(d.reason, "tied_with_cheapest")
        self.assertEqual(d.target_price, Decimal("10.00"))


class RaiseTest(unittest.TestCase):
    def test_raises_when_competitors_rise(self):
        d = decide(listing(price="11.00", floor="10.00", ceiling="20.00"), comps("15.00"), ALLOWED)
        self.assertEqual(d.action, "raise")
        self.assertEqual(d.target_price, Decimal("14.99"))
        self.assertEqual(d.reason, "raise_to_undercut")
        self.assertTrue(d.changed)

    def test_raise_is_clamped_by_ceiling(self):
        d = decide(listing(price="11.00", floor="10.00", ceiling="13.00"), comps("15.00"), ALLOWED)
        self.assertEqual(d.action, "raise")
        self.assertEqual(d.target_price, Decimal("13.00"))
        self.assertEqual(d.reason, "raise_ceiling_clamped")

    def test_raise_without_ceiling_is_flagged_uncapped(self):
        d = decide(listing(price="11.00", floor="10.00"), comps("15.00"), ALLOWED)
        self.assertEqual(d.action, "raise")
        self.assertEqual(d.target_price, Decimal("14.99"))
        self.assertEqual(d.reason, "raise_uncapped")

    def test_no_raise_when_already_one_cent_under(self):
        d = decide(listing(price="14.99", floor="10.00", ceiling="20.00"), comps("15.00"), ALLOWED)
        self.assertEqual(d.action, "hold")
        self.assertEqual(d.reason, "no_change")


class FloorTest(unittest.TestCase):
    def test_floor_clamps_the_undercut(self):
        d = decide(listing(price="12.50", floor="11.50"), comps("11.20"), ALLOWED)
        self.assertEqual(d.action, "drop")
        self.assertEqual(d.target_price, Decimal("11.50"))
        self.assertEqual(d.reason, "undercut_floor_clamped")

    def test_never_below_floor_when_competitor_is_under_it(self):
        d = decide(listing(price="12.50", floor="11.50"), comps("9.00"), ALLOWED)
        self.assertEqual(d.target_price, Decimal("11.50"))

    def test_holds_when_already_at_floor_and_competitor_under_it(self):
        d = decide(listing(price="11.50", floor="11.50"), comps("10.00"), ALLOWED)
        self.assertEqual(d.action, "hold")
        self.assertEqual(d.reason, "no_change")

    def test_one_cent_above_floor_moves_to_floor(self):
        d = decide(listing(price="11.51", floor="11.50"), comps("11.50"), ALLOWED)
        self.assertEqual(d.action, "drop")
        self.assertEqual(d.target_price, Decimal("11.50"))


class AllowlistTest(unittest.TestCase):
    def test_other_category_is_ignored(self):
        d = decide(listing(category="Accounts"), comps("5.00"), ALLOWED)
        self.assertEqual(d.reason, "category_not_allowed")
        self.assertEqual(d.target_price, d.current_price)

    def test_allowlist_is_case_insensitive(self):
        self.assertEqual(decide(listing(category="top up"), comps("12.00"), ALLOWED).action, "drop")

    def test_multiple_allowed_categories(self):
        d = decide(listing(category="Currency"), comps("12.00"), ["Top Up", "Currency"])
        self.assertEqual(d.action, "drop")


class ParsePriceTest(unittest.TestCase):
    def test_string_and_number(self):
        self.assertEqual(parse_price("12.349"), Decimal("12.35"))
        self.assertEqual(parse_price(7), Decimal("7.00"))

    def test_boolean_rejected(self):
        with self.assertRaises(Exception):
            parse_price(True)


if __name__ == "__main__":
    unittest.main()
