# dashboard/ui/render_reports.py
from __future__ import annotations

import io
import json
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st
import yaml

from ..db import load_events, load_orders, load_positions, load_price_ticks
from ..metrics import build_unrealized_pnl, load_equity_curve
from ..strategy_manager import load_strategy_yaml
from .data import SIGNAL_EVENT_TYPES


@dataclass(frozen=True)
class ReportBundle:
    summary: pd.DataFrame
    equity: pd.DataFrame
    events: pd.DataFrame
    orders: pd.DataFrame
    positions: pd.DataFrame
    trades: pd.DataFrame
    strategy_yaml_text: str
    strategy_hash: str


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _max_drawdown(equity: pd.DataFrame) -> float:
    if equity.empty or "equity" not in equity.columns:
        return 0.0
    s = equity["equity"].astype(float)
    peak = s.cummax()
    dd = s - peak
    return float(dd.min())  # negative number (worst drawdown)


def _build_trade_rounds(events: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """
    phase 2: reconstruct trade rounds from event sequence:
      - entry_filled opens a round
      - tp2_filled or stop_filled closes a round
    computes duration + MFE/MAE using price ticks between entry and exit.
    """
    if events.empty or prices.empty:
        return pd.DataFrame()

    required = {"ts", "product_id", "event_type"}
    if not required.issubset(set(events.columns)):
        return pd.DataFrame()

    ev = events.dropna(subset=["ts"]).copy()
    ev["product_id"] = ev["product_id"].fillna("").astype(str)
    ev = ev.sort_values(["product_id", "ts"], ascending=True)

    px = prices.dropna(subset=["ts", "product_id", "price"]).copy()
    px["product_id"] = px["product_id"].astype(str)
    px = px.sort_values(["product_id", "ts"], ascending=True)

    rows: list[dict[str, Any]] = []

    for product_id, g in ev.groupby("product_id", sort=False):
        if not product_id:
            continue

        g = g[g["event_type"].isin({"entry_filled", "tp1_filled", "tp2_filled", "stop_filled", "stop_moved"})]
        if g.empty:
            continue

        open_entry: Optional[pd.Timestamp] = None
        entry_event: Optional[pd.Series] = None

        for _, r in g.iterrows():
            et = str(r["event_type"])
            ts = r["ts"]

            if et == "entry_filled":
                # start a new round; if one is already open, we "restart" (should be rare)
                open_entry = ts
                entry_event = r
                continue

            if open_entry is None:
                continue

            if et in {"tp2_filled", "stop_filled"}:
                exit_ts = ts
                exit_type = "tp2" if et == "tp2_filled" else "stop"

                # slice prices between entry and exit
                pxg = px[px["product_id"] == product_id]
                window = pxg[(pxg["ts"] >= open_entry) & (pxg["ts"] <= exit_ts)]
                if window.empty:
                    mfe = None
                    mae = None
                else:
                    # use first tick after entry as entry price proxy if needed
                    entry_px = float(window.iloc[0]["price"])
                    high = float(window["price"].max())
                    low = float(window["price"].min())
                    mfe = high - entry_px
                    mae = low - entry_px

                rows.append(
                    {
                        "product_id": product_id,
                        "entry_ts": open_entry,
                        "exit_ts": exit_ts,
                        "duration_s": float((exit_ts - open_entry).total_seconds()),
                        "exit_type": exit_type,
                        "mfe": mfe,
                        "mae": mae,
                    }
                )

                open_entry = None
                entry_event = None

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.sort_values(["product_id", "entry_ts"], ascending=True)
    return df


def _build_report_bundle(db_path: str, strategy_config_path: str) -> ReportBundle:
    prices = load_price_ticks(db_path)
    positions = load_positions(db_path)
    orders = load_orders(db_path)
    events = load_events(db_path, limit=5000)

    equity = load_equity_curve(prices, positions)

    # strategy snapshot (from disk)
    ok, data, err = load_strategy_yaml(strategy_config_path)
    if ok and data is not None:
        strategy_yaml_text = yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    else:
        strategy_yaml_text = f"# failed to load strategy: {err}\n# path: {strategy_config_path}\n"

    strategy_hash = _sha256_text(strategy_yaml_text)

    # pnl totals
    btc_last = None
    eth_last = None
    if not prices.empty:
        # latest per product
        last_prices = prices.sort_values("ts").groupby("product_id")["price"].last().to_dict()
        btc_last = float(last_prices.get("BTC-USD")) if "BTC-USD" in last_prices else None
        eth_last = float(last_prices.get("ETH-USD")) if "ETH-USD" in last_prices else None

    total_realized = float(positions["realized_pnl"].sum()) if not positions.empty else 0.0
    total_unreal = build_unrealized_pnl(positions, btc_last, eth_last)
    total_pnl = total_realized + total_unreal

    # event stats
    event_counts = (
        events["event_type"].value_counts().to_dict()
        if (not events.empty and "event_type" in events.columns)
        else {}
    )
    entries = int(event_counts.get("entry_filled", 0))
    tp1 = int(event_counts.get("tp1_filled", 0))
    tp2 = int(event_counts.get("tp2_filled", 0))
    stops = int(event_counts.get("stop_filled", 0))
    stop_moved = int(event_counts.get("stop_moved", 0))

    max_dd = _max_drawdown(equity)

    summary = pd.DataFrame(
        [
            {"metric": "strategy_path", "value": strategy_config_path},
            {"metric": "strategy_hash_sha256", "value": strategy_hash},
            {"metric": "prices_rows", "value": int(len(prices))},
            {"metric": "events_rows", "value": int(len(events))},
            {"metric": "orders_rows", "value": int(len(orders))},
            {"metric": "positions_rows", "value": int(len(positions))},
            {"metric": "total_realized_pnl", "value": total_realized},
            {"metric": "total_unrealized_pnl", "value": total_unreal},
            {"metric": "total_pnl", "value": total_pnl},
            {"metric": "max_drawdown", "value": max_dd},
            {"metric": "entries_filled", "value": entries},
            {"metric": "tp1_filled", "value": tp1},
            {"metric": "tp2_filled", "value": tp2},
            {"metric": "stops_filled", "value": stops},
            {"metric": "stop_moved", "value": stop_moved},
        ]
    )

    trades = _build_trade_rounds(events=events, prices=prices)

    return ReportBundle(
        summary=summary,
        equity=equity,
        events=events,
        orders=orders,
        positions=positions,
        trades=trades,
        strategy_yaml_text=strategy_yaml_text,
        strategy_hash=strategy_hash,
    )


def _download_df(label: str, df: pd.DataFrame, filename: str) -> None:
    if df.empty:
        st.download_button(label, data=b"", file_name=filename, mime="text/csv", disabled=True)
        return
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(label, data=csv_bytes, file_name=filename, mime="text/csv")


def render_reports_tab(db_path: str, strategy_config_path: str) -> None:
    st.subheader("reports")
    st.caption("export strategy-aware performance reports to optimize your strategy.")

    with st.container(border=True):
        st.write({"db_path": db_path, "strategy_path": strategy_config_path})

    if st.button("build reports", type="primary", width="stretch"):
        bundle = _build_report_bundle(db_path=db_path, strategy_config_path=strategy_config_path)
        st.session_state._report_bundle = bundle  # cache for downloads


    bundle: Optional[ReportBundle] = st.session_state.get("_report_bundle")
    if not bundle:
        st.info("click **build reports** to generate exportable report files.")
        return

    # show quick summary
    with st.container(border=True):
        st.markdown("### summary")
        st.dataframe(bundle.summary, hide_index=True, width="stretch")

    c1, c2, c3 = st.columns(3)
    with c1:
        _download_df("download summary.csv", bundle.summary, "summary.csv")
        _download_df("download equity_curve.csv", bundle.equity, "equity_curve.csv")
    with c2:
        _download_df("download events.csv", bundle.events, "events.csv")
        _download_df("download orders.csv", bundle.orders, "orders.csv")
    with c3:
        _download_df("download positions.csv", bundle.positions, "positions.csv")
        _download_df("download trades.csv", bundle.trades, "trades.csv")

    # strategy snapshot download
    st.divider()
    st.markdown("### strategy snapshot")
    st.code(bundle.strategy_yaml_text, language="yaml")
    st.download_button(
        "download strategy_snapshot.yaml",
        data=bundle.strategy_yaml_text.encode("utf-8"),
        file_name="strategy_snapshot.yaml",
        mime="text/yaml",
    )

    # optional: json export bundle (summary only to keep it small)
    st.divider()
    st.markdown("### json exports")
    summary_json = json.dumps(bundle.summary.to_dict(orient="records"), indent=2)
    st.download_button("download summary.json", data=summary_json.encode("utf-8"), file_name="summary.json", mime="application/json")