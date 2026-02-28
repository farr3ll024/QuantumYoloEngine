# quantum_yolo_engine/strategy.py
from __future__ import annotations

from typing import Dict, Tuple

import yaml

from .models import AssetStrategy, EntryRule, TakeProfitRule


def load_strategy_config(path: str) -> Tuple[float, Dict[str, AssetStrategy]]:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    bankroll = float(raw["bankroll_usd"])
    assets_raw = raw["assets"]

    strategies: Dict[str, AssetStrategy] = {}
    for product_id, v in assets_raw.items():
        tp = TakeProfitRule(
            tp1_price=float(v["take_profit"]["tp1_price"]),
            tp1_fraction=float(v["take_profit"]["tp1_fraction"]),
            tp2_price=float(v["take_profit"]["tp2_price"]),
            tp2_fraction=float(v["take_profit"]["tp2_fraction"]),
        )
        entries = [
            EntryRule(
                id=str(e["id"]),
                price=float(e["price"]),
                quote_size_usd=float(e["quote_size_usd"]),
            )
            for e in v["entries"]
        ]

        strategies[product_id] = AssetStrategy(
            product_id=product_id,
            enabled=bool(v.get("enabled", True)),
            allocation_usd=float(v["allocation_usd"]),
            stop_price=float(v["stop_price"]),
            take_profit=tp,
            entries=entries,
        )

    return bankroll, strategies