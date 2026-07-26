from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
from typing import Dict

from .models import AssetStrategy, PositionState, PriceSnapshot
from .store import StateStore

ENGINE_VERSION = "0.2.0"


def strategy_snapshot_and_hash(strategies: Dict[str, AssetStrategy]) -> tuple[dict, str]:
    """Builds a stable, sorted JSON snapshot of a strategy dict and its
    sha256 fingerprint. Shared by bootstrap-time logging and any code that
    needs to attribute a run to the exact strategy revision that produced it."""
    assets: dict[str, dict] = {}
    for product_id, strat in strategies.items():
        assets[product_id] = {
            "enabled": bool(strat.enabled),
            "allocation_usd": float(strat.allocation_usd),
            "stop_price": float(strat.stop_price),
            "take_profit": {
                "tp1_price": float(strat.take_profit.tp1_price),
                "tp1_fraction": float(strat.take_profit.tp1_fraction),
                "tp2_price": float(strat.take_profit.tp2_price),
                "tp2_fraction": float(strat.take_profit.tp2_fraction),
            },
            "entries": [
                {"id": str(e.id), "price": float(e.price), "quote_size_usd": float(e.quote_size_usd)}
                for e in (strat.entries or [])
            ],
        }
    snapshot = {"assets": assets}
    snapshot_text = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    strategy_hash = hashlib.sha256(snapshot_text.encode("utf-8")).hexdigest()
    return snapshot, strategy_hash


