# Architecture

## Layers

```
config.json  ->  config.py  ->  Listing objects
competitors.json -> sources.py -> CompetitorOffer lists
                       |
                  pricing.py  (pure rule)
                       |
                 PriceDecision
                    /      \
             store.py     api.py (live mode only)
```

- **pricing.py** is pure: same inputs, same decision, no clock and no network. Everything that
  decides money is testable without a marketplace.
- **guards.py** validates the config before anything runs, and gates live mode. Two independent
  conditions are required to change a real price: `--live` on the command line and
  `endpoints_verified: true` in the config, plus credentials in the environment.
- **sources.py** isolates where competitor prices come from. Today: a JSON file. Later: the
  marketplace feed, once its endpoint is confirmed. A missing feed is an explicit
  `NotImplementedError`, never a guessed URL.
- **api.py** owns authentication and transport. It refreshes the 15-minute token automatically.
- **store.py** appends every decision to `data/decisions.jsonl` with the reason and whether it was
  applied, so any price on the account can be explained afterwards.

## Deliberate safety choices

- The floor is enforced in the engine, not in the caller, so no code path can go under it.
- A raise is bounded by the listing's ceiling. Without a ceiling the engine still computes the raise
  and labels it `raise_uncapped`, and live mode refuses it rather than guess how high the seller is
  willing to go.
- Ties are explicit: `undercut_on_tie` (default true) means the bot takes the price one cent under a
  competitor who matches it. Turning it off holds instead.
- Categories outside the allowlist are skipped before any competitor data is read.
- Live mode is refused, not warned about, when endpoints are unverified or credentials are missing.
- The decision log records holds, drops and raises, so "why did it not react?" is answerable.

## What a scheduler would add

A loop that polls competitor prices every `poll_interval_seconds`, calls `decide`, and applies drops.
It is not built yet because the competitor feed is the blocking dependency, not the loop.
