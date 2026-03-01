# dashboard/ui.py
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Set, Tuple

import pandas as pd
import plotly.express as plotly_express
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from .constants import APP_TITLE
from .db import clear_all_data, load_events, load_orders, load_positions, load_price_ticks
from .metrics import (
    build_unrealized_pnl,
    compute_asset_pnl_rows,
    format_usd,
    last_db_tick_ts,
    load_equity_curve,
)

DEFAULT_DB_PATH = Path("runtime/db/paper_trader.db")

# trade-related event types we can overlay on the chart
SIGNAL_EVENT_TYPES: Set[str] = {"entry_filled", "tp1_filled", "tp2_filled", "stop_filled", "stop_moved"}

# plotly config (streamlit wants this passed via `config=...`, not kwargs)
PLOTLY_CONFIG = {
    "displayModeBar": True,  # keep toolbar available
    "scrollZoom": True,
    "responsive": True,
}

# event marker colors (dark theme friendly)
EVENT_COLORS: Dict[str, str] = {
    "entry_filled": "#34d399",  # green
    "tp1_filled": "#60a5fa",  # blue
    "tp2_filled": "#a78bfa",  # purple
    "stop_filled": "#f87171",  # red
    "stop_moved": "#fbbf24",  # amber
}

# -----------------------------
# fragments support (streamlit >= 1.33-ish)
# -----------------------------
_HAS_FRAGMENTS = hasattr(st, "fragment")
if _HAS_FRAGMENTS:
    fragment = st.fragment  # type: ignore[attr-defined]
else:

    def fragment(*_args, **_kwargs):  # type: ignore[no-redef]
        # fallback decorator: run function normally
        def deco(fn):
            return fn

        return deco


# -----------------------------
# path helpers
# -----------------------------
def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _normalize_db_path(value: str) -> str:
    p = Path(value).expanduser()
    _ensure_parent_dir(p)
    return str(p)


# -----------------------------
# format helpers
# -----------------------------
def money_col(label: str) -> st.column_config.NumberColumn:
    return st.column_config.NumberColumn(label=label, format="$%.2f")


def qty_col(label: str) -> st.column_config.NumberColumn:
    return st.column_config.NumberColumn(label=label, format="%.8f")


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _safe_dt(ts: Optional[pd.Timestamp]) -> Optional[dt.datetime]:
    if ts is None or pd.isna(ts):
        return None
    if ts.tzinfo is None:
        return ts.to_pydatetime().replace(tzinfo=dt.timezone.utc)
    return ts.to_pydatetime()


def _format_seconds(s: Optional[float]) -> str:
    if s is None:
        return "-"
    if s < 60:
        return f"{s:.0f}s"
    if s < 3600:
        return f"{s/60:.1f}m"
    return f"{s/3600:.2f}h"


def _pnl_color(value: float) -> str:
    if value > 0:
        return "#16a34a"  # green
    if value < 0:
        return "#dc2626"  # red
    return "#6b7280"  # gray


def _colored_money(value: float, font_px: int = 20) -> str:
    color = _pnl_color(value)
    sign = "" if value < 0 else "+"
    return (
        f"<span style='color:{color}; font-weight:800; font-size:{font_px}px; line-height:1.1'>"
        f"{sign}{format_usd(value)}</span>"
    )


def _label(text: str, font_px: int = 14) -> str:
    return f"<div style='font-size:{font_px}px; font-weight:700; color: rgba(255,255,255,0.72); margin-bottom:4px'>{text}</div>"


