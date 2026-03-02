# dashboard/strategy_manager.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml


DEFAULT_STRATEGY_PATH = "strategy.yaml"


def load_strategy_yaml(path: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Returns (ok, parsed_dict, error_message).
    """
    p = Path(path).expanduser()
    if not p.exists():
        return False, None, f"file not found: {path}"
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return True, data, ""
    except Exception as ex:
        return False, None, str(ex)


def save_strategy_yaml(path: str, data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Writes the strategy dict back to disk as YAML.
    Returns (ok, error_message).
    """
    p = Path(path).expanduser()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        return True, ""
    except Exception as ex:
        return False, str(ex)


def validate_strategy_dict(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Basic structural validation before saving.
    Returns (ok, error_message).
    """
    if not isinstance(data, dict):
        return False, "top-level must be a mapping"

    if "bankroll_usd" not in data:
        return False, "missing bankroll_usd"

    try:
        bankroll = float(data["bankroll_usd"])
    except (TypeError, ValueError):
        return False, "bankroll_usd must be a number"

    if "assets" not in data or not isinstance(data["assets"], dict):
        return False, "missing or invalid 'assets' section"

    total_alloc = 0.0
    for product_id, asset in data["assets"].items():
        if not isinstance(asset, dict):
            return False, f"{product_id}: asset config must be a mapping"

        for required in ("allocation_usd", "stop_price", "take_profit", "entries"):
            if required not in asset:
                return False, f"{product_id}: missing required field '{required}'"

        tp = asset["take_profit"]
        for tp_field in ("tp1_price", "tp1_fraction", "tp2_price", "tp2_fraction"):
            if tp_field not in tp:
                return False, f"{product_id}.take_profit: missing '{tp_field}'"

        if not isinstance(asset["entries"], list) or len(asset["entries"]) == 0:
            return False, f"{product_id}: entries must be a non-empty list"

        for e in asset["entries"]:
            for ef in ("id", "price", "quote_size_usd"):
                if ef not in e:
                    return False, f"{product_id}: entry missing '{ef}'"

        if asset.get("enabled", True):
            total_alloc += float(asset["allocation_usd"])

    if total_alloc > bankroll + 1e-9:
        return False, f"enabled allocations (${total_alloc:.2f}) exceed bankroll (${bankroll:.2f})"

    return True, ""