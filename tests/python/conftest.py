from __future__ import annotations

import datetime as dt
import logging
from typing import Dict, List, Optional

import pytest

from quantum_yolo_engine.engine import PaperTrader
from quantum_yolo_engine.models import AssetStrategy, EntryRule, TakeProfitRule
from quantum_yolo_engine.store import StateStore


def make_strategy(
    product_id: str = "BTC-USD",
    stop_price: float = 90.0,
    tp1_price: float = 120.0,
    tp1_fraction: float = 0.5,
    tp2_price: float = 140.0,
    tp2_fraction: float = 0.5,
    entries: Optional[List[EntryRule]] = None,
    enabled: bool = True,
    allocation_usd: float = 1000.0,
) -> AssetStrategy:
    if entries is None:
        entries = [EntryRule(id="e1", price=100.0, quote_size_usd=100.0)]
    return AssetStrategy(
        product_id=product_id,
        enabled=enabled,
        allocation_usd=allocation_usd,
        stop_price=stop_price,
        take_profit=TakeProfitRule(
            tp1_price=tp1_price, tp1_fraction=tp1_fraction, tp2_price=tp2_price, tp2_fraction=tp2_fraction
        ),
        entries=entries,
    )


@pytest.fixture
def logger() -> logging.Logger:
    lg = logging.getLogger("test_qye")
    lg.addHandler(logging.NullHandler())
    lg.setLevel(logging.DEBUG)
    return lg


@pytest.fixture
def db_path(tmp_path) -> str:
    return str(tmp_path / "test.db")


def make_store(db_path: str, run_id: str = "test-run-1") -> StateStore:
    return StateStore(db_path, run_id=run_id)


def make_trader(
    store: StateStore,
    strategies: Dict[str, AssetStrategy],
    logger: logging.Logger,
    move_stop_to_breakeven_after_tp1: bool = True,
) -> PaperTrader:
    trader = PaperTrader(
        store=store,
        strategies=strategies,
        logger=logger,
        move_stop_to_breakeven_after_tp1=move_stop_to_breakeven_after_tp1,
        strategy_source_path="test.yaml",
    )
    trader.bootstrap()
    return trader


def ts(seconds: int) -> dt.datetime:
    base = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    return base + dt.timedelta(seconds=seconds)
