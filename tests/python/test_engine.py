from __future__ import annotations

import pytest

from quantum_yolo_engine.models import EntryRule
from tests.python.conftest import make_store, make_strategy, make_trader, ts


def test_no_fills_when_price_never_reaches_entry(db_path, logger):
    store = make_store(db_path)
    strat = make_strategy(entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)])
    trader = make_trader(store, {"BTC-USD": strat}, logger)

    trader.on_price_tick(ts(1), {"BTC-USD": 150.0})
    trader.on_price_tick(ts(2), {"BTC-USD": 160.0})

    pos = store.get_position("BTC-USD")
    assert pos.base_qty == 0.0
    assert pos.state == "waiting_for_entry"


def test_one_entry_fill_uses_min_of_market_and_limit(db_path, logger):
    store = make_store(db_path)
    strat = make_strategy(entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)])
    trader = make_trader(store, {"BTC-USD": strat}, logger)

    trader.on_price_tick(ts(1), {"BTC-USD": 95.0})

    pos = store.get_position("BTC-USD")
    assert pos.avg_entry == 95.0
    assert pos.base_qty == pytest.approx(100.0 / 95.0)
    assert pos.state == "active"


def test_three_ladder_fills_weighted_average(db_path, logger):
    store = make_store(db_path)
    entries = [
        EntryRule(id="e1", price=100.0, quote_size_usd=100.0),
        EntryRule(id="e2", price=95.0, quote_size_usd=100.0),
        EntryRule(id="e3", price=90.0, quote_size_usd=100.0),
    ]
    strat = make_strategy(stop_price=50.0, entries=entries)
    trader = make_trader(store, {"BTC-USD": strat}, logger)

    trader.on_price_tick(ts(1), {"BTC-USD": 100.0})
    trader.on_price_tick(ts(2), {"BTC-USD": 95.0})
    trader.on_price_tick(ts(3), {"BTC-USD": 90.0})

    pos = store.get_position("BTC-USD")
    qty1, qty2, qty3 = 100.0 / 100.0, 100.0 / 95.0, 100.0 / 90.0
    expected_avg = (100.0 * qty1 + 95.0 * qty2 + 90.0 * qty3) / (qty1 + qty2 + qty3)
    assert pos.avg_entry == pytest.approx(expected_avg)
    assert pos.base_qty == pytest.approx(qty1 + qty2 + qty3)
    assert pos.invested_quote == pytest.approx(300.0)


def test_entry_then_stop_on_later_tick(db_path, logger):
    store = make_store(db_path)
    strat = make_strategy(stop_price=90.0, entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)])
    trader = make_trader(store, {"BTC-USD": strat}, logger)

    trader.on_price_tick(ts(1), {"BTC-USD": 100.0})
    trader.on_price_tick(ts(2), {"BTC-USD": 85.0})

    pos = store.get_position("BTC-USD")
    assert pos.stop_done is True
    assert pos.base_qty == 0.0
    assert pos.state == "stopped_out"
    # stop fill price is min(market, stop) = min(85, 90) = 85
    expected_realized = (85.0 - 100.0) * (100.0 / 100.0)
    assert pos.realized_pnl == pytest.approx(expected_realized)


def test_same_tick_entry_and_stop_does_not_fire_stop(db_path, logger):
    # an already-open position (stop already active, well below avg entry)
    # gets a *second* ladder fill on a tick where price also crosses the
    # active stop. the guard must prevent the stop from firing on the same
    # timestamp as an entry fill; it should fire cleanly on the next tick.
    store = make_store(db_path)
    strat = make_strategy(
        stop_price=100.0,
        tp1_price=500.0,
        tp2_price=600.0,
        entries=[
            EntryRule(id="e1", price=150.0, quote_size_usd=100.0),
            EntryRule(id="e2", price=120.0, quote_size_usd=100.0),
        ],
    )
    trader = make_trader(store, {"BTC-USD": strat}, logger)

    trader.on_price_tick(ts(1), {"BTC-USD": 140.0})  # fills e1 only, avg=140, stop stays 100
    pos = store.get_position("BTC-USD")
    assert pos.active_stop_price == pytest.approx(100.0)  # no adjustment needed (100 < 140)

    # tick 2: e2 fills (95 <= 120) AND market (95) is also <= active stop (100)
    trader.on_price_tick(ts(2), {"BTC-USD": 95.0})
    pos = store.get_position("BTC-USD")
    assert pos.base_qty > 0.0
    assert pos.stop_done is False  # guarded: no stop-out on the same tick as this fill
    assert pos.state == "active"

    # tick 3: same price, no new fill this tick -> guard no longer applies
    trader.on_price_tick(ts(3), {"BTC-USD": 95.0})
    pos = store.get_position("BTC-USD")
    assert pos.stop_done is True


def test_tp1_partial_exit_and_breakeven_stop_move(db_path, logger):
    store = make_store(db_path)
    strat = make_strategy(
        stop_price=90.0,
        tp1_price=110.0,
        tp1_fraction=0.5,
        tp2_price=130.0,
        tp2_fraction=0.5,
        entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)],
    )
    trader = make_trader(store, {"BTC-USD": strat}, logger, move_stop_to_breakeven_after_tp1=True)

    trader.on_price_tick(ts(1), {"BTC-USD": 100.0})
    full_qty = store.get_position("BTC-USD").base_qty

    trader.on_price_tick(ts(2), {"BTC-USD": 110.0})

    pos = store.get_position("BTC-USD")
    assert pos.tp1_done is True
    assert pos.base_qty == pytest.approx(full_qty * 0.5)
    assert pos.active_stop_price == pytest.approx(100.0)  # moved to breakeven (avg entry)
    assert pos.realized_pnl == pytest.approx((110.0 - 100.0) * (full_qty * 0.5))


def test_tp2_final_exit_closes_position(db_path, logger):
    store = make_store(db_path)
    strat = make_strategy(
        stop_price=90.0,
        tp1_price=110.0,
        tp1_fraction=0.5,
        tp2_price=130.0,
        tp2_fraction=0.5,
        entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)],
    )
    trader = make_trader(store, {"BTC-USD": strat}, logger)

    trader.on_price_tick(ts(1), {"BTC-USD": 100.0})
    trader.on_price_tick(ts(2), {"BTC-USD": 110.0})
    trader.on_price_tick(ts(3), {"BTC-USD": 130.0})

    pos = store.get_position("BTC-USD")
    assert pos.tp2_done is True
    assert pos.base_qty == 0.0
    assert pos.state == "completed"

    # stop order must be canceled once the position is fully closed via tp2
    stop_orders = store.get_orders_by_type("BTC-USD", "stop")
    assert all(o["status"] != "open" for o in stop_orders)


def test_price_gap_through_stop_fills_at_market_not_stop(db_path, logger):
    store = make_store(db_path)
    strat = make_strategy(stop_price=90.0, entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)])
    trader = make_trader(store, {"BTC-USD": strat}, logger)

    trader.on_price_tick(ts(1), {"BTC-USD": 100.0})
    trader.on_price_tick(ts(2), {"BTC-USD": 60.0})  # gaps well past the stop

    pos = store.get_position("BTC-USD")
    assert pos.stop_done is True
    # sell stop: fill = min(market, stop) -> the worse (lower) of the two
    expected_realized = (60.0 - 100.0) * (100.0 / 100.0)
    assert pos.realized_pnl == pytest.approx(expected_realized)


