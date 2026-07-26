# quantum_yolo_engine/validate.py
from __future__ import annotations

import math
from typing import Dict, List

from .models import PRODUCT_IDS, AssetStrategy


class StrategyValidationError(ValueError):
    """Raised with every violation found, not just the first, so callers can
    surface a complete list of problems in one pass."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def _finite(x: float) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def validate_strategy(bankroll_usd: float, strategies: Dict[str, AssetStrategy]) -> None:
    """Validates a full strategy (bankroll + all assets). Raises
    StrategyValidationError containing every violation found."""
    errors: List[str] = []

    if not _finite(bankroll_usd) or bankroll_usd <= 0:
        errors.append(f"bankroll_usd must be a positive finite number, got {bankroll_usd!r}")

    enabled_allocation_total = 0.0

    for product_id, strat in strategies.items():
        prefix = f"{product_id}: "

        if product_id not in PRODUCT_IDS:
            errors.append(f"{prefix}unsupported product_id (supported: {PRODUCT_IDS})")

        if not _finite(strat.allocation_usd) or strat.allocation_usd <= 0:
            errors.append(f"{prefix}allocation_usd must be a positive finite number, got {strat.allocation_usd!r}")
        elif strat.enabled:
            enabled_allocation_total += strat.allocation_usd

        if not _finite(strat.stop_price) or strat.stop_price <= 0:
            errors.append(f"{prefix}stop_price must be a positive finite number, got {strat.stop_price!r}")

        tp = strat.take_profit
        if not _finite(tp.tp1_price) or tp.tp1_price <= 0:
            errors.append(f"{prefix}take_profit.tp1_price must be a positive finite number")
        if not _finite(tp.tp2_price) or tp.tp2_price <= 0:
            errors.append(f"{prefix}take_profit.tp2_price must be a positive finite number")
        if not _finite(tp.tp1_fraction) or not (0 < tp.tp1_fraction <= 1):
            errors.append(f"{prefix}take_profit.tp1_fraction must satisfy 0 < fraction <= 1, got {tp.tp1_fraction!r}")
        if not _finite(tp.tp2_fraction) or not (0 < tp.tp2_fraction <= 1):
            errors.append(f"{prefix}take_profit.tp2_fraction must satisfy 0 < fraction <= 1, got {tp.tp2_fraction!r}")
        if _finite(tp.tp1_fraction) and _finite(tp.tp2_fraction):
            total_exit = tp.tp1_fraction + tp.tp2_fraction
            if total_exit > 1.0 + 1e-9:
                errors.append(
                    f"{prefix}tp1_fraction + tp2_fraction must be <= 1.0, got {total_exit!r}"
                )

        if (
            _finite(tp.tp1_price)
            and _finite(tp.tp2_price)
            and tp.tp1_price > 0
            and tp.tp2_price > 0
            and tp.tp1_price >= tp.tp2_price
        ):
            errors.append(f"{prefix}take_profit.tp1_price must be < tp2_price")

        if (
            _finite(strat.stop_price)
            and _finite(tp.tp1_price)
            and strat.stop_price > 0
            and tp.tp1_price > 0
            and strat.stop_price >= tp.tp1_price
        ):
            errors.append(f"{prefix}stop_price must be < take_profit.tp1_price")

        seen_ids = set()
        if not strat.entries:
            errors.append(f"{prefix}must have at least one entry rule")

        for entry in strat.entries:
            if entry.id in seen_ids:
                errors.append(f"{prefix}duplicate entry id {entry.id!r}")
            seen_ids.add(entry.id)

            if not _finite(entry.price) or entry.price <= 0:
                errors.append(f"{prefix}entry {entry.id!r} price must be a positive finite number")
            elif _finite(strat.stop_price) and strat.stop_price > 0 and entry.price <= strat.stop_price:
                errors.append(f"{prefix}entry {entry.id!r} price must be > stop_price")

            if not _finite(entry.quote_size_usd) or entry.quote_size_usd <= 0:
                errors.append(f"{prefix}entry {entry.id!r} quote_size_usd must be a positive finite number")

        if strat.enabled and strat.entries:
            entries_total = sum(e.quote_size_usd for e in strat.entries if _finite(e.quote_size_usd))
            if _finite(strat.allocation_usd) and entries_total > strat.allocation_usd + 1e-9:
                errors.append(
                    f"{prefix}entries total (${entries_total:.2f}) exceeds allocation_usd "
                    f"(${strat.allocation_usd:.2f})"
                )

    if _finite(bankroll_usd) and enabled_allocation_total > bankroll_usd + 1e-9:
        errors.append(
            f"total enabled allocations (${enabled_allocation_total:.2f}) exceed bankroll_usd (${bankroll_usd:.2f})"
        )

    if errors:
        raise StrategyValidationError(errors)
