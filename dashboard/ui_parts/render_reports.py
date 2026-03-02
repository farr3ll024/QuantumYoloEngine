from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd
import plotly.express as px
import streamlit as st
import yaml

from ..db import load_events, load_orders, load_positions, load_price_ticks
from ..metrics import build_unrealized_pnl, load_equity_curve
from ..strategy_manager import load_strategy_yaml
from ..theme import THEME
from .plotly_theme import PLOTLY_CONFIG, apply_dark_plotly_theme


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


def _summary_value(bundle: ReportBundle, metric: str) -> Optional[float]:
    df = bundle.summary
    if df.empty:
        return None
    rows = df[df["metric"] == metric]
    if rows.empty:
        return None
    try:
        return float(rows.iloc[0]["value"])
    except Exception:
        return None


def _fmt_money(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"${v:,.2f}"


def _fmt_pct(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"{v * 100:.1f}%"


def _build_trade_rounds(events: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """
    reconstruct trade rounds from event sequence:
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

        for _, r in g.iterrows():
            et = str(r["event_type"])
            ts = r["ts"]

            if et == "entry_filled":
                open_entry = ts
                continue

            if open_entry is None:
                continue

            if et in {"tp2_filled", "stop_filled"}:
                exit_ts = ts
                exit_type = "tp2" if et == "tp2_filled" else "stop"

                pxg = px[px["product_id"] == product_id]
                window = pxg[(pxg["ts"] >= open_entry) & (pxg["ts"] <= exit_ts)]
                if window.empty:
                    mfe = None
                    mae = None
                    entry_px = None
                    exit_px = None
                else:
                    entry_px = float(window.iloc[0]["price"])
                    exit_px = float(window.iloc[-1]["price"])
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
                        "entry_px": entry_px,
                        "exit_px": exit_px,
                        "mfe": mfe,
                        "mae": mae,
                    }
                )

                open_entry = None

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

    ok, data, err = load_strategy_yaml(strategy_config_path)
    if ok and data is not None:
        strategy_yaml_text = yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    else:
        strategy_yaml_text = f"# failed to load strategy: {err}\n# path: {strategy_config_path}\n"

    strategy_hash = _sha256_text(strategy_yaml_text)

    btc_last = None
    eth_last = None
    if not prices.empty:
        last_prices = prices.sort_values("ts").groupby("product_id")["price"].last().to_dict()
        btc_last = float(last_prices.get("BTC-USD")) if "BTC-USD" in last_prices else None
        eth_last = float(last_prices.get("ETH-USD")) if "ETH-USD" in last_prices else None

    total_realized = float(positions["realized_pnl"].sum()) if not positions.empty else 0.0
    total_unreal = build_unrealized_pnl(positions, btc_last, eth_last)
    total_pnl = total_realized + total_unreal

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


def _build_zip_bundle(bundle: ReportBundle) -> bytes:
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("summary.csv", bundle.summary.to_csv(index=False))
        z.writestr("equity_curve.csv", bundle.equity.to_csv(index=False))
        z.writestr("events.csv", bundle.events.to_csv(index=False))
        z.writestr("orders.csv", bundle.orders.to_csv(index=False))
        z.writestr("positions.csv", bundle.positions.to_csv(index=False))
        z.writestr("trades.csv", bundle.trades.to_csv(index=False))
        z.writestr("strategy_snapshot.yaml", bundle.strategy_yaml_text)

        summary_json = json.dumps(bundle.summary.to_dict(orient="records"), indent=2)
        z.writestr("summary.json", summary_json)

        z.writestr(
            "README.md",
            f"""# Quantum Yolo Engine Reports

strategy_hash_sha256: {bundle.strategy_hash}

## Files
- summary.csv: KPI metrics for this build
- trades.csv: reconstructed trade rounds (entry→exit) with duration + MFE/MAE (if available)
- equity_curve.csv: equity curve derived from ticks + position map
- events.csv / orders.csv / positions.csv: raw runtime tables
- strategy_snapshot.yaml: YAML snapshot used to generate this report
- summary.json: JSON form of summary.csv

## Notes
- This report currently snapshots the strategy file on disk at build time.
  To guarantee attribution across strategy revisions, persist a strategy hash in DB when the engine starts (recommended).
""",
        )

    mem.seek(0)
    return mem.read()


def render_reports_tab(db_path: str, strategy_config_path: str) -> None:
    # header row
    bundle: Optional[ReportBundle] = st.session_state.get("_report_bundle")
    last_built: Optional[str] = st.session_state.get("_report_last_built")

    left, right = st.columns([2, 1])
    with left:
        st.subheader("reports")
        st.caption("export strategy-aware performance reports to optimize your strategy.")
    with right:
        if bundle:
            st.markdown(
                f"<div style='text-align:right;'>"
                f"<div style='font-size:12px; color:{THEME.text_muted}; font-weight:700;'>strategy hash</div>"
                f"<div style='font-size:14px; font-weight:900; color:{THEME.primary};'>"
                f"{bundle.strategy_hash[:12]}…</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        if last_built:
            st.caption(f"last built: {last_built}")

    # build card
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.write({"db_path": db_path, "strategy_path": strategy_config_path})
        with c2:
            build = st.button("build reports", type="primary", width="stretch")

    if build:
        with st.spinner("building reports…"):
            bundle = _build_report_bundle(db_path=db_path, strategy_config_path=strategy_config_path)
        st.session_state._report_bundle = bundle
        st.session_state._report_last_built = datetime.now(timezone.utc).isoformat(timespec="seconds")
        st.rerun()

    bundle = st.session_state.get("_report_bundle")
    if not bundle:
        st.info("click **build reports** to generate exportable report files.")
        return

    # KPI cards
    total_pnl = _summary_value(bundle, "total_pnl")
    realized = _summary_value(bundle, "total_realized_pnl")
    unreal = _summary_value(bundle, "total_unrealized_pnl")
    max_dd = _summary_value(bundle, "max_drawdown")
    entries = _summary_value(bundle, "entries_filled") or 0.0
    stops = _summary_value(bundle, "stops_filled") or 0.0
    tp2 = _summary_value(bundle, "tp2_filled") or 0.0

    stop_rate = (float(stops) / float(entries)) if entries > 0 else None
    tp2_rate = (float(tp2) / float(entries)) if entries > 0 else None

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        with st.container(border=True):
            st.metric("total pnl", _fmt_money(total_pnl))
    with k2:
        with st.container(border=True):
            st.metric("realized pnl", _fmt_money(realized))
    with k3:
        with st.container(border=True):
            st.metric("unrealized pnl", _fmt_money(unreal))
    with k4:
        with st.container(border=True):
            st.metric("max drawdown", _fmt_money(max_dd))
    with k5:
        with st.container(border=True):
            st.metric("stop rate", _fmt_pct(stop_rate), delta=_fmt_pct(tp2_rate) if tp2_rate is not None else None)

    st.divider()

    # section tabs
    t_summary, t_trades, t_equity, t_events, t_exports = st.tabs(
        ["summary", "trades", "equity", "events", "exports"]
    )

    with t_summary:
        with st.container(border=True):
            st.dataframe(bundle.summary, hide_index=True, width="stretch", height=420)

    with t_trades:
        if bundle.trades.empty:
            st.info("no reconstructed trades yet (need entry_filled + tp2_filled/stop_filled sequences).")
        else:
            f1, f2, f3 = st.columns([1, 1, 1])
            with f1:
                asset = st.selectbox("asset", ["all"] + sorted(bundle.trades["product_id"].unique().tolist()))
            with f2:
                exit_type = st.selectbox("exit type", ["all", "tp2", "stop"])
            with f3:
                min_dur = st.number_input("min duration (s)", min_value=0, value=0, step=60)

            df = bundle.trades.copy()
            if asset != "all":
                df = df[df["product_id"] == asset]
            if exit_type != "all":
                df = df[df["exit_type"] == exit_type]
            if min_dur > 0:
                df = df[df["duration_s"] >= float(min_dur)]

            with st.container(border=True):
                st.dataframe(df.tail(75), hide_index=True, width="stretch", height=520)

            counts = df["exit_type"].value_counts().reset_index()
            counts.columns = ["exit_type", "count"]
            fig = px.bar(counts, x="exit_type", y="count")
            apply_dark_plotly_theme(fig)
            st.plotly_chart(fig, config=PLOTLY_CONFIG, use_container_width=True)

    with t_equity:
        if bundle.equity.empty:
            st.info("equity curve not available yet.")
        else:
            fig = px.line(bundle.equity, x="ts", y="equity")
            fig.update_layout(height=420, yaxis_title="pnl ($)")
            apply_dark_plotly_theme(fig)
            st.plotly_chart(fig, config=PLOTLY_CONFIG, use_container_width=True)

            with st.expander("view equity table", expanded=False):
                st.dataframe(bundle.equity.tail(200), hide_index=True, width="stretch", height=420)

    with t_events:
        if bundle.events.empty:
            st.info("no events yet.")
        else:
            c1, c2 = st.columns([1, 2])
            with c1:
                vc = bundle.events["event_type"].value_counts().reset_index()
                vc.columns = ["event_type", "count"]
                fig = px.bar(vc.head(12), x="event_type", y="count")
                apply_dark_plotly_theme(fig)
                st.plotly_chart(fig, config=PLOTLY_CONFIG, use_container_width=True)
            with c2:
                with st.container(border=True):
                    st.dataframe(bundle.events.head(300), hide_index=True, width="stretch", height=520)

    with t_exports:
        st.markdown("### export bundle")
        zip_bytes = _build_zip_bundle(bundle)
        st.download_button(
            "download report bundle (.zip)",
            data=zip_bytes,
            file_name=f"qye_reports_{bundle.strategy_hash[:10]}.zip",
            mime="application/zip",
            type="primary",
        )

        st.divider()
        st.markdown("### individual exports")
        c1, c2, c3 = st.columns(3)
        with c1:
            _download_df("download summary.csv", bundle.summary, "summary.csv")
            _download_df("download trades.csv", bundle.trades, "trades.csv")
        with c2:
            _download_df("download equity_curve.csv", bundle.equity, "equity_curve.csv")
            _download_df("download positions.csv", bundle.positions, "positions.csv")
        with c3:
            _download_df("download events.csv", bundle.events, "events.csv")
            _download_df("download orders.csv", bundle.orders, "orders.csv")

        st.divider()
        st.markdown("### strategy snapshot")
        st.code(bundle.strategy_yaml_text, language="yaml")
        st.download_button(
            "download strategy_snapshot.yaml",
            data=bundle.strategy_yaml_text.encode("utf-8"),
            file_name="strategy_snapshot.yaml",
            mime="text/yaml",
        )

        st.divider()
        st.markdown("### json exports")
        summary_json = json.dumps(bundle.summary.to_dict(orient="records"), indent=2)
        st.download_button(
            "download summary.json",
            data=summary_json.encode("utf-8"),
            file_name="summary.json",
            mime="application/json",
        )