def _last_and_prev_price(prices: pd.DataFrame, product_id: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Returns (last_price, prev_price) for product_id based on ts ordering.
    """
    if prices.empty or "product_id" not in prices.columns:
        return None, None

    df = prices[prices["product_id"] == product_id]
    if df.empty or "ts" not in df.columns or "price" not in df.columns:
        return None, None

    df = df.sort_values("ts")
    last_row = df.iloc[-1]
    last_px = float(last_row["price"]) if pd.notna(last_row["price"]) else None

    if len(df) < 2:
        return last_px, None

    prev_row = df.iloc[-2]
    prev_px = float(prev_row["price"]) if pd.notna(prev_row["price"]) else None
    return last_px, prev_px


def _delta_and_pct(last_px: Optional[float], prev_px: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
    if last_px is None or prev_px is None:
        return None, None
    if prev_px == 0:
        return None, None
    d = last_px - prev_px
    pct = (d / prev_px) * 100.0
    return d, pct


# -----------------------------
# plotly theme helpers
# -----------------------------
def _apply_dark_plotly_theme(fig: go.Figure) -> None:
    """
    Makes plotly charts dark without relying on global templates.
    Also forces a non-black colorway so lines/markers stay visible.
    """
    fig.update_layout(
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0b1220",
        font=dict(color="rgba(255,255,255,0.88)"),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            font=dict(color="rgba(255,255,255,0.85)"),
        ),
        margin=dict(l=60, r=20, t=40, b=60),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(15,23,42,0.95)", font=dict(color="white")),
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.18)",
        zeroline=False,
        tickfont=dict(color="rgba(255,255,255,0.78)", size=11),
        title=dict(font=dict(color="rgba(255,255,255,0.85)", size=12)),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.18)",
        zeroline=False,
        tickfont=dict(color="rgba(255,255,255,0.78)", size=11),
        title=dict(font=dict(color="rgba(255,255,255,0.85)", size=12)),
    )

    fig.update_layout(
        colorway=[
            "#60a5fa",
            "#a78bfa",
            "#34d399",
            "#fbbf24",
            "#f87171",
            "#22d3ee",
            "#fb7185",
            "#cbd5e1",
        ]
    )


# -----------------------------
# df filtering helpers
# -----------------------------
def _apply_asset_focus(df: pd.DataFrame, asset_focus: str) -> pd.DataFrame:
    if df.empty:
        return df
    if asset_focus == "all":
        return df
    if "product_id" not in df.columns:
        return df
    return df[df["product_id"] == asset_focus]


def _apply_events_filters(
    events: pd.DataFrame,
    asset_focus: str,
    only_signals: bool,
    levels: Set[str],
    event_types: Set[str],
    text_query: str,
) -> pd.DataFrame:
    if events.empty:
        return events

    df = _apply_asset_focus(events, asset_focus)

    if only_signals:
        df = df[df["event_type"].isin(SIGNAL_EVENT_TYPES)]

    if levels:
        df = df[df["level"].isin(levels)]

    if event_types:
        df = df[df["event_type"].isin(event_types)]

    q = (text_query or "").strip().lower()
    if q:
        hay = (
            df["message"].astype(str).str.lower()
            + " "
            + df["event_type"].astype(str).str.lower()
            + " "
            + df["product_id"].astype(str).str.lower()
        )
        df = df[hay.str.contains(q, na=False)]

    return df


# -----------------------------
# sidebar tools
# -----------------------------
def render_dev_tools(db_path: str) -> None:
    st.sidebar.divider()
    with st.sidebar.expander("developer tools", expanded=False):
        st.caption("danger zone")

        if "confirm_clear" not in st.session_state:
            st.session_state.confirm_clear = False

        if not st.session_state.confirm_clear:
            if st.button("clear all data", type="primary", width="stretch"):
                st.session_state.confirm_clear = True
                st.warning("click again to confirm clearing all data.")
        else:
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("confirm clear", type="primary", width="stretch"):
                    try:
                        clear_all_data(db_path)

                        load_price_ticks.clear()
                        load_positions.clear()
                        load_orders.clear()
                        load_events.clear()

                        st.session_state.confirm_clear = False
                        st.success("cleared ✅")
                        st.rerun()
                    except Exception as ex:
                        st.session_state.confirm_clear = False
                        st.error("failed to clear data")
                        st.exception(ex)
            with col_b:
                if st.button("cancel", width="stretch"):
                    st.session_state.confirm_clear = False


# -----------------------------
# trade overlay helpers
# -----------------------------
def _extract_price_from_message(msg: str) -> Optional[float]:
    m = re.search(r"\bat\s+([0-9]+(?:\.[0-9]+)?)\b", msg or "")
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _nearest_price_at_or_before(px: pd.DataFrame, ts: pd.Timestamp) -> Optional[float]:
    if px.empty or "ts" not in px.columns or "price" not in px.columns:
        return None
    i = px["ts"].searchsorted(ts, side="right") - 1
    if i < 0:
        return None
    v = px.iloc[int(i)]["price"]
    return float(v) if pd.notna(v) else None


def _build_trade_event_markers(
    prices: pd.DataFrame,
    events: pd.DataFrame,
    asset_focus: str,
    max_markers: int = 500,
) -> pd.DataFrame:
    """
    markers_df columns: ts, product_id, event_type, message, y
    """
    if prices.empty or events.empty:
        return pd.DataFrame()

    px = prices.sort_values("ts").copy()
    ev = events.copy()

    ev = ev[ev["event_type"].isin(SIGNAL_EVENT_TYPES)]
    if ev.empty:
        return pd.DataFrame()

    px = _apply_asset_focus(px, asset_focus)
    ev = _apply_asset_focus(ev, asset_focus)

    if ev.empty or px.empty:
        return pd.DataFrame()

    ev = ev.sort_values("ts", ascending=True).tail(max_markers)

    rows = []
    for _, r in ev.iterrows():
        e_ts = r.get("ts")
        if pd.isna(e_ts):
            continue

        msg = str(r.get("message", ""))
        fill_px = _extract_price_from_message(msg)

        product_id = str(r.get("product_id") or "")
        px_pid = px if asset_focus != "all" else px[px["product_id"] == product_id]

        y = fill_px if fill_px is not None else _nearest_price_at_or_before(px_pid[["ts", "price"]], e_ts)
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


# -----------------------------
# render panels
# -----------------------------
def _render_status_rail(
    prices: pd.DataFrame,
    positions: pd.DataFrame,
    last_tick: Optional[pd.Timestamp],
    asset_focus: str,
) -> None:
    btc_last, btc_prev = _last_and_prev_price(prices, "BTC-USD")
    eth_last, eth_prev = _last_and_prev_price(prices, "ETH-USD")

    btc_d, btc_pct = _delta_and_pct(btc_last, btc_prev)
    eth_d, eth_pct = _delta_and_pct(eth_last, eth_prev)

    total_realized = float(positions["realized_pnl"].sum()) if not positions.empty else 0.0
    total_unreal = build_unrealized_pnl(positions, btc_last, eth_last)
    total_pnl = total_realized + total_unreal

    last_tick_dt = _safe_dt(last_tick)
    age_s: Optional[float] = None
    if last_tick_dt is not None:
        age_s = max(0.0, (_utc_now() - last_tick_dt).total_seconds())

    c1, c2, c3, c4, c5, c6 = st.columns([1.15, 1.15, 1, 1, 1, 1])

    btc_value = f"${btc_last:,.2f}" if btc_last is not None else "-"
    eth_value = f"${eth_last:,.2f}" if eth_last is not None else "-"

    btc_delta = "-" if btc_d is None or btc_pct is None else f"{btc_d:+,.2f} ({btc_pct:+.2f}%)"
    eth_delta = "-" if eth_d is None or eth_pct is None else f"{eth_d:+,.2f} ({eth_pct:+.2f}%)"

    c1.metric("btc", btc_value, delta=btc_delta, delta_color="normal")
    c2.metric("eth", eth_value, delta=eth_delta, delta_color="normal")

    with c3:
        st.markdown(_label("realized", font_px=15), unsafe_allow_html=True)
        st.markdown(_colored_money(total_realized, font_px=22), unsafe_allow_html=True)

    with c4:
        st.markdown(_label("unrealized", font_px=15), unsafe_allow_html=True)
        st.markdown(_colored_money(total_unreal, font_px=22), unsafe_allow_html=True)

    with c5:
        st.markdown(_label("total pnl", font_px=15), unsafe_allow_html=True)
        st.markdown(_colored_money(total_pnl, font_px=22), unsafe_allow_html=True)

    with c6:
        st.markdown(_label("last tick age", font_px=15), unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:22px; font-weight:800; line-height:1.1'>{_format_seconds(age_s)}</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<div style='margin-top:6px; font-size:16px; color: rgba(255,255,255,0.72)'>asset focus: <b>{asset_focus}</b></div>",
        unsafe_allow_html=True,
    )


def _render_price_panel(
    prices: pd.DataFrame,
    events_for_overlay: pd.DataFrame,
    asset_focus: str,
    last_n_ticks: int,
    show_trade_overlay: bool,
) -> None:
    st.subheader("price chart")

    if prices.empty:
        st.info("no price ticks yet. run paper_trader first.")
        return

    df = prices.copy()
    if last_n_ticks > 0:
        uniq = df[["ts"]].drop_duplicates().sort_values("ts")
        tail = uniq.tail(last_n_ticks)
        df = df.merge(tail, on="ts", how="inner")

    df = _apply_asset_focus(df, asset_focus)

    fig = plotly_express.line(df, x="ts", y="price", color="product_id")
    fig.update_layout(height=420, legend_title_text="")

    if show_trade_overlay and not events_for_overlay.empty:
        markers = _build_trade_event_markers(
            prices=df,
            events=events_for_overlay,
            asset_focus=asset_focus,
            max_markers=500,
        )

        if not markers.empty:
            for event_type in sorted(markers["event_type"].unique().tolist()):
                m = markers[markers["event_type"] == event_type]
                color = EVENT_COLORS.get(event_type, "#cbd5e1")
                fig.add_trace(
                    go.Scatter(
                        x=m["ts"],
                        y=m["y"],
                        mode="markers",
                        name=f"{event_type}",
                        hovertemplate="<b>%{text}</b><br>time=%{x}<br>y=%{y}<extra></extra>",
                        text=m.apply(
                            lambda r: f"{r['product_id']} • {r['event_type']} • {r['message']}",
                            axis=1,
                        ),
                        marker=dict(size=11, symbol="circle", color=color, line=dict(width=0)),
                    )
                )

    _apply_dark_plotly_theme(fig)
    st.plotly_chart(fig, config=PLOTLY_CONFIG)


def _render_equity_panel(equity: pd.DataFrame) -> None:
    st.subheader("equity curve")

    if equity.empty:
        st.info("equity curve will appear after ticks are recorded.")
        return

    fig_eq = plotly_express.line(equity, x="ts", y="equity")
    fig_eq.update_layout(height=260, yaxis_title="pnl ($)")
    _apply_dark_plotly_theme(fig_eq)
    st.plotly_chart(fig_eq, config=PLOTLY_CONFIG)


def _render_positions_panel(prices: pd.DataFrame, positions: pd.DataFrame, table_density: str, asset_focus: str) -> None:
    st.subheader("positions (with pnl)")

    if positions.empty:
        st.info("no positions found")
        return

    pos = compute_asset_pnl_rows(prices, positions)
    pos = _apply_asset_focus(pos, asset_focus)

    display_cols_full = [
        "product_id",
        "state",
        "base_qty",
        "avg_entry",
        "last_price",
        "invested_quote",
        "realized_pnl",
        "unrealized_pnl",
        "total_pnl",
        "tp1_done",
        "tp2_done",
        "stop_done",
        "updated_at",
    ]
    display_cols_compact = [
        "product_id",
        "state",
        "base_qty",
        "avg_entry",
        "last_price",
        "total_pnl",
        "tp1_done",
        "tp2_done",
        "stop_done",
    ]
    cols = display_cols_full if table_density == "full" else display_cols_compact

    if "total_pnl" in pos.columns:
        pos = pos.sort_values("total_pnl", ascending=False)

    column_config = {
        "product_id": st.column_config.TextColumn("asset", width="small"),
        "state": st.column_config.TextColumn("state", width="small"),
        "base_qty": qty_col("qty"),
        "avg_entry": money_col("avg entry"),
        "last_price": money_col("last price"),
        "invested_quote": money_col("invested"),
        "realized_pnl": money_col("realized pnl"),
        "unrealized_pnl": money_col("unrealized pnl"),
        "total_pnl": money_col("total pnl"),
        "tp1_done": st.column_config.CheckboxColumn("tp1", width="small"),
        "tp2_done": st.column_config.CheckboxColumn("tp2", width="small"),
        "stop_done": st.column_config.CheckboxColumn("stop", width="small"),
        "updated_at": st.column_config.TextColumn("updated", width="medium"),
    }

    st.data_editor(
        pos[cols],
        width="stretch",
        hide_index=True,
        disabled=True,
        column_config=column_config,
        height=260 if table_density == "compact" else 360,
    )


def _render_events_panel(events: pd.DataFrame) -> None:
    st.subheader("events")

    if events.empty:
        st.info("no events yet")
        return

    view = events.copy()
    if "ts" in view.columns and not view["ts"].empty:
        view["ts"] = view["ts"].dt.strftime("%Y-%m-%d %H:%M:%S")

    st.data_editor(view.head(500), width="stretch", hide_index=True, disabled=True, height=620)


def _render_orders_panel(orders: pd.DataFrame) -> None:
    st.subheader("orders")

    if orders.empty:
        st.info("no orders found")
        return

    st.data_editor(orders, width="stretch", hide_index=True, disabled=True, height=620)


# -----------------------------
# fragments: live sections
# -----------------------------
def _run_every(refresh_sec: int) -> Optional[dt.timedelta]:
    if refresh_sec <= 0:
        return None
    return dt.timedelta(seconds=int(refresh_sec))


def _with_run_every(fn: Callable[..., Any], refresh_sec: int) -> Callable[..., Any]:
    if not _HAS_FRAGMENTS:
        return fn
    base = getattr(fn, "__wrapped__", fn)
    return fragment(run_every=_run_every(refresh_sec))(base)  # type: ignore[misc]


@fragment
def _frag_status(db_path: str, asset_focus: str) -> None:
    prices = load_price_ticks(db_path)
    positions = load_positions(db_path)
    last_tick = last_db_tick_ts(prices)

    with st.container(border=True):
        if last_tick is None:
            st.warning("no ticks found in db yet")
        else:
            st.caption(f"last tick (utc): {last_tick}")
        _render_status_rail(prices=prices, positions=positions, last_tick=last_tick, asset_focus=asset_focus)


@fragment
def _frag_overview(
    db_path: str,
    asset_focus: str,
    last_n_ticks: int,
    show_trade_overlay: bool,
    table_density: str,
    event_limit: int,
    show_only_signal_events: bool,
    levels_selected: Set[str],
    event_types_selected: Set[str],
    event_search: str,
) -> None:
    prices = load_price_ticks(db_path)
    positions = load_positions(db_path)
    events = load_events(db_path, limit=event_limit)
    equity = load_equity_curve(prices, positions)

    events_filtered = _apply_events_filters(
        events=events,
        asset_focus=asset_focus,
        only_signals=show_only_signal_events,
        levels=levels_selected,
        event_types=event_types_selected,
        text_query=event_search,
    )

    left, right = st.columns([2, 1], gap="large")
    with left:
        with st.container(border=True):
            _render_price_panel(
                prices=prices,
                events_for_overlay=events_filtered,
                asset_focus=asset_focus,
                last_n_ticks=last_n_ticks,
                show_trade_overlay=show_trade_overlay,
            )
        with st.container(border=True):
            _render_equity_panel(equity=equity)

    with right:
        with st.container(border=True):
            _render_positions_panel(
                prices=prices,
                positions=positions,
                table_density=table_density,
                asset_focus=asset_focus,
            )


@fragment
def _frag_events(
    db_path: str,
    asset_focus: str,
    event_limit: int,
    show_only_signal_events: bool,
    levels_selected: Set[str],
    event_types_selected: Set[str],
    event_search: str,
) -> None:
    events = load_events(db_path, limit=event_limit)
    events_filtered = _apply_events_filters(
        events=events,
        asset_focus=asset_focus,
        only_signals=show_only_signal_events,
        levels=levels_selected,
        event_types=event_types_selected,
        text_query=event_search,
    )
    with st.container(border=True):
        _render_events_panel(events_filtered)


@fragment
def _frag_orders(db_path: str, asset_focus: str) -> None:
    orders = load_orders(db_path)
    orders = _apply_asset_focus(orders, asset_focus)
    with st.container(border=True):
        _render_orders_panel(orders)


@fragment
def _frag_diagnostics(db_path: str) -> None:
    prices = load_price_ticks(db_path)
    events = load_events(db_path, limit=500)
    orders = load_orders(db_path)
    positions = load_positions(db_path)

    with st.container(border=True):
        st.subheader("diagnostics")
        st.write(
            {
                "db_path": db_path,
                "prices_rows": int(len(prices)),
                "events_rows": int(len(events)),
                "orders_rows": int(len(orders)),
                "positions_rows": int(len(positions)),
            }
        )


# -----------------------------
# main
# -----------------------------
def run_app() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")

    st.title(APP_TITLE)
    st.caption("A dashboard to experiment with losing money while trading. Enjoy!")

    st.sidebar.subheader("controls")

    db_path = st.sidebar.text_input("sqlite db path", value=str(DEFAULT_DB_PATH))
    db_path = _normalize_db_path(db_path)

    auto_refresh = st.sidebar.checkbox("auto refresh", value=True)
    refresh_sec = st.sidebar.slider("refresh seconds", min_value=1, max_value=10, value=2)

    st.sidebar.divider()
    st.sidebar.subheader("data & focus")

    event_limit = st.sidebar.slider("events to load", min_value=50, max_value=5000, value=500, step=50)
    asset_focus = st.sidebar.selectbox("asset focus", options=["all", "BTC-USD", "ETH-USD"], index=0)

    last_n_ticks = st.sidebar.slider(
        "chart window (unique ticks)",
        min_value=50,
        max_value=2000,
        value=500,
        step=50,
        help="limits the chart to the most recent N unique timestamps",
    )

    show_trade_overlay = st.sidebar.checkbox(
        "overlay trade events on chart",
        value=True,
        help="plots entry/tp/stop events on the price chart",
    )

    st.sidebar.divider()
    st.sidebar.subheader("filters")

    show_only_signal_events = st.sidebar.checkbox("trade events only", value=True)
    event_search = st.sidebar.text_input("event search", value="", placeholder="type to filter…")

    levels_selected = set(
        st.sidebar.multiselect(
            "event levels",
            options=["info", "warn", "error"],
            default=["info", "warn"],
        )
    )

    event_types_selected = set(
        st.sidebar.multiselect(
            "event types",
            options=sorted(SIGNAL_EVENT_TYPES | {"bootstrap_position", "seed_entries"}),
            default=[],
            help="leave empty to show all types (respecting trade-only toggle)",
        )
    )

    st.sidebar.divider()
    st.sidebar.subheader("tables")

    table_density = st.sidebar.radio("positions table layout", options=["full", "compact"], index=0)
    show_orders = st.sidebar.checkbox("show orders tab", value=True)

    render_dev_tools(db_path)

    if auto_refresh and not _HAS_FRAGMENTS:
        st_autorefresh(interval=refresh_sec * 1000, key="paper_trader_refresh")

    frag_status_live = _with_run_every(_frag_status, refresh_sec) if auto_refresh else _frag_status
    frag_overview_live = _with_run_every(_frag_overview, refresh_sec) if auto_refresh else _frag_overview
    frag_events_live = _with_run_every(_frag_events, refresh_sec) if auto_refresh else _frag_events
    frag_orders_live = _with_run_every(_frag_orders, refresh_sec) if auto_refresh else _frag_orders
    frag_diagnostics_live = _with_run_every(_frag_diagnostics, refresh_sec) if auto_refresh else _frag_diagnostics

    frag_status_live(db_path=db_path, asset_focus=asset_focus)

    st.divider()

    tab_names = ["overview", "events", "diagnostics"]
    if show_orders:
        tab_names.insert(1, "orders")
    tabs = st.tabs(tab_names)

    with tabs[0]:
        frag_overview_live(
            db_path=db_path,
            asset_focus=asset_focus,
            last_n_ticks=last_n_ticks,
            show_trade_overlay=show_trade_overlay,
            table_density=table_density,
            event_limit=event_limit,
            show_only_signal_events=show_only_signal_events,
            levels_selected=levels_selected,
            event_types_selected=event_types_selected,
            event_search=event_search,
        )

    if show_orders:
        with tabs[1]:
            frag_orders_live(db_path=db_path, asset_focus=asset_focus)
        events_tab = tabs[2]
        diag_tab = tabs[3]
    else:
        events_tab = tabs[1]
        diag_tab = tabs[2]

    with events_tab:
        frag_events_live(
            db_path=db_path,
            asset_focus=asset_focus,
            event_limit=event_limit,
            show_only_signal_events=show_only_signal_events,
            levels_selected=levels_selected,
            event_types_selected=event_types_selected,
            event_search=event_search,
        )

    with diag_tab:
        frag_diagnostics_live(db_path=db_path)