"""Measure how long one pricing decision takes.

The engine's own latency is what this prints. It is not the latency of the bot:
that is dominated by how fast competitor prices can be fetched, which is a
marketplace API question, not a code question.

    python3 bench/bench_decide.py
"""

from __future__ import annotations

import pathlib
import statistics
import sys
import time
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from marketplace_tool.models import CompetitorOffer, Listing  # noqa: E402
from marketplace_tool.pricing import decide  # noqa: E402

LISTING = Listing(
    offer_id="OF-BENCH",
    title="1000 UC",
    category="Top Up",
    price=Decimal("12.50"),
    floor_price=Decimal("11.00"),
    ceiling_price=Decimal("16.00"),
)
COMPETITORS = [CompetitorOffer(seller=f"s{i}", price=Decimal("12.40") + Decimal(i) / 100) for i in range(20)]
ALLOWED = ["Top Up"]
ITERATIONS = 50_000


def main() -> int:
    samples = []
    for _ in range(ITERATIONS):
        start = time.perf_counter_ns()
        decide(LISTING, COMPETITORS, ALLOWED)
        samples.append(time.perf_counter_ns() - start)
    samples.sort()
    mean = statistics.fmean(samples) / 1000
    median = samples[len(samples) // 2] / 1000
    p95 = samples[int(len(samples) * 0.95)] / 1000
    p99 = samples[int(len(samples) * 0.99)] / 1000
    print(f"iterations: {ITERATIONS}  competitors per listing: {len(COMPETITORS)}")
    print(f"one decision: mean {mean:.2f} us, median {median:.2f} us, p95 {p95:.2f} us, p99 {p99:.2f} us")
    print(f"decisions per second, single core: {1_000_000 / mean:,.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
