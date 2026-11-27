"""Append-only decision log.

One JSON object per line, so a price change can always be explained later.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import PriceDecision


class DecisionLog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, decision: PriceDecision, applied: bool) -> None:
        entry = {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "offer_id": decision.offer_id,
            "action": decision.action,
            "reason": decision.reason,
            "current_price": str(decision.current_price),
            "target_price": str(decision.target_price),
            "best_competitor": None if decision.best_competitor is None else str(decision.best_competitor),
            "applied": applied,
            "detail": decision.detail,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
