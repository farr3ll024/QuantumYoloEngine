from __future__ import annotations

import sqlite3
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

from .parsing import parse_ts_series


@st.cache_resource(show_spinner=False)
def get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # reader-friendly pragmas (no behavior change; helps avoid "database is locked")
    try:
        conn.execute("pragma busy_timeout=2000;")
    except Exception:
        pass

    return conn


def clear_all_data(db_path: str) -> None:
    """
    wipes all runtime data but keeps the schema intact
    """
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("delete from price_ticks")
    cur.execute("delete from events")
    cur.execute("delete from orders")
    cur.execute("delete from positions")
    conn.commit()


@st.cache_data(ttl=2, show_spinner=False)
def load_price_ticks(db_path: str) -> pd.DataFrame:
    conn = get_conn(db_path)
    q = """
        select ts, product_id, price
        from price_ticks
        order by id asc \
        """
    df = pd.read_sql_query(q, conn)
    if not df.empty:
        df["ts"] = parse_ts_series(df["ts"])
        df = df.dropna(subset=["ts"])
    return df


@st.cache_data(ttl=2, show_spinner=False)
def load_positions(db_path: str) -> pd.DataFrame:
    conn = get_conn(db_path)
    q = """
        select product_id,
               base_qty,
               avg_entry,
               invested_quote,
               realized_pnl,
               state,
               tp1_done,
               tp2_done,
               stop_done,
               updated_at
        from positions
        order by product_id \
        """
    return pd.read_sql_query(q, conn)


@st.cache_data(ttl=2, show_spinner=False)
def load_orders(db_path: str) -> pd.DataFrame:
    conn = get_conn(db_path)
    q = """
        select order_id,
               product_id,
               order_type,
               rule_id,
               side,
               price,
               quote_size_usd,
               base_size,
               status,
               created_at,
               filled_at
        from orders
        order by created_at desc \
        """
    return pd.read_sql_query(q, conn)


def _events_has_payload_json(conn: sqlite3.Connection) -> bool:
    try:
        cols = conn.execute("pragma table_info(events)").fetchall()
        names = {str(r["name"]) for r in cols}
        return "payload_json" in names
    except Exception:
        return False


@st.cache_data(ttl=2, show_spinner=False)
def load_events(db_path: str, limit: int = 200) -> pd.DataFrame:
    conn = get_conn(db_path)
    limit_i = max(1, min(int(limit), 50_000))

    if _events_has_payload_json(conn):
        q = """
            select id as event_id, ts, level, product_id, event_type, message, payload_json
            from events
            order by id desc limit ? \
            """
    else:
        q = """
            select id as event_id, ts, level, product_id, event_type, message
            from events
            order by id desc limit ? \
            """

    df = pd.read_sql_query(q, conn, params=(limit_i,))
    if not df.empty:
        df["ts"] = parse_ts_series(df["ts"])
        df = df.dropna(subset=["ts"])
        df = df.sort_values("ts", ascending=False)
    return df


@st.cache_data(ttl=2, show_spinner=False)
def load_db_health(db_path: str) -> Dict[str, Any]:
    conn = get_conn(db_path)
    cur = conn.cursor()

    health: Dict[str, Any] = {
        "db_path": db_path,
        "ok": True,
        "tables": [],
        "counts": {},
        "latest": {},
        "errors": [],
    }

    try:
        tables = cur.execute(
            """
            select name
            from sqlite_master
            where type = 'table'
            order by name
            """
        ).fetchall()
        health["tables"] = [str(r["name"]) for r in tables]
    except Exception as ex:
        health["ok"] = False
        health["errors"].append(f"failed listing tables: {type(ex).__name__}: {ex}")
        return health

    def _safe_scalar(sql: str) -> Optional[Any]:
        try:
            row = cur.execute(sql).fetchone()
            if not row:
                return None
            return row[0]
        except Exception:
            return None

    for t in ["price_ticks", "events", "orders", "positions"]:
        if t not in health["tables"]:
            continue
        health["counts"][t] = _safe_scalar(f"select count(1) from {t}")

    if "price_ticks" in health["tables"]:
        health["latest"]["price_ticks.ts"] = _safe_scalar("select max(ts) from price_ticks")

    if "events" in health["tables"]:
        health["latest"]["events.ts"] = _safe_scalar("select max(ts) from events")

    if "orders" in health["tables"]:
        health["latest"]["orders.created_at"] = _safe_scalar("select max(created_at) from orders")
        health["latest"]["orders.filled_at"] = _safe_scalar(
            "select max(filled_at) from orders where filled_at is not null")

    if "positions" in health["tables"]:
        health["latest"]["positions.updated_at"] = _safe_scalar("select max(updated_at) from positions")

    try:
        cur.execute("select 1").fetchone()
    except Exception as ex:
        health["ok"] = False
        health["errors"].append(f"db ping failed: {type(ex).__name__}: {ex}")

    return health
