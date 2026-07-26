# quantum_yolo_engine/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

PRODUCT_IDS: List[str] = ["BTC-USD", "ETH-USD"]
PriceSnapshot = Dict[str, float]


@dataclass
class EntryRule:
    id: str
    price: float
    quote_size_usd: float


@dataclass
class TakeProfitRule:
    tp1_price: float
    tp1_fraction: float
    tp2_price: float
    tp2_fraction: float


@dataclass
class AssetStrategy:
    product_id: str
    enabled: bool
    allocation_usd: float
    stop_price: float
    take_profit: TakeProfitRule
    entries: List[EntryRule] = field(default_factory=list)


@dataclass
class PositionState:
    product_id: str
    base_qty: float = 0.0
    avg_entry: float = 0.0
    invested_quote: float = 0.0
    realized_pnl: float = 0.0
    state: str = "waiting_for_entry"
    tp1_done: bool = False
    tp2_done: bool = False
    stop_done: bool = False
    # the currently active stop price for this run. Seeded from the strategy's
    # stop_price at bootstrap and may move (e.g. to breakeven after TP1). Kept
    # on position state rather than mutating the immutable strategy snapshot.
    active_stop_price: float = 0.0

    @property
    def has_position(self) -> bool:
        return self.base_qty > 0.0
