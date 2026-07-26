# quantum_yolo_engine/store.py
from __future__ import annotations

import contextlib
import datetime as dt
import json
import sqlite3
from typing import List, Optional

from .models import PositionState


class StateStore:
    """
    Persists engine state to SQLite. All rows are scoped by a first-class
    run_id so a database file can safely be reused across multiple runs
    without one run's orders/positions/events bleeding into another's.
    """

    def __init__(self, db_path: str, run_id: str):
        self.db_path = db_path
        self.run_id = run_id

        # check_same_thread=False helps when you have a writer + separate reader process (streamlit)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self._in_tx = False

        self._apply_pragmas()
        self._init_db()

    def _apply_pragmas(self) -> None:
        cur = self.conn.cursor()
        cur.execute("pragma journal_mode=WAL;")
        cur.execute("pragma synchronous=NORMAL;")
        cur.execute("pragma temp_store=MEMORY;")
        cur.execute("pragma cache_size=-65536;")  # ~64MB cache
        self.conn.commit()

    def _maybe_commit(self) -> None:
        if not self._in_tx:
            self.conn.commit()

    @contextlib.contextmanager
    def transaction(self):
        """
        batches many writes into a single sqlite transaction
        """
        if self._in_tx:
            yield
            return

        self._in_tx = True
        try:
            self.conn.execute("begin;")
            yield
            self.conn.execute("commit;")
        except Exception:
            self.conn.execute("rollback;")
            raise
        finally:
            self._in_tx = False

    def _init_db(self) -> None:
        cur = self.conn.cursor()

        cur.execute(
            """
            create table if not exists runs (
                run_id text primary key,
                started_at text not null,
                completed_at text,
                strategy_source_path text,
                strategy_hash text,
                strategy_snapshot_json text,
                engine_version text
            )
            """
        )

        cur.execute(
            """
            create table if not exists positions (
                run_id text not null,
                product_id text not null,
                base_qty real not null,
                avg_entry real not null,
                invested_quote real not null,
                realized_pnl real not null,
                state text not null,
                tp1_done integer not null,
                tp2_done integer not null,
                stop_done integer not null,
                active_stop_price real not null default 0,
                updated_at text not null,
                primary key (run_id, product_id)
            )
            """
        )

        cur.execute(
            """
            create table if not exists orders (
                order_id text primary key,
                run_id text not null,
                product_id text not null,
                order_type text not null,
                rule_id text,
                side text not null,
                price real not null,
                quote_size_usd real,
                base_size real,
                status text not null,
                created_at text not null,
                filled_at text
            )
            """
        )

        cur.execute(
            """
            create table if not exists events (
                id integer primary key autoincrement,
                run_id text not null,
                sequence integer not null,
                ts text not null,
                level text not null,
                product_id text,
                event_type text not null,
                message text not null,
                payload_json text
            )
            """
        )

        cur.execute(
            """
            create table if not exists price_ticks (
                id integer primary key autoincrement,
                run_id text not null,
                ts text not null,
                product_id text not null,
                price real not null
            )
            """
        )

        # indexes used by dashboard queries
        cur.execute("create index if not exists idx_price_ticks_run_pid_ts on price_ticks(run_id, product_id, ts)")
        cur.execute("create index if not exists idx_price_ticks_run_ts on price_ticks(run_id, ts)")
        cur.execute("create index if not exists idx_events_run_seq on events(run_id, sequence)")
        cur.execute("create index if not exists idx_events_run_type_ts on events(run_id, event_type, ts)")
        cur.execute(
            "create index if not exists idx_orders_run_pid_type_status "
            "on orders(run_id, product_id, order_type, status, created_at)"
        )

        self.conn.commit()

        cur.execute("select coalesce(max(sequence), 0) as v from events where run_id = ?", (self.run_id,))
        self._next_sequence = int(cur.fetchone()["v"]) + 1

    def register_run(
        self,
        started_at_iso: str,
        strategy_source_path: Optional[str],
        strategy_hash: str,
        strategy_snapshot_json: str,
        engine_version: str,
    ) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            insert or ignore into runs (
                run_id, started_at, strategy_source_path, strategy_hash,
                strategy_snapshot_json, engine_version
            ) values (?, ?, ?, ?, ?, ?)
            """,
            (self.run_id, started_at_iso, strategy_source_path, strategy_hash, strategy_snapshot_json, engine_version),
        )
        self._maybe_commit()

    def get_position(self, product_id: str) -> Optional[PositionState]:
        cur = self.conn.cursor()
        cur.execute(
            "select * from positions where run_id = ? and product_id = ?",
            (self.run_id, product_id),
        )
        row = cur.fetchone()
        if not row:
            return None

        return PositionState(
            product_id=row["product_id"],
            base_qty=row["base_qty"],
            avg_entry=row["avg_entry"],
            invested_quote=row["invested_quote"],
            realized_pnl=row["realized_pnl"],
            state=row["state"],
            tp1_done=bool(row["tp1_done"]),
            tp2_done=bool(row["tp2_done"]),
            stop_done=bool(row["stop_done"]),
            active_stop_price=row["active_stop_price"],
        )

    def upsert_position(self, pos: PositionState, ts_iso: Optional[str] = None) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            insert into positions (
                run_id, product_id, base_qty, avg_entry, invested_quote, realized_pnl, state,
                tp1_done, tp2_done, stop_done, active_stop_price, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(run_id, product_id) do update set
                base_qty = excluded.base_qty,
                avg_entry = excluded.avg_entry,
                invested_quote = excluded.invested_quote,
                realized_pnl = excluded.realized_pnl,
                state = excluded.state,
                tp1_done = excluded.tp1_done,
                tp2_done = excluded.tp2_done,
                stop_done = excluded.stop_done,
                active_stop_price = excluded.active_stop_price,
                updated_at = excluded.updated_at
            """,
            (
                self.run_id,
                pos.product_id,
                pos.base_qty,
                pos.avg_entry,
                pos.invested_quote,
                pos.realized_pnl,
                pos.state,
                int(pos.tp1_done),
                int(pos.tp2_done),
                int(pos.stop_done),
                pos.active_stop_price,
                ts_iso or dt.datetime.now(dt.timezone.utc).isoformat(),
            ),
        )
        self._maybe_commit()

    def insert_order(
        self,
        order_id: str,
        product_id: str,
        order_type: str,
        rule_id: Optional[str],
        side: str,
        price: float,
        quote_size_usd: Optional[float],
        base_size: Optional[float],
        status: str = "open",
        ts_iso: Optional[str] = None,
    ) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            insert or ignore into orders (
                order_id, run_id, product_id, order_type, rule_id, side, price,
                quote_size_usd, base_size, status, created_at, filled_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, null)
            """,
            (
                order_id,
                self.run_id,
                product_id,
                order_type,
                rule_id,
                side,
                price,
                quote_size_usd,
                base_size,
                status,
                ts_iso or dt.datetime.now(dt.timezone.utc).isoformat(),
            ),
        )
        self._maybe_commit()

    def get_orders_by_type(self, product_id: str, order_type: str, status: Optional[str] = None) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        if status:
            cur.execute(
                """
                select * from orders
                where run_id = ? and product_id = ? and order_type = ? and status = ?
                order by created_at asc
                """,
                (self.run_id, product_id, order_type, status),
            )
        else:
            cur.execute(
                """
                select * from orders
                where run_id = ? and product_id = ? and order_type = ?
                order by created_at asc
                """,
                (self.run_id, product_id, order_type),
            )
        return cur.fetchall()

    def mark_order_filled(self, order_id: str, ts_iso: Optional[str] = None) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "update orders set status = 'filled', filled_at = ? where order_id = ? and run_id = ?",
            (ts_iso or dt.datetime.now(dt.timezone.utc).isoformat(), order_id, self.run_id),
        )
        self._maybe_commit()

    def cancel_open_orders(self, product_id: str, order_type: Optional[str] = None) -> int:
        cur = self.conn.cursor()
        if order_type:
            cur.execute(
                """
                update orders
                set status = 'canceled'
                where run_id = ? and product_id = ? and order_type = ? and status = 'open'
                """,
                (self.run_id, product_id, order_type),
            )
        else:
            cur.execute(
                """
                update orders
                set status = 'canceled'
                where run_id = ? and product_id = ? and status = 'open'
                """,
                (self.run_id, product_id),
            )
        count = cur.rowcount
        self._maybe_commit()
        return count

    def log_event(
        self,
        level: str,
        event_type: str,
        message: str,
        product_id: Optional[str] = None,
        payload: Optional[dict] = None,
        ts_iso: Optional[str] = None,
    ) -> int:
        sequence = self._next_sequence
        self._next_sequence += 1

        cur = self.conn.cursor()
        cur.execute(
            """
            insert into events (run_id, sequence, ts, level, product_id, event_type, message, payload_json)
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.run_id,
                sequence,
                ts_iso or dt.datetime.now(dt.timezone.utc).isoformat(),
                level,
                product_id,
                event_type,
                message,
                json.dumps(payload) if payload else None,
            ),
        )
        self._maybe_commit()
        return sequence

    def get_events(self) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute(
            "select * from events where run_id = ? order by sequence asc",
            (self.run_id,),
        )
        return cur.fetchall()

    def insert_price_tick(self, product_id: str, price: float, ts_iso: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "insert into price_ticks (run_id, ts, product_id, price) values (?, ?, ?, ?)",
            (self.run_id, ts_iso, product_id, price),
        )
        self._maybe_commit()

    def print_summary(self) -> None:
        cur = self.conn.cursor()
        rows = cur.execute(
            "select * from positions where run_id = ? order by product_id", (self.run_id,)
        ).fetchall()
        print("\n=== position summary ===")
        for row in rows:
            print(
                f"{row['product_id']}: state={row['state']}, qty={row['base_qty']:.10f}, "
                f"avg={row['avg_entry']:.2f}, invested=${row['invested_quote']:.2f}, "
                f"realized=${row['realized_pnl']:.2f}, tp1={row['tp1_done']}, tp2={row['tp2_done']}, stop={row['stop_done']}"
            )
