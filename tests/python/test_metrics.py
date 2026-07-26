from __future__ import annotations

import pytest

from quantum_yolo_engine.metrics import compute_equity_curve
from quantum_yolo_engine.models import EntryRule
from tests.python.conftest import make_store, make_strategy, make_trader, ts


def _rows(store):
    price_ticks = [dict(row) for row in store.conn.execute(
        "select ts, product_id, price from price_ticks where run_id = ? order by id", (store.run_id,)
    ).fetchall()]
    events = [dict(row) for row in store.get_events()]
    return price_ticks, events


def test_equity_flat_when_no_price_movement(db_path, logger):
    store = make_store(db_path)
    strat = make_strategy(entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)])
    trader = make_trader(store, {"BTC-USD": strat}, logger)
    trader.on_price_tick(ts(1), {"BTC-USD": 100.0})

    price_ticks, events = _rows(store)
    result = compute_equity_curve(1000.0, price_ticks, events)

    assert result.samples[-1].equity == pytest.approx(1000.0)
    assert result.max_drawdown == pytest.approx(0.0)


def test_equity_reflects_unrealized_pnl_event_by_event(db_path, logger):
    store = make_store(db_path)
    strat = make_strategy(stop_price=50.0, entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)])
    trader = make_trader(store, {"BTC-USD": strat}, logger)

    trader.on_price_tick(ts(1), {"BTC-USD": 100.0})  # fills entry, qty=1.0
    trader.on_price_tick(ts(2), {"BTC-USD": 110.0})  # +10 unrealized
    trader.on_price_tick(ts(3), {"BTC-USD": 90.0})  # -10 unrealized -> drawdown

    price_ticks, events = _rows(store)
    result = compute_equity_curve(1000.0, price_ticks, events)

    equities = [s.equity for s in result.samples]
    assert equities[0] == pytest.approx(1000.0)  # entry fills at avg==market, no P&L yet
    assert equities[1] == pytest.approx(1010.0)
    assert equities[2] == pytest.approx(990.0)
    assert result.max_drawdown == pytest.approx(-20.0)  # peak 1010 -> trough 990


def test_equity_after_realized_pnl_from_stop(db_path, logger):
    store = make_store(db_path)
    strat = make_strategy(stop_price=90.0, entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)])
    trader = make_trader(store, {"BTC-USD": strat}, logger)

    trader.on_price_tick(ts(1), {"BTC-USD": 100.0})
    trader.on_price_tick(ts(2), {"BTC-USD": 80.0})  # stop fills at 80

    price_ticks, events = _rows(store)
    result = compute_equity_curve(1000.0, price_ticks, events)

    expected_realized = (80.0 - 100.0) * 1.0
    assert result.ending_equity == pytest.approx(1000.0 + expected_realized)


def test_equity_curve_is_monotone_length_with_tick_count(db_path, logger):
    store = make_store(db_path)
    strat = make_strategy(entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)])
    trader = make_trader(store, {"BTC-USD": strat}, logger)
    for i in range(1, 6):
        trader.on_price_tick(ts(i), {"BTC-USD": 100.0 + i})

    price_ticks, events = _rows(store)
    result = compute_equity_curve(1000.0, price_ticks, events)
    assert len(result.samples) == 5
