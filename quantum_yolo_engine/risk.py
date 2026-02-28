# quantum_yolo_engine/risk.py
from __future__ import annotations

from typing import Dict

from .models import AssetStrategy


class RiskManager:
    def __init__(self, bankroll_usd: float):
        self.bankroll_usd = bankroll_usd

    def validate_strategy_allocations(self, strategies: Dict[str, AssetStrategy]) -> None:
        total = sum(s.allocation_usd for s in strategies.values() if s.enabled)
        if total > self.bankroll_usd + 1e-9:
            raise ValueError(f"allocations ${total:.2f} exceed bankroll ${self.bankroll_usd:.2f}")

    def validate_entry_budget(self, strategy: AssetStrategy) -> None:
        total_entries = sum(e.quote_size_usd for e in strategy.entries)
        if total_entries > strategy.allocation_usd + 1e-9:
            raise ValueError(
                f"{strategy.product_id} entries (${total_entries:.2f}) exceed allocation (${strategy.allocation_usd:.2f})"
            )