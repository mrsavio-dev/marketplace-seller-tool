# Marketplace Seller Tool (working name)

An early-stage tool for marketplace sellers. Connect a selling platform's API credentials and manage
offers, prices and stock from one place.

**Status: v0.2, early development.** This repository currently contains one working module: a
**repricing engine** that keeps your offers one cent below the cheapest competitor, moving down when
competitors drop and up when they rise, without ever going below the floor price you set or above the
ceiling you set. The rest of the tool (offer management, stock tracking, message auto-reply) is
planned, not built. See [docs/ROADMAP.md](docs/ROADMAP.md).

The first supported marketplace is [Eldorado](https://eldorado.gg).

**Scope of this version:** Top Up offers only, one marketplace, price changes driven by competitor
prices. Boosting, other categories, order handling, stock tracking and message auto-reply are not in
this version.

## What works today

- A pricing engine that is pure, deterministic and fully unit-tested: given your price, your floor,
  your ceiling and the competitors' prices, it returns one decision (drop / raise / hold) and the
  exact target price.
- Category allowlist, so the bot only touches the categories you list (default: `Top Up`).
- Dry-run by default. Nothing is ever sent to a marketplace unless you pass `--live` **and** the config
  explicitly marks the API endpoints as verified, and every listing that can raise has a ceiling.
- A local JSONL audit log of every decision, so price changes are reviewable after the fact.
- The Eldorado authentication flow (client credentials to a 15-minute access token), implemented
  against their published instructions, plus a `check-auth` command that proves credentials work
  without touching any offer.
- Pluggable competitor price source: a JSON file today, the marketplace feed once its endpoint is
  confirmed.

## What is not built yet

- Offer create/update/delete and bulk CSV import.
- Stock and quantity management.
- Auto-reply to customer messages. **Eldorado's Seller API does not cover messages** (their help
  article lists messages, disputes and feedback as out of scope), so this needs a different route.
- Order handling and invoices.
- Any hosted service, scheduler or dashboard.

## Quickstart

Requires Python 3.10+. No third-party dependencies.

```bash
# 1. Copy the example config and fill in your real offer IDs, prices and floors
cp config.example.json config.json

# 2. Describe what competitors currently charge for the same listing
cp competitors.example.json competitors.json

# 3. Dry run: prints what it would do, changes nothing
python3 main.py plan --config config.json --competitors competitors.json

# 4. Tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

No credentials yet? `examples/demo-config.json` and `examples/demo-competitors.json` are synthetic
data that runs out of the box:

```bash
python3 main.py plan --config examples/demo-config.json --competitors examples/demo-competitors.json
```

Live mode, once you have credentials from Eldorado (Dashboard > Seller API):

```bash
export ELDORADO_CLIENT_ID='...'
export ELDORADO_CLIENT_SECRET='...'
python3 main.py check-auth --config config.json
python3 main.py run --config config.json --competitors competitors.json --live
```

Live mode is refused unless `config.json` sets `"endpoints_verified": true`. Eldorado publishes the
authentication flow but not the offer endpoint paths publicly; confirm them with their API team
(api@eldorado.gg) and record them in the config before enabling live mode. There is **no test
environment** on Eldorado: every live request changes real offers.

## How the pricing rule works

1. Filter to the allowed categories. Anything else is ignored.
2. Take the cheapest competitor price for the same listing.
3. Aim for `cheapest - tick` (one cent by default). This is bidirectional: below your price it is a
   drop, above it a raise, so the one-cent undercut is kept in both directions.
4. Never aim below your floor. If the target would cross it, the floor is the target.
5. Never aim above your ceiling, when one is set. A raise with no ceiling is reported as
   `raise_uncapped` and live mode refuses it.
6. If the target equals your current price, hold.

Ties: if your price equals the cheapest competitor, `undercut_on_tie` decides. It is `true` by
default, so the bot drops one cent to become the cheapest. Set it to `false` to hold on a tie.

The engine refuses to produce a price below the floor or above the ceiling, under any competitor
input. See `src/marketplace_tool/pricing.py`.

## Project layout

```
src/marketplace_tool/
  models.py    Listing, CompetitorOffer, PriceDecision
  pricing.py   the repricing rule
  guards.py    config and listing validation, live-mode gate
  config.py    JSON config loading
  api.py       Eldorado client: token flow + generic calls
  sources.py   where competitor prices come from
  store.py     decision log
  cli.py       validate / plan / run / check-auth
docs/
  ARCHITECTURE.md
  ROADMAP.md
  ELDORADO_API.md
tests/
```

## License

No license has been chosen yet. That is a decision for the repository owner, and it has to be made
before this code is published publicly: with no license, nobody else has the right to reuse it.

Not affiliated with or endorsed by Eldorado.
