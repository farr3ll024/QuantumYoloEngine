# quantum_yolo_engine/engine.py
from __future__ import annotations

import datetime as dt
import logging
from typing import Dict

from .models import AssetStrategy, PositionState, PriceSnapshot
from .store import StateStore


class PaperTrader:
    def __init__(
        self,
        store: StateStore,
        strategies: Dict[str, AssetStrategy],
        logger: logging.Logger,
        move_stop_to_breakeven_after_tp1: bool = True,
    ):
        self.store = store
        self.strategies = strategies
        self.logger = logger
        self.move_stop_to_breakeven_after_tp1 = move_stop_to_breakeven_after_tp1

    def bootstrap(self) -> None:
        now_iso = dt.datetime.now(dt.timezone.utc).isoformat()

        with self.store.transaction():
            for product_id, strat in self.strategies.items():
                if not strat.enabled:
                    continue

                existing = self.store.get_position(product_id)
                if existing is None:
                    self.store.upsert_position(PositionState(product_id=product_id), ts_iso=now_iso)
                    self.store.log_event("info", "bootstrap_position", "created initial position state", product_id, ts_iso=now_iso)

                existing_entry_orders = self.store.get_orders_by_type(product_id, "entry")
                if not existing_entry_orders:
                    for entry in strat.entries:
                        self.store.insert_order(
                            order_id=f"{product_id}:{entry.id}",
                            product_id=product_id,
                            order_type="entry",
                            rule_id=entry.id,
                            side="buy",
                            price=entry.price,
                            quote_size_usd=entry.quote_size_usd,
                            base_size=None,
                            ts_iso=now_iso,
                        )
                    self.store.log_event("info", "seed_entries", "seeded entry ladder orders", product_id, ts_iso=now_iso)
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
            if market_price <= float(order["price"]):
                quote_size = float(order["quote_size_usd"])
                fill_price = float(order["price"])
                base_qty = quote_size / fill_price

                new_base = pos.base_qty + base_qty
                if new_base <= 0:
                    continue

                new_avg = fill_price if pos.base_qty <= 0 else (
                    ((pos.avg_entry * pos.base_qty) + (fill_price * base_qty)) / new_base
                )

                pos.base_qty = new_base
                pos.avg_entry = new_avg
                pos.invested_quote += quote_size
                pos.state = "active"

                self.store.mark_order_filled(order["order_id"], ts_iso=ts_iso)
                self.store.upsert_position(pos, ts_iso=ts_iso)
                self.store.log_event(
                    "info",
                    "entry_filled",
                    f"filled entry {order['rule_id']} at {fill_price:.2f}",
                    strat.product_id,
                    payload={
                        "quote_size": quote_size,
                        "base_qty": base_qty,
                        "new_avg_entry": new_avg,
                        "market_price": market_price,
                    },
                    ts_iso=ts_iso,
                )
                self.logger.info(
                    "%s entry filled | %s | fill=%.2f | qty=%.8f | avg=%.2f",
                    strat.product_id,
                    order["rule_id"],
                    fill_price,
                    base_qty,
                    new_avg,
                )

    def _ensure_exit_orders(self, strat: AssetStrategy, pos: PositionState, ts_iso: str) -> None:
        if not self.store.get_orders_by_type(strat.product_id, "stop", status="open"):
            self.store.insert_order(
                order_id=f"{strat.product_id}:stop",
                product_id=strat.product_id,
                order_type="stop",
                rule_id="stop",
                side="sell",
                price=strat.stop_price,
                quote_size_usd=None,
                base_size=None,
                ts_iso=ts_iso,
            )

        if not pos.tp1_done and not self.store.get_orders_by_type(strat.product_id, "tp1", status="open"):
            self.store.insert_order(
                order_id=f"{strat.product_id}:tp1",
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
                order_id=f"{strat.product_id}:tp2",
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
        if market_price > strat.stop_price:
            return

        qty_to_sell = pos.base_qty
        fill_price = strat.stop_price
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
            payload={"qty": qty_to_sell, "realized_pnl": realized},
            ts_iso=ts_iso,
        )
        self.logger.warning(
            "%s stop filled | fill=%.2f | qty=%.8f | realized=%.2f",
            strat.product_id,
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
            fill_price = strat.take_profit.tp1_price
            realized = (fill_price - pos.avg_entry) * qty

            pos.base_qty -= qty
            pos.realized_pnl += realized
            pos.tp1_done = True
            pos.state = "tp1_hit"

            open_tp1 = self.store.get_orders_by_type(strat.product_id, "tp1", status="open")
            if open_tp1:
                self.store.mark_order_filled(open_tp1[0]["order_id"], ts_iso=ts_iso)

            if self.move_stop_to_breakeven_after_tp1:
                old_stop = strat.stop_price
                strat.stop_price = round(pos.avg_entry, 2)
                self.store.log_event(
                    "info",
                    "stop_moved",
                    f"moved stop to breakeven from {old_stop:.2f} to {strat.stop_price:.2f}",
                    strat.product_id,
                    ts_iso=ts_iso,
                )
                self.logger.info("%s stop moved to breakeven | old=%.2f | new=%.2f", strat.product_id, old_stop, strat.stop_price)

            self.store.upsert_position(pos, ts_iso=ts_iso)
            self.store.log_event(
                "info",
                "tp1_filled",
                f"tp1 filled at {fill_price:.2f}",
                strat.product_id,
                payload={"qty": qty, "realized_pnl": realized},
                ts_iso=ts_iso,
            )
            self.logger.info("%s tp1 filled | fill=%.2f | qty=%.8f | realized=%.2f", strat.product_id, fill_price, qty, realized)

        pos = self.store.get_position(strat.product_id)
        if pos is None or not pos.has_position:
            return

        if not pos.tp2_done and market_price >= strat.take_profit.tp2_price:
            qty = pos.base_qty
            fill_price = strat.take_profit.tp2_price
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
                payload={"qty": qty, "realized_pnl": realized},
                ts_iso=ts_iso,
            )
            self.logger.info("%s tp2 filled | fill=%.2f | qty=%.8f | realized=%.2f", strat.product_id, fill_price, qty, realized)