from __future__ import annotations

import json

from quantum_yolo_engine.engine import strategy_snapshot_and_hash
from quantum_yolo_engine.models import EntryRule
from tests.python.conftest import make_store, make_strategy, make_trader


def test_strategy_hash_is_stable_for_identical_config():
    strat_a = make_strategy(entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)])
    strat_b = make_strategy(entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)])

    _, hash_a = strategy_snapshot_and_hash({"BTC-USD": strat_a})
    _, hash_b = strategy_snapshot_and_hash({"BTC-USD": strat_b})
    assert hash_a == hash_b


def test_strategy_hash_changes_when_config_changes():
    strat_a = make_strategy(stop_price=90.0)
    strat_b = make_strategy(stop_price=91.0)

    _, hash_a = strategy_snapshot_and_hash({"BTC-USD": strat_a})
    _, hash_b = strategy_snapshot_and_hash({"BTC-USD": strat_b})
    assert hash_a != hash_b


def test_run_registered_with_snapshot_and_hash(db_path, logger):
    strat = make_strategy(entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)])
    store = make_store(db_path, run_id="run-xyz")
    make_trader(store, {"BTC-USD": strat}, logger)

    row = store.conn.execute("select * from runs where run_id = ?", ("run-xyz",)).fetchone()
    assert row is not None
    assert row["strategy_hash"]
    snapshot = json.loads(row["strategy_snapshot_json"])
    assert "assets" in snapshot
    assert snapshot["assets"]["BTC-USD"]["entries"][0]["id"] == "e1"


def test_registering_run_twice_is_idempotent(db_path, logger):
    strat = make_strategy(entries=[EntryRule(id="e1", price=100.0, quote_size_usd=100.0)])
    store = make_store(db_path, run_id="run-xyz")
    trader = make_trader(store, {"BTC-USD": strat}, logger)
    trader.bootstrap()

    count = store.conn.execute("select count(*) as c from runs where run_id = ?", ("run-xyz",)).fetchone()["c"]
    assert count == 1
