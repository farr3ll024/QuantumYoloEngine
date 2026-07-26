"""
Generates human-reviewable behavioral parity fixtures from the Python
reference engine. Each fixture captures one scenario end-to-end: strategy
input, ordered ticks, and the resulting orders/positions/events/equity/
summary/hashes. The TypeScript engine (web/src/engine) must reproduce every
fixture byte-for-byte after the shared rounding policy is applied.

Rounding policy: every float in a fixture is rounded to 8 decimal places
before serialization (ROUND_DP). This matches the base-asset quantity
precision used throughout the engine (see engine.py fill logic) and is
generous enough to preserve USD-denominated values to well below a cent.
Both the Python and TypeScript engines must apply this exact policy before
comparing numbers in the parity test suite.

Run: python tests/parity/generate_fixtures.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from quantum_yolo_engine.engine import PaperTrader, strategy_snapshot_and_hash  # noqa: E402
from quantum_yolo_engine.metrics import compute_equity_curve  # noqa: E402
from quantum_yolo_engine.models import AssetStrategy, EntryRule, TakeProfitRule  # noqa: E402
from quantum_yolo_engine.store import StateStore  # noqa: E402

ROUND_DP = 8
FIXTURES_DIR = Path(__file__).parent / "fixtures"
BANKROLL_USD = 10_000.0


def round_floats(obj):
    if isinstance(obj, float):
        return round(obj, ROUND_DP)
    if isinstance(obj, dict):
        return {k: round_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [round_floats(v) for v in obj]
    return obj


def strat(
    product_id: str,
    stop_price: float,
    tp1_price: float,
    tp2_price: float,
    entries: List[Tuple[str, float, float]],
    tp1_fraction: float = 0.5,
    tp2_fraction: float = 0.5,
    enabled: bool = True,
) -> AssetStrategy:
    return AssetStrategy(
        product_id=product_id,
        enabled=enabled,
        allocation_usd=10_000.0,
        stop_price=stop_price,
        take_profit=TakeProfitRule(
            tp1_price=tp1_price, tp1_fraction=tp1_fraction, tp2_price=tp2_price, tp2_fraction=tp2_fraction
        ),
        entries=[EntryRule(id=i, price=p, quote_size_usd=q) for (i, p, q) in entries],
    )


def base_ts(seconds: int) -> dt.datetime:
    return dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc) + dt.timedelta(seconds=seconds)


def dataset_hash(ticks: List[Tuple[int, Dict[str, float]]]) -> str:
    rows = []
    for sec, prices in ticks:
        ts_iso = base_ts(sec).isoformat()
        for pid, price in sorted(prices.items()):
            rows.append({"ts": ts_iso, "product_id": pid, "price": price})
    text = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_scenario(name: str, strategies: Dict[str, AssetStrategy], ticks: List[Tuple[int, Dict[str, float]]]) -> dict:
    db_path = f":memory:?cache=shared&_fixture_{name}"
    # sqlite ":memory:" URIs need uri=True and a shared cache to survive
    # across connections; simplest reliable option is a real temp file.
    import tempfile

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()

    logger = logging.getLogger(f"fixture.{name}")
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.CRITICAL)

    store = StateStore(tmp.name, run_id=f"fixture-{name}")
    trader = PaperTrader(
        store=store,
        strategies=strategies,
        logger=logger,
        move_stop_to_breakeven_after_tp1=True,
        strategy_source_path=f"fixtures/{name}.yaml",
    )
    trader.bootstrap()

    for sec, prices in ticks:
        trader.on_price_tick(base_ts(sec), prices)

    orders = [
        dict(row)
        for row in store.conn.execute(
            "select order_id, product_id, order_type, rule_id, side, price, quote_size_usd, base_size, "
            "status, created_at, filled_at from orders where run_id = ? order by created_at, order_id",
            (store.run_id,),
        ).fetchall()
    ]
    positions = [
        dict(row)
        for row in store.conn.execute(
            "select product_id, base_qty, avg_entry, invested_quote, realized_pnl, state, tp1_done, tp2_done, "
            "stop_done, active_stop_price from positions where run_id = ? order by product_id",
            (store.run_id,),
        ).fetchall()
    ]
    events = [
        dict(row)
        for row in store.conn.execute(
            "select sequence, ts, level, product_id, event_type, message, payload_json "
            "from events where run_id = ? order by sequence",
            (store.run_id,),
        ).fetchall()
    ]
    for ev in events:
        ev["payload"] = json.loads(ev.pop("payload_json")) if ev.get("payload_json") else None

    price_ticks = [
        dict(row)
        for row in store.conn.execute(
            "select ts, product_id, price from price_ticks where run_id = ? order by id", (store.run_id,)
        ).fetchall()
    ]
    equity_result = compute_equity_curve(BANKROLL_USD, price_ticks, events)

    total_realized = sum(p["realized_pnl"] for p in positions)
    summary = {
        "ending_equity": equity_result.ending_equity,
        "max_drawdown": equity_result.max_drawdown,
        "total_realized_pnl": total_realized,
        "stop_count": sum(1 for p in positions if p["stop_done"]),
        "tp1_count": sum(1 for p in positions if p["tp1_done"]),
        "tp2_count": sum(1 for p in positions if p["tp2_done"]),
        "entries_filled_count": sum(1 for o in orders if o["order_type"] == "entry" and o["status"] == "filled"),
    }

    strategy_input = {
        pid: {
            "productId": s.product_id,
            "enabled": s.enabled,
            "allocationUsd": s.allocation_usd,
            "stopPrice": s.stop_price,
            "takeProfit": {
                "tp1Price": s.take_profit.tp1_price,
                "tp1Fraction": s.take_profit.tp1_fraction,
                "tp2Price": s.take_profit.tp2_price,
                "tp2Fraction": s.take_profit.tp2_fraction,
            },
            "entries": [{"id": e.id, "price": e.price, "quoteSizeUsd": e.quote_size_usd} for e in s.entries],
        }
        for pid, s in strategies.items()
    }

    _, strategy_hash = strategy_snapshot_and_hash(strategies)

    fixture = {
        "name": name,
        "roundDp": ROUND_DP,
        "bankrollUsd": BANKROLL_USD,
        "moveStopToBreakevenAfterTp1": True,
        "strategy": strategy_input,
        "strategyHash": strategy_hash,
        "datasetHash": dataset_hash(ticks),
        "ticks": [
            {"ts": base_ts(sec).isoformat(), "prices": prices} for sec, prices in ticks
        ],
        "expectedOrders": orders,
        "expectedPositions": positions,
        "expectedEvents": [
            {
                "sequence": e["sequence"],
                "ts": e["ts"],
                "level": e["level"],
                "productId": e["product_id"],
                "eventType": e["event_type"],
                "message": e["message"],
                "payload": e["payload"],
            }
            for e in events
        ],
        "expectedEquitySamples": [
            {"ts": s.ts, "equity": s.equity, "drawdown": s.drawdown} for s in equity_result.samples
        ],
        "expectedSummary": summary,
    }

    store.conn.close()
    for suffix in ("", "-wal", "-shm"):
        try:
            Path(tmp.name + suffix).unlink(missing_ok=True)
        except OSError:
            pass
    return round_floats(fixture)


def build_scenarios() -> Dict[str, dict]:
    scenarios: Dict[str, dict] = {}

    # 1. no fills
    scenarios["01_no_fills"] = run_scenario(
        "01_no_fills",
        {"BTC-USD": strat("BTC-USD", 90, 120, 140, [("e1", 100, 100)])},
        [(1, {"BTC-USD": 150}), (2, {"BTC-USD": 160})],
    )

    # 2. one entry fill
    scenarios["02_one_entry_fill"] = run_scenario(
        "02_one_entry_fill",
        {"BTC-USD": strat("BTC-USD", 90, 120, 140, [("e1", 100, 100)])},
        [(1, {"BTC-USD": 95})],
    )

    # 3. three ladder fills, weighted average
    scenarios["03_three_ladder_fills"] = run_scenario(
        "03_three_ladder_fills",
        {"BTC-USD": strat("BTC-USD", 50, 200, 220, [("e1", 100, 100), ("e2", 95, 100), ("e3", 90, 100)])},
        [(1, {"BTC-USD": 100}), (2, {"BTC-USD": 95}), (3, {"BTC-USD": 90})],
    )

    # 4. entry followed by stop on a later tick
    scenarios["04_entry_then_stop_later_tick"] = run_scenario(
        "04_entry_then_stop_later_tick",
        {"BTC-USD": strat("BTC-USD", 90, 200, 220, [("e1", 100, 100)])},
        [(1, {"BTC-USD": 100}), (2, {"BTC-USD": 85})],
    )

    # 5. entry and stop threshold crossed on the same tick (second ladder rung
    # crosses an already-active stop on the same timestamp -> guarded)
    scenarios["05_entry_and_stop_same_tick"] = run_scenario(
        "05_entry_and_stop_same_tick",
        {
            "BTC-USD": strat(
                "BTC-USD", 100, 500, 600, [("e1", 150, 100), ("e2", 120, 100)]
            )
        },
        [(1, {"BTC-USD": 140}), (2, {"BTC-USD": 95}), (3, {"BTC-USD": 95})],
    )

    # 6. TP1 then break-even stop
    scenarios["06_tp1_then_breakeven"] = run_scenario(
        "06_tp1_then_breakeven",
        {"BTC-USD": strat("BTC-USD", 90, 110, 130, [("e1", 100, 100)])},
        [(1, {"BTC-USD": 100}), (2, {"BTC-USD": 110})],
    )

    # 7. TP1 then TP2
    scenarios["07_tp1_then_tp2"] = run_scenario(
        "07_tp1_then_tp2",
        {"BTC-USD": strat("BTC-USD", 90, 110, 130, [("e1", 100, 100)])},
        [(1, {"BTC-USD": 100}), (2, {"BTC-USD": 110}), (3, {"BTC-USD": 130})],
    )

    # 8. BTC and ETH interleaved at identical timestamps
    scenarios["08_btc_eth_interleaved"] = run_scenario(
        "08_btc_eth_interleaved",
        {
            "BTC-USD": strat("BTC-USD", 90, 200, 220, [("b1", 100, 100)]),
            "ETH-USD": strat("ETH-USD", 9, 20, 22, [("e1", 10, 50)]),
        },
        [(1, {"BTC-USD": 100, "ETH-USD": 10}), (2, {"BTC-USD": 210, "ETH-USD": 21})],
    )

    # 9. price gap through stop
    scenarios["09_price_gap_through_stop"] = run_scenario(
        "09_price_gap_through_stop",
        {"BTC-USD": strat("BTC-USD", 90, 200, 220, [("e1", 100, 100)])},
        [(1, {"BTC-USD": 100}), (2, {"BTC-USD": 60})],
    )

    # 10. price gap through take profit
    scenarios["10_price_gap_through_take_profit"] = run_scenario(
        "10_price_gap_through_take_profit",
        {"BTC-USD": strat("BTC-USD", 90, 110, 130, [("e1", 100, 100)], tp1_fraction=1.0)},
        [(1, {"BTC-USD": 100}), (2, {"BTC-USD": 200})],
    )

    return scenarios


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    scenarios = build_scenarios()
    for name, fixture in scenarios.items():
        out_path = FIXTURES_DIR / f"{name}.json"
        out_path.write_text(json.dumps(fixture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {out_path.relative_to(REPO_ROOT)}")
    print(f"\n{len(scenarios)} fixtures generated.")


if __name__ == "__main__":
    main()
