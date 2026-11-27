"""Command line interface.

    python3 main.py validate   --config config.json
    python3 main.py plan       --config config.json --competitors competitors.json
    python3 main.py run        --config config.json --competitors competitors.json [--live]
    python3 main.py check-auth --config config.json

`plan` is the default way to use the tool: it prints every decision and changes
nothing. `run --live` is the only path that touches a marketplace.
"""

from __future__ import annotations

import argparse
import os
import sys

from .api import EldoradoApiError, EldoradoClient
from .config import load_config
from .guards import ConfigError, LiveModeRefused, require_live_ready, validate_config
from .models import Config, PriceDecision
from .pricing import decide
from .sources import CompetitorSource, JsonFileSource
from .store import DecisionLog

MARKERS = {"drop": "DROP", "raise": "RAISE", "hold": "hold"}


def _print_decision(decision: PriceDecision) -> None:
    print(
        f"[{MARKERS.get(decision.action, decision.action)}] {decision.offer_id}  "
        f"{decision.current_price} -> {decision.target_price}"
        f"  ({decision.reason}: {decision.detail})"
    )


def _decisions(config: Config, source: CompetitorSource) -> list[PriceDecision]:
    return [
        decide(
            listing,
            source.prices_for(listing),
            config.allowed_categories,
            config.tick,
            config.undercut_on_tie,
        )
        for listing in config.listings
    ]


def _summary(decisions: list[PriceDecision]) -> str:
    drops = sum(1 for d in decisions if d.action == "drop")
    raises = sum(1 for d in decisions if d.action == "raise")
    return (
        f"{len(decisions)} listing(s): {drops} would drop, {raises} would raise, "
        f"{len(decisions) - drops - raises} hold"
    )


def cmd_validate(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    validate_config(config)
    print(f"config OK: {len(config.listings)} listing(s), categories {config.allowed_categories}")
    for listing in config.listings:
        ceiling = listing.ceiling_price if listing.ceiling_price is not None else "none"
        print(
            f"  {listing.offer_id}  {listing.title or '(no title)'}  {listing.category}  "
            f"price {listing.price}  floor {listing.floor_price}  ceiling {ceiling}"
        )
    if not config.endpoints_verified:
        print("note: endpoints_verified is false, so --live will be refused")
    uncapped = [
        listing.offer_id
        for listing in config.listings
        if listing.ceiling_price is None and not listing.allow_uncapped_raise
    ]
    if uncapped:
        print(f"note: no ceiling on {', '.join(uncapped)}; live mode will refuse their raises")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    validate_config(config)
    source = JsonFileSource(args.competitors)
    log = DecisionLog(args.log)
    decisions = _decisions(config, source)
    for decision in decisions:
        _print_decision(decision)
        log.record(decision, applied=False)
    print(f"\n{_summary(decisions)}. Nothing was sent to any marketplace.")
    print(f"decisions logged to {args.log}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    validate_config(config)
    source = JsonFileSource(args.competitors)
    decisions = _decisions(config, source)
    log = DecisionLog(args.log)

    if not args.live:
        for decision in decisions:
            _print_decision(decision)
            log.record(decision, applied=False)
        print(f"\ndry run: {_summary(decisions)}. Nothing sent; add --live to apply.")
        return 0

    client_id = os.environ.get("ELDORADO_CLIENT_ID")
    client_secret = os.environ.get("ELDORADO_CLIENT_SECRET")
    try:
        require_live_ready(config, client_id, client_secret)
    except LiveModeRefused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2

    client = EldoradoClient(client_id or "", client_secret or "")
    failures = 0
    for decision in decisions:
        if not decision.changed:
            _print_decision(decision)
            log.record(decision, applied=False)
            continue
        try:
            client.set_price(
                config.offer_path, config.offer_price_path, decision.offer_id, decision.target_price
            )
        except EldoradoApiError as exc:
            failures += 1
            print(f"[FAIL] {decision.offer_id}: {exc}", file=sys.stderr)
            log.record(decision, applied=False)
            continue
        print(
            f"[LIVE] {decision.offer_id}  {decision.current_price} -> {decision.target_price}"
            f"  ({decision.reason})"
        )
        log.record(decision, applied=True)
    return 1 if failures else 0


def cmd_check_auth(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    client_id = os.environ.get("ELDORADO_CLIENT_ID")
    client_secret = os.environ.get("ELDORADO_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("set ELDORADO_CLIENT_ID and ELDORADO_CLIENT_SECRET first", file=sys.stderr)
        return 2
    client = EldoradoClient(client_id, client_secret)
    try:
        token = client.access_token()
    except EldoradoApiError as exc:
        print(f"authentication failed: {exc}", file=sys.stderr)
        return 1
    print(
        "authentication OK: got an access token "
        f"({len(token)} chars, expires in under 15 minutes). No offer was touched."
    )
    print(f"config endpoints_verified: {config.endpoints_verified}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="marketplace-tool", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="check the config without touching anything")
    p_validate.add_argument("--config", required=True)
    p_validate.set_defaults(func=cmd_validate)

    p_plan = sub.add_parser("plan", help="print the pricing decisions, change nothing")
    p_plan.add_argument("--config", required=True)
    p_plan.add_argument("--competitors", required=True)
    p_plan.add_argument("--log", default="data/decisions.jsonl")
    p_plan.set_defaults(func=cmd_plan)

    p_run = sub.add_parser("run", help="evaluate once and optionally apply price changes")
    p_run.add_argument("--config", required=True)
    p_run.add_argument("--competitors", required=True)
    p_run.add_argument("--log", default="data/decisions.jsonl")
    p_run.add_argument("--live", action="store_true", help="apply drops and raises to the live marketplace")
    p_run.set_defaults(func=cmd_run)

    p_auth = sub.add_parser("check-auth", help="verify Eldorado credentials without touching offers")
    p_auth.add_argument("--config", required=True)
    p_auth.set_defaults(func=cmd_check_auth)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