class PaperTrader:
    def __init__(
            self,
            store: StateStore,
            strategies: Dict[str, AssetStrategy],
            logger: logging.Logger,
            move_stop_to_breakeven_after_tp1: bool = True,
            strategy_source_path: str | None = None,
    ):
        self.store = store
        self.strategies = strategies
        self.logger = logger
        self.move_stop_to_breakeven_after_tp1 = move_stop_to_breakeven_after_tp1
        self.strategy_source_path = strategy_source_path

        # prevents "enter and stop out on the same tick" behavior. this can happen
        # in csv replay or tight stops when the stop condition is evaluated on the
        # same timestamp as the entry fill.
        self._last_entry_ts_by_product: Dict[str, str] = {}

    def _register_run(self, ts_iso: str) -> None:
        """
        Persists an immutable strategy snapshot + sha256 fingerprint for this
        run_id, both in the `runs` table and as a `strategy_loaded` event, so
        reports can attribute outcomes to the exact strategy revision used —
        without ever needing to re-read the strategy file from disk.
        """
        try:
            snapshot, strategy_hash = strategy_snapshot_and_hash(self.strategies)
            full_snapshot = {
                "strategy_source_path": self.strategy_source_path,
                "generated_at_utc": ts_iso,
                **snapshot,
            }

            self.store.register_run(
                started_at_iso=ts_iso,
                strategy_source_path=self.strategy_source_path,
                strategy_hash=strategy_hash,
                strategy_snapshot_json=json.dumps(full_snapshot, sort_keys=True),
                engine_version=ENGINE_VERSION,
            )

            self.store.log_event(
                level="info",
                event_type="strategy_loaded",
                message=f"strategy loaded (sha256={strategy_hash[:12]}…)",
                product_id=None,
                payload={
                    "sha256": strategy_hash,
                    "strategy_source_path": self.strategy_source_path,
                    "snapshot": full_snapshot,
                },
                ts_iso=ts_iso,
            )

            self.logger.info("strategy_loaded | sha256=%s | path=%s", strategy_hash[:12], self.strategy_source_path)
        except Exception as ex:
            # never block trading because reporting metadata failed
            self.logger.warning("failed to log strategy_loaded event: %s", ex)

    def _order_id(self, product_id: str, rule_id: str) -> str:
        return f"{self.store.run_id}:{product_id}:{rule_id}"

    def bootstrap(self) -> None:
        now_iso = dt.datetime.now(dt.timezone.utc).isoformat()

        with self.store.transaction():
            # log strategy fingerprint once per run_id (idempotent: insert-or-ignore)
            self._register_run(now_iso)

            for product_id, strat in self.strategies.items():
                if not strat.enabled:
                    continue

                existing = self.store.get_position(product_id)
                if existing is None:
                    self.store.upsert_position(
                        PositionState(product_id=product_id, active_stop_price=float(strat.stop_price)),
                        ts_iso=now_iso,
                    )
                    self.store.log_event(
                        "info",
                        "bootstrap_position",
                        "created initial position state",
                        product_id,
                        ts_iso=now_iso,
                    )

                existing_entry_orders = self.store.get_orders_by_type(product_id, "entry")
                if not existing_entry_orders:
                    for entry in strat.entries:
                        self.store.insert_order(
                            order_id=self._order_id(product_id, entry.id),
                            product_id=product_id,
                            order_type="entry",
                            rule_id=entry.id,
                            side="buy",
                            price=entry.price,
                            quote_size_usd=entry.quote_size_usd,
                            base_size=None,
                            ts_iso=now_iso,
                        )
                    self.store.log_event(
                        "info",
                        "seed_entries",
                        "seeded entry ladder orders",
                        product_id,
                        ts_iso=now_iso,
                    )
                    self.logger.info("%s seeded %s entry orders", product_id, len(strat.entries))

    def on_price_tick(self, ts: dt.datetime, prices: PriceSnapshot) -> None:
        ts_iso = ts.isoformat()

        with self.store.transaction():
            for product_id, price in prices.items():
                self.store.insert_price_tick(product_id, price, ts_iso)

                if product_id not in self.strategies or not self.strategies[product_id].enabled:
                    continue

                strat = self.strategies[product_id]
                pos = self.store.get_position(product_id)
                if pos is None:
                    continue

                if pos.has_position and pos.state == "waiting_for_entry":
                    pos.state = "active"
                    self.store.upsert_position(pos, ts_iso=ts_iso)

                self._fill_entries(strat, pos, price, ts_iso)
                pos = self.store.get_position(product_id) or pos

                if pos.has_position and not pos.stop_done:
                    self._ensure_exit_orders(strat, pos, ts_iso)

                self._fill_stop_if_hit(strat, price, ts_iso)
                pos = self.store.get_position(product_id) or pos

                if pos.stop_done or not pos.has_position:
                    continue

                self._fill_tps_if_hit(strat, price, ts_iso)

    def _fill_entries(self, strat: AssetStrategy, pos: PositionState, market_price: float, ts_iso: str) -> None:
        open_entries = self.store.get_orders_by_type(strat.product_id, "entry", status="open")
        for order in open_entries:
            limit_price = float(order["price"])

            # buy limit: eligible when market is at or below the limit
            if market_price <= limit_price:
                quote_size = float(order["quote_size_usd"])

                # fill at the best available price (never worse than the limit)
                fill_price = min(limit_price, float(market_price))

                base_qty = quote_size / fill_price

                new_base = pos.base_qty + base_qty
                if new_base <= 0:
                    continue

                new_avg = (
                    fill_price
                    if pos.base_qty <= 0
                    else (((pos.avg_entry * pos.base_qty) + (fill_price * base_qty)) / new_base)
                )

                pos.base_qty = new_base
                pos.avg_entry = new_avg
                pos.invested_quote += quote_size
                pos.state = "active"

                if pos.active_stop_price <= 0:
                    pos.active_stop_price = float(strat.stop_price)

                # guard rails: for longs, stop must be below the current average entry.
                # if strategy config results in stop >= entry, it can instantly trigger.
                if float(pos.active_stop_price) >= float(new_avg):
                    original_stop = float(pos.active_stop_price)
                    adjusted_stop = round(float(new_avg) * 0.995, 2)
                    pos.active_stop_price = adjusted_stop
                    self.store.log_event(
                        "warn",
                        "stop_adjusted",
                        f"adjusted stop from {original_stop:.2f} to {adjusted_stop:.2f} (stop must be below avg entry)",
                        strat.product_id,
                        payload={
                            "original_stop": original_stop,
                            "adjusted_stop": adjusted_stop,
                            "avg_entry": float(new_avg),
                            "fill_price": float(fill_price),
                        },
                        ts_iso=ts_iso,
                    )
                    self.logger.warning(
                        "%s stop adjusted | original=%.2f | adjusted=%.2f | avg=%.2f",
                        strat.product_id,
                        original_stop,
                        adjusted_stop,
                        float(new_avg),
                    )

                # record entry tick so stop cannot immediately fire on the same timestamp
                self._last_entry_ts_by_product[strat.product_id] = ts_iso

                self.store.mark_order_filled(order["order_id"], ts_iso=ts_iso)
                self.store.upsert_position(pos, ts_iso=ts_iso)
                self.store.log_event(
                    "info",
                    "entry_filled",
                    f"filled entry {order['rule_id']} at {fill_price:.2f}",
                    strat.product_id,
                    payload={
                        "order_id": order["order_id"],
                        "rule_id": order["rule_id"],
                        "quote_size": quote_size,
                        "base_qty": base_qty,
                        "fill_price": float(fill_price),
                        "new_avg_entry": new_avg,
                        "market_price": float(market_price),
                        "limit_price": limit_price,
                    },
                    ts_iso=ts_iso,
                )
                self.logger.info(
                    "%s entry filled | %s | market=%.2f | limit=%.2f | fill=%.2f | qty=%.8f | avg=%.2f",
                    strat.product_id,
                    order["rule_id"],
                    float(market_price),
                    limit_price,
                    fill_price,
                    base_qty,
                    new_avg,
                )

    def _ensure_exit_orders(self, strat: AssetStrategy, pos: PositionState, ts_iso: str) -> None:
        stop_price = pos.active_stop_price if pos.active_stop_price > 0 else float(strat.stop_price)

        if not self.store.get_orders_by_type(strat.product_id, "stop", status="open"):
            self.store.insert_order(
                order_id=self._order_id(strat.product_id, "stop"),
                product_id=strat.product_id,
                order_type="stop",
                rule_id="stop",
                side="sell",
                price=stop_price,
                quote_size_usd=None,
                base_size=None,
                ts_iso=ts_iso,
            )

        if not pos.tp1_done and not self.store.get_orders_by_type(strat.product_id, "tp1", status="open"):
            self.store.insert_order(
                order_id=self._order_id(strat.product_id, "tp1"),
                product_id=strat.product_id,
                order_type="tp1",
                rule_id="tp1",
                side="sell",
                price=strat.take_profit.tp1_price,
                quote_size_usd=None,
                base_size=None,
                ts_iso=ts_iso,
            )

        if not pos.tp2_done and not self.store.get_orders_by_type(strat.product_id, "tp2", status="open"):
            self.store.insert_order(
                order_id=self._order_id(strat.product_id, "tp2"),
                product_id=strat.product_id,
                order_type="tp2",
                rule_id="tp2",
                side="sell",
                price=strat.take_profit.tp2_price,
                quote_size_usd=None,
                base_size=None,
                ts_iso=ts_iso,
            )

    def _fill_stop_if_hit(self, strat: AssetStrategy, market_price: float, ts_iso: str) -> None:
        pos = self.store.get_position(strat.product_id)
        if pos is None or not pos.has_position or pos.stop_done:
            return

        stop_price = pos.active_stop_price if pos.active_stop_price > 0 else float(strat.stop_price)

        # guard: do not allow the stop to fill on the same tick as an entry fill.
        if self._last_entry_ts_by_product.get(strat.product_id) == ts_iso:
            return
        if market_price > stop_price:
            return

        qty_to_sell = pos.base_qty

        # stop: fill at the best available price (never better than stop for a sell stop)
        fill_price = min(float(market_price), float(stop_price))

        realized = (fill_price - pos.avg_entry) * qty_to_sell

        pos.realized_pnl += realized
        pos.base_qty = 0.0
        pos.state = "stopped_out"
        pos.stop_done = True

        self.store.cancel_open_orders(strat.product_id, "tp1")
        self.store.cancel_open_orders(strat.product_id, "tp2")

        open_stops = self.store.get_orders_by_type(strat.product_id, "stop", status="open")
        if open_stops:
            self.store.mark_order_filled(open_stops[0]["order_id"], ts_iso=ts_iso)

        self.store.upsert_position(pos, ts_iso=ts_iso)
        self.store.log_event(
            "warn",
            "stop_filled",
            f"stop filled at {fill_price:.2f}",
            strat.product_id,
            payload={
                "qty": qty_to_sell,
                "realized_pnl": realized,
                "market_price": float(market_price),
                "stop_price": float(stop_price),
            },
            ts_iso=ts_iso,
        )
        self.logger.warning(
            "%s stop filled | market=%.2f | stop=%.2f | fill=%.2f | qty=%.8f | realized=%.2f",
            strat.product_id,
            float(market_price),
            float(stop_price),
            fill_price,
            qty_to_sell,
            realized,
        )

    def _fill_tps_if_hit(self, strat: AssetStrategy, market_price: float, ts_iso: str) -> None:
        pos = self.store.get_position(strat.product_id)
        if pos is None or not pos.has_position:
            return

        if not pos.tp1_done and market_price >= strat.take_profit.tp1_price:
            qty = pos.base_qty * strat.take_profit.tp1_fraction

            # take profit: fill at the best available price (never worse than the tp limit)
            fill_price = max(float(market_price), float(strat.take_profit.tp1_price))

            realized = (fill_price - pos.avg_entry) * qty

            pos.base_qty -= qty
            pos.realized_pnl += realized
            pos.tp1_done = True
            pos.state = "tp1_hit"

            open_tp1 = self.store.get_orders_by_type(strat.product_id, "tp1", status="open")
            if open_tp1:
                self.store.mark_order_filled(open_tp1[0]["order_id"], ts_iso=ts_iso)

            if self.move_stop_to_breakeven_after_tp1:
                old_stop = pos.active_stop_price
                pos.active_stop_price = round(pos.avg_entry, 2)
                self.store.cancel_open_orders(strat.product_id, "stop")
                self.store.log_event(
                    "info",
                    "stop_moved",
                    f"moved stop to breakeven from {old_stop:.2f} to {pos.active_stop_price:.2f}",
                    strat.product_id,
                    ts_iso=ts_iso,
                )
                self.logger.info(
                    "%s stop moved to breakeven | old=%.2f | new=%.2f",
                    strat.product_id,
                    old_stop,
                    pos.active_stop_price,
                )

            self.store.upsert_position(pos, ts_iso=ts_iso)
            self.store.log_event(
                "info",
                "tp1_filled",
                f"tp1 filled at {fill_price:.2f}",
                strat.product_id,
                payload={
                    "qty": qty,
                    "realized_pnl": realized,
                    "market_price": float(market_price),
                    "tp1_price": float(strat.take_profit.tp1_price),
                },
                ts_iso=ts_iso,
            )
            self.logger.info(
                "%s tp1 filled | market=%.2f | tp1=%.2f | fill=%.2f | qty=%.8f | realized=%.2f",
                strat.product_id,
                float(market_price),
                float(strat.take_profit.tp1_price),
                fill_price,
                qty,
                realized,
            )

        pos = self.store.get_position(strat.product_id)
        if pos is None or not pos.has_position:
            return

        if not pos.tp2_done and market_price >= strat.take_profit.tp2_price:
            qty = pos.base_qty

            # take profit: fill at the best available price (never worse than the tp limit)
            fill_price = max(float(market_price), float(strat.take_profit.tp2_price))

            realized = (fill_price - pos.avg_entry) * qty

            pos.base_qty = 0.0
            pos.realized_pnl += realized
            pos.tp2_done = True
            pos.state = "completed"

            open_tp2 = self.store.get_orders_by_type(strat.product_id, "tp2", status="open")
            if open_tp2:
                self.store.mark_order_filled(open_tp2[0]["order_id"], ts_iso=ts_iso)

            self.store.cancel_open_orders(strat.product_id, "stop")

            self.store.upsert_position(pos, ts_iso=ts_iso)
            self.store.log_event(
                "info",
                "tp2_filled",
                f"tp2 filled at {fill_price:.2f}",
                strat.product_id,
                payload={
                    "qty": qty,
                    "realized_pnl": realized,
                    "market_price": float(market_price),
                    "tp2_price": float(strat.take_profit.tp2_price),
                },
                ts_iso=ts_iso,
            )
            self.logger.info(
                "%s tp2 filled | market=%.2f | tp2=%.2f | fill=%.2f | qty=%.8f | realized=%.2f",
                strat.product_id,
                float(market_price),
                float(strat.take_profit.tp2_price),
                fill_price,
                qty,
                realized,
            )
