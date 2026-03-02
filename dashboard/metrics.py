from __future__ import annotations

from typing import Optional

import pandas as pd


def latest_price(df_prices: pd.DataFrame, product_id: str) -> Optional[float]:
    if df_prices.empty:
        return None

    rows = df_prices[df_prices["product_id"] == product_id]
    if rows.empty:
        return None

    if "ts" in rows.columns:
        rows = rows.sort_values("ts")

    return float(rows.iloc[-1]["price"])


def format_usd(value: float) -> str:
    return f"${value:,.2f}"


def build_unrealized_pnl(
    positions: pd.DataFrame,
    btc_price: Optional[float],
    eth_price: Optional[float],
) -> float:
    total_unreal = 0.0
    if positions.empty:
        return total_unreal

    for _, p in positions.iterrows():
        product_id = p["product_id"]
        current_px = btc_price if product_id == "BTC-USD" else eth_price if product_id == "ETH-USD" else None
        if current_px is None:
            continue
        total_unreal += (float(current_px) - float(p["avg_entry"])) * float(p["base_qty"])

    return total_unreal


def compute_asset_pnl_rows(prices: pd.DataFrame, positions: pd.DataFrame) -> pd.DataFrame:
    if positions.empty:
        return positions

    last_prices = (
        prices.sort_values("ts")
        .groupby("product_id")["price"]
        .last()
        .to_dict()
        if not prices.empty
        else {}
    )

    df = positions.copy()
    df["last_price"] = df["product_id"].map(lambda pid: float(last_prices.get(pid)) if pid in last_prices else None)
    df["unrealized_pnl"] = df.apply(
        lambda r: (float(r["last_price"]) - float(r["avg_entry"])) * float(r["base_qty"])
        if pd.notna(r["last_price"])
        else 0.0,
        axis=1,
    )
    df["total_pnl"] = df["unrealized_pnl"] + df["realized_pnl"]

    for col in ["tp1_done", "tp2_done", "stop_done"]:
        if col in df.columns:
            df[col] = df[col].astype(bool)

    return df


def last_db_tick_ts(prices: pd.DataFrame) -> Optional[pd.Timestamp]:
    if prices.empty or "ts" not in prices.columns:
        return None
    return prices["ts"].max()


def load_equity_curve(prices: pd.DataFrame, positions: pd.DataFrame) -> pd.DataFrame:
    if prices.empty:
        return pd.DataFrame(columns=["ts", "equity"])

    pos_map = {}
    for _, row in positions.iterrows():
        pos_map[row["product_id"]] = {
            "qty": float(row["base_qty"]),
            "avg": float(row["avg_entry"]),
            "realized": float(row["realized_pnl"]),
        }

    pivot = prices.pivot_table(index="ts", columns="product_id", values="price", aggfunc="last").ffill().reset_index()

    equity_vals = []
    for _, row in pivot.iterrows():
        total_realized = 0.0
        total_unreal = 0.0
        for product_id, p in pos_map.items():
            total_realized += p["realized"]
            px_val = row.get(product_id)
            if pd.notna(px_val):
                total_unreal += (float(px_val) - p["avg"]) * p["qty"]
        equity_vals.append(total_realized + total_unreal)

    pivot["equity"] = equity_vals
    return pivot[["ts", "equity"]]