# Roadmap

Honest status: only the repricing engine exists. Everything below it is planned.

## v0.1 (this repository)

- [x] Repricing rule: one cent under the cheapest competitor in both directions, never
      below the floor, never above the ceiling.
- [x] Category allowlist, config validation, live-mode gate.
- [x] Eldorado token authentication.
- [x] Decision log.
- [x] Tests.

## v0.2

- [ ] Confirm offer endpoints with Eldorado, then wire `set_price` and `list_offers`.
- [ ] Read competitor prices from the marketplace instead of a JSON file.
- [ ] Polling loop with backoff, and a `--max-changes-per-hour` circuit breaker.
- [ ] Dry-run report comparing what the bot would have done against what you actually charged.

## v0.3

- [ ] Offer management: pause/resume, quantity, delivery time, bulk CSV.
- [ ] Stock tracking: quantity thresholds per offer, alert when stock runs low.
- [ ] Multi-marketplace adapter interface (the pricing engine is marketplace-agnostic already).

## Later

- [ ] Message auto-reply. Blocked: Eldorado's Seller API does not expose messages, disputes or
  feedback. Needs the website or another channel, plus a clear answer on whether automating replies
  is allowed by their terms.
- [ ] Dashboard.
- [ ] Hosted deployment.

## Non-goals

- Withdrawals, balance, payouts.
- Anything that hides price changes from the seller: every decision is logged.
