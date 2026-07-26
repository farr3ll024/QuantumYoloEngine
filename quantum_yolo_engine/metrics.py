# quantum_yolo_engine/metrics.py
"""
Event-sourced equity/drawdown reconstruction.

This is the reference implementation the TypeScript engine's metrics module
must match (see tests/parity). Equity is computed strictly by replaying the
event ledger and price ticks in chronological order -- never by projecting
the final position snapshot backward across history, which silently produces
a wrong equity curve whenever a position's size changed over time.

Definition: equity(t) = bankroll_usd + sum_over_products(
    cumulative_realized_pnl(t) + (mark_price(t) - avg_entry(t)) * open_base_qty(t)
)

Opening a position does not change equity (cash converts to an asset of
equal value at the fill price); only realized and unrealized P&L move it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence


@dataclass
class EquitySample:
    ts: str
    equity: float
    drawdown: float  # <= 0, equity - running_peak


@dataclass
class EquityCurveResult:
    samples: List[EquitySample]
    max_drawdown: float  # <= 0, the most negative drawdown observed
    ending_equity: float


@dataclass
class _ProductState:
    base_qty: float = 0.0
    avg_entry: float = 0.0
    realized_pnl: float = 0.0
    mark_price: Optional[float] = None


def compute_equity_curve(
    bankroll_usd: float,
    price_ticks: Sequence[dict],
    events: Sequence[dict],
) -> EquityCurveResult:
    """
    price_ticks: rows with at least {ts, product_id, price}, in insertion order.
    events: rows with at least {ts, sequence, event_type, product_id, payload},
        in sequence order. `payload` may be a dict (already decoded) or a raw
        JSON string.
    """
    import json as _json

    ticks_by_ts: Dict[str, List[dict]] = {}
    tick_order: List[str] = []
    for row in price_ticks:
        ts = row["ts"]
        if ts not in ticks_by_ts:
            ticks_by_ts[ts] = []
            tick_order.append(ts)
        ticks_by_ts[ts].append(row)

    events_by_ts: Dict[str, List[dict]] = {}
    for row in events:
        ts = row["ts"]
        events_by_ts.setdefault(ts, []).append(row)
    for ts in events_by_ts:
        events_by_ts[ts].sort(key=lambda r: r["sequence"])

    # ticks and events can interleave at timestamps that only appear in one
    # of the two collections (e.g. a strategy_loaded event fired before the
    # first tick). Merge and sort all distinct timestamps chronologically.
    all_ts = sorted(set(tick_order) | set(events_by_ts.keys()))

    state: Dict[str, _ProductState] = {}

    def get_state(product_id: str) -> _ProductState:
        if product_id not in state:
            state[product_id] = _ProductState()
        return state[product_id]

    samples: List[EquitySample] = []
    running_peak = float(bankroll_usd)
    max_drawdown = 0.0

    for ts in all_ts:
        for row in ticks_by_ts.get(ts, []):
            get_state(row["product_id"]).mark_price = float(row["price"])

        for ev in events_by_ts.get(ts, []):
            payload = ev.get("payload", ev.get("payload_json"))
            if isinstance(payload, str):
                payload = _json.loads(payload) if payload else {}
            payload = payload or {}
            product_id = ev.get("product_id")
            event_type = ev.get("event_type")

            if not product_id:
                continue
            s = get_state(product_id)

            if event_type == "entry_filled":
                s.base_qty += float(payload["base_qty"])
                s.avg_entry = float(payload["new_avg_entry"])
            elif event_type == "stop_filled":
                s.realized_pnl += float(payload["realized_pnl"])
                s.base_qty = 0.0
            elif event_type == "tp1_filled":
                s.realized_pnl += float(payload["realized_pnl"])
                s.base_qty -= float(payload["qty"])
            elif event_type == "tp2_filled":
                s.realized_pnl += float(payload["realized_pnl"])
                s.base_qty = 0.0

        # only emit a sample on ticks (not on metadata-only event timestamps,
        # e.g. strategy_loaded before any price data exists)
        if ts not in ticks_by_ts:
            continue

        equity = float(bankroll_usd)
        for s in state.values():
            equity += s.realized_pnl
            if s.base_qty > 0 and s.mark_price is not None:
                equity += (s.mark_price - s.avg_entry) * s.base_qty

        running_peak = max(running_peak, equity)
        drawdown = equity - running_peak
        max_drawdown = min(max_drawdown, drawdown)

        samples.append(EquitySample(ts=ts, equity=round(equity, 8), drawdown=round(drawdown, 8)))

    ending_equity = samples[-1].equity if samples else float(bankroll_usd)
    return EquityCurveResult(samples=samples, max_drawdown=round(max_drawdown, 8), ending_equity=ending_equity)
