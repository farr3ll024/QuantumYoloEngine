from __future__ import annotations

import re
from typing import Any, Optional, Set, Tuple

import pandas as pd

SIGNAL_EVENT_TYPES: Set[str] = {"entry_filled", "tp1_filled", "tp2_filled", "stop_filled", "stop_moved"}

RULE_MAP = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "1h": "1H",
    "4h": "4H",
    "1d": "1D",
}


def apply_asset_focus(df: pd.DataFrame, asset_focus: str) -> pd.DataFrame:
    if df.empty or asset_focus == "all" or "product_id" not in df.columns:
        return df
    return df[df["product_id"] == asset_focus]


def last_and_prev_price(prices: pd.DataFrame, product_id: str) -> Tuple[Optional[float], Optional[float]]:
    if prices.empty or "product_id" not in prices.columns:
        return None, None

    df = prices[prices["product_id"] == product_id]
    if df.empty or "ts" not in df.columns or "price" not in df.columns:
        return None, None

    df = df.sort_values("ts")
    last_px = float(df.iloc[-1]["price"]) if pd.notna(df.iloc[-1]["price"]) else None
    if len(df) < 2:
        return last_px, None
    prev_px = float(df.iloc[-2]["price"]) if pd.notna(df.iloc[-2]["price"]) else None
    return last_px, prev_px


def delta_and_pct(last_px: Optional[float], prev_px: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
    if last_px is None or prev_px is None or prev_px == 0:
        return None, None
    d = last_px - prev_px
    pct = (d / prev_px) * 100.0
    return d, pct


def build_ohlc_from_ticks(prices: pd.DataFrame, product_id: str, interval: str) -> pd.DataFrame:
    if prices.empty or "product_id" not in prices.columns:
        return pd.DataFrame()

    df = prices[prices["product_id"] == product_id].copy()
    if df.empty:
        return pd.DataFrame()

    df = df.dropna(subset=["ts", "price"]).sort_values("ts")
    df = df.set_index("ts")

    rule = RULE_MAP.get(interval, "5min")
    ohlc = df["price"].resample(rule).agg(["first", "max", "min", "last"]).dropna()
    ohlc = ohlc.rename(columns={"first": "open", "max": "high", "min": "low", "last": "close"}).reset_index()
    return ohlc


def apply_events_filters(
    events: pd.DataFrame,
    asset_focus: str,
    only_signals: bool,
    levels: Set[str],
    event_types: Set[str],
    text_query: str,
) -> pd.DataFrame:
    if events.empty:
        return events

    df = apply_asset_focus(events, asset_focus)

    if only_signals and "event_type" in df.columns:
        df = df[df["event_type"].isin(SIGNAL_EVENT_TYPES)]

    if levels and "level" in df.columns:
        df = df[df["level"].isin(levels)]

    if event_types and "event_type" in df.columns:
        df = df[df["event_type"].isin(event_types)]

    q = (text_query or "").strip().lower()
    if q:
        hay = (
            df.get("message", pd.Series([], dtype=str)).astype(str).str.lower()
            + " "
            + df.get("event_type", pd.Series([], dtype=str)).astype(str).str.lower()
            + " "
            + df.get("product_id", pd.Series([], dtype=str)).astype(str).str.lower()
        )
        df = df[hay.str.contains(q, na=False)]

    return df


def extract_price_from_message(msg: str) -> Optional[float]:
    m = re.search(r"at\s+([0-9]+(?:\.[0-9]+)?)", msg or "")
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def nearest_price_at_or_before(px: pd.DataFrame, ts: pd.Timestamp) -> Optional[float]:
    if px.empty or "ts" not in px.columns or "price" not in px.columns:
        return None
    i = px["ts"].searchsorted(ts, side="right") - 1
    if i < 0:
        return None
    v = px.iloc[int(i)]["price"]
    return float(v) if pd.notna(v) else None


def build_trade_event_markers(
    prices: pd.DataFrame,
    events: pd.DataFrame,
    asset_focus: str,
    max_markers: int = 500,
) -> pd.DataFrame:
    if prices.empty or events.empty:
        return pd.DataFrame()

    px = prices.sort_values("ts").copy()
    ev = events.copy()

    if "event_type" not in ev.columns:
        return pd.DataFrame()

    ev = ev[ev["event_type"].isin(SIGNAL_EVENT_TYPES)]
    if ev.empty:
        return pd.DataFrame()

    px = apply_asset_focus(px, asset_focus)
    ev = apply_asset_focus(ev, asset_focus)

    if ev.empty or px.empty:
        return pd.DataFrame()

    ev = ev.sort_values("ts", ascending=True).tail(max_markers)

    rows: list[dict[str, Any]] = []
    for _, r in ev.iterrows():
        e_ts = r.get("ts")
        if pd.isna(e_ts):
            continue

        msg = str(r.get("message", ""))
        fill_px = extract_price_from_message(msg)

        product_id = str(r.get("product_id") or "")
        px_pid = px if asset_focus != "all" else px[px["product_id"] == product_id]

        y = fill_px if fill_px is not None else nearest_price_at_or_before(px_pid[["ts", "price"]], e_ts)
        if y is None:
            continue

        rows.append(
            {
                "ts": e_ts,
                "product_id": product_id,
                "event_type": str(r.get("event_type") or ""),
                "message": msg,
                "y": float(y),
            }
        )

    return pd.DataFrame(rows)