def test_price_gap_through_take_profit_fills_at_market_not_limit(db_path, logger):
    store = make_store(db_path)
    strat = make_strategy(
        stop_price=90.0,
        tp1_price=110.0,
        tp1_fraction=1.0,
        tp2_price=130.0,
        tp2_fraction=1.0,
        entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)],
    )
    trader = make_trader(store, {"BTC-USD": strat}, logger)

    trader.on_price_tick(ts(1), {"BTC-USD": 100.0})
    trader.on_price_tick(ts(2), {"BTC-USD": 200.0})  # gaps well past tp1

    pos = store.get_position("BTC-USD")
    assert pos.tp1_done is True
    # take profit: fill = max(market, tp_price) -> the better (higher) of the two
    full_qty = 100.0 / 100.0
    expected_realized = (200.0 - 100.0) * (full_qty * 1.0)
    assert pos.realized_pnl == pytest.approx(expected_realized)


def test_btc_and_eth_interleaved_at_identical_timestamps(db_path, logger):
    store = make_store(db_path)
    btc = make_strategy(product_id="BTC-USD", stop_price=90.0, entries=[EntryRule(id="b1", price=100.0, quote_size_usd=100.0)])
    eth = make_strategy(product_id="ETH-USD", stop_price=9.0, entries=[EntryRule(id="e1", price=10.0, quote_size_usd=50.0)])
    trader = make_trader(store, {"BTC-USD": btc, "ETH-USD": eth}, logger)

    trader.on_price_tick(ts(1), {"BTC-USD": 100.0, "ETH-USD": 10.0})

    btc_pos = store.get_position("BTC-USD")
    eth_pos = store.get_position("ETH-USD")
    assert btc_pos.base_qty == pytest.approx(1.0)
    assert eth_pos.base_qty == pytest.approx(5.0)


def test_order_cancellation_on_stop(db_path, logger):
    store = make_store(db_path)
    strat = make_strategy(
        stop_price=90.0,
        tp1_price=110.0,
        tp2_price=130.0,
        entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)],
    )
    trader = make_trader(store, {"BTC-USD": strat}, logger)

    trader.on_price_tick(ts(1), {"BTC-USD": 100.0})
    trader.on_price_tick(ts(2), {"BTC-USD": 80.0})  # stop

    tp1_orders = store.get_orders_by_type("BTC-USD", "tp1")
    tp2_orders = store.get_orders_by_type("BTC-USD", "tp2")
    assert all(o["status"] == "canceled" for o in tp1_orders)
    assert all(o["status"] == "canceled" for o in tp2_orders)


def test_event_sequence_is_monotonic_and_ordered(db_path, logger):
    store = make_store(db_path)
    strat = make_strategy(entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)])
    make_trader(store, {"BTC-USD": strat}, logger)

    events = store.get_events()
    sequences = [e["sequence"] for e in events]
    assert sequences == sorted(sequences)
    assert len(sequences) == len(set(sequences))


def test_idempotent_bootstrap_does_not_duplicate_orders(db_path, logger):
    store = make_store(db_path)
    strat = make_strategy(entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)])
    trader = make_trader(store, {"BTC-USD": strat}, logger)

    trader.bootstrap()  # calling bootstrap again must not reseed orders
    entry_orders = store.get_orders_by_type("BTC-USD", "entry")
    assert len(entry_orders) == 1


def test_two_run_ids_do_not_share_state(db_path, logger):
    strat = make_strategy(entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)])

    store_a = make_store(db_path, run_id="run-a")
    trader_a = make_trader(store_a, {"BTC-USD": strat}, logger)
    trader_a.on_price_tick(ts(1), {"BTC-USD": 100.0})

    store_b = make_store(db_path, run_id="run-b")
    trader_b = make_trader(store_b, {"BTC-USD": strat}, logger)

    pos_a = store_a.get_position("BTC-USD")
    pos_b = store_b.get_position("BTC-USD")
    assert pos_a.base_qty > 0.0
    assert pos_b.base_qty == 0.0  # run-b's fresh position must not see run-a's fill

    # order ids must not collide across runs sharing one database file
    orders_a = store_a.get_orders_by_type("BTC-USD", "entry")
    orders_b = store_b.get_orders_by_type("BTC-USD", "entry")
    assert orders_a[0]["order_id"] != orders_b[0]["order_id"]
