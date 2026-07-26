from __future__ import annotations

import math

import pytest

from quantum_yolo_engine.models import EntryRule
from quantum_yolo_engine.validate import StrategyValidationError, validate_strategy
from tests.python.conftest import make_strategy


def test_valid_strategy_passes():
    strat = make_strategy()
    validate_strategy(1000.0, {"BTC-USD": strat})  # must not raise


def test_negative_bankroll_rejected():
    strat = make_strategy()
    with pytest.raises(StrategyValidationError, match="bankroll_usd"):
        validate_strategy(-100.0, {"BTC-USD": strat})


def test_allocations_exceeding_bankroll_rejected():
    strat = make_strategy(allocation_usd=2000.0)
    with pytest.raises(StrategyValidationError, match="exceed bankroll"):
        validate_strategy(1000.0, {"BTC-USD": strat})


def test_entry_budget_exceeding_allocation_rejected():
    strat = make_strategy(
        allocation_usd=50.0,
        entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)],
    )
    with pytest.raises(StrategyValidationError, match="exceeds allocation_usd"):
        validate_strategy(1000.0, {"BTC-USD": strat})


def test_unsupported_product_id_rejected():
    strat = make_strategy(product_id="DOGE-USD")
    with pytest.raises(StrategyValidationError, match="unsupported product_id"):
        validate_strategy(1000.0, {"DOGE-USD": strat})


def test_duplicate_entry_ids_rejected():
    strat = make_strategy(
        entries=[
            EntryRule(id="e1", price=100.0, quote_size_usd=10.0),
            EntryRule(id="e1", price=95.0, quote_size_usd=10.0),
        ]
    )
    with pytest.raises(StrategyValidationError, match="duplicate entry id"):
        validate_strategy(1000.0, {"BTC-USD": strat})


@pytest.mark.parametrize("fraction", [0.0, -0.1, 1.5, float("nan")])
def test_tp1_fraction_out_of_range_rejected(fraction):
    strat = make_strategy(tp1_fraction=fraction)
    with pytest.raises(StrategyValidationError, match="tp1_fraction"):
        validate_strategy(1000.0, {"BTC-USD": strat})


def test_tp_fraction_sum_over_one_rejected():
    strat = make_strategy(tp1_fraction=0.7, tp2_fraction=0.7)
    with pytest.raises(StrategyValidationError, match="tp1_fraction \\+ tp2_fraction"):
        validate_strategy(1000.0, {"BTC-USD": strat})


def test_nonpositive_entry_price_rejected():
    strat = make_strategy(entries=[EntryRule(id="e1", price=0.0, quote_size_usd=10.0)])
    with pytest.raises(StrategyValidationError, match="price must be a positive finite number"):
        validate_strategy(1000.0, {"BTC-USD": strat})


def test_non_finite_values_rejected():
    strat = make_strategy(stop_price=math.inf)
    with pytest.raises(StrategyValidationError, match="stop_price"):
        validate_strategy(1000.0, {"BTC-USD": strat})


def test_stop_must_be_below_tp1():
    strat = make_strategy(stop_price=115.0, tp1_price=110.0, tp2_price=130.0)
    with pytest.raises(StrategyValidationError, match="stop_price must be < take_profit.tp1_price"):
        validate_strategy(1000.0, {"BTC-USD": strat})


def test_tp1_must_be_below_tp2():
    strat = make_strategy(tp1_price=140.0, tp2_price=130.0)
    with pytest.raises(StrategyValidationError, match="tp1_price must be < tp2_price"):
        validate_strategy(1000.0, {"BTC-USD": strat})


def test_all_violations_reported_together():
    strat = make_strategy(stop_price=-1, entries=[EntryRule(id="e1", price=-5, quote_size_usd=-5)])
    with pytest.raises(StrategyValidationError) as exc_info:
        validate_strategy(-1.0, {"BTC-USD": strat})
    assert len(exc_info.value.errors) >= 3
