from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.express as plotly_express
import plotly.graph_objects as go
import streamlit as st

from ..metrics import build_unrealized_pnl, compute_asset_pnl_rows, last_db_tick_ts, load_equity_curve
from ..theme import THEME
from .data import apply_asset_focus, build_ohlc_from_ticks, build_trade_event_markers, delta_and_pct, last_and_prev_price
from .formatters import colored_money, format_seconds, label, safe_dt, utc_now
from .plotly_theme import PLOTLY_CONFIG, apply_dark_plotly_theme

EVENT_COLORS: dict[str, str] = {
    "entry_filled": THEME.success,
    "tp1_filled": THEME.blue,
    "tp2_filled": THEME.primary,
    "stop_filled": THEME.danger,
    "stop_moved": THEME.warn,
}


def render_status_rail(
    prices: pd.DataFrame,
    positions: pd.DataFrame,
    last_tick: Optional[pd.Timestamp],
    asset_focus: str,
) -> None:
    btc_last, btc_prev = last_and_prev_price(prices, "BTC-USD")
    eth_last, eth_prev = last_and_prev_price(prices, "ETH-USD")

    btc_d, btc_pct = delta_and_pct(btc_last, btc_prev)
    eth_d, eth_pct = delta_and_pct(eth_last, eth_prev)

    total_realized = float(positions["realized_pnl"].sum()) if not positions.empty else 0.0
    total_unreal = build_unrealized_pnl(positions, btc_last, eth_last)
    total_pnl = total_realized + total_unreal

    last_tick_dt = safe_dt(last_tick)
    age_s: Optional[float] = None
    if last_tick_dt is not None:
        age_s = max(0.0, (utc_now() - last_tick_dt).total_seconds())

    c1, c2, c3, c4, c5, c6 = st.columns([1.15, 1.15, 1, 1, 1, 1])

    btc_value = f"${btc_last:,.2f}" if btc_last is not None else "-"
    eth_value = f"${eth_last:,.2f}" if eth_last is not None else "-"

    btc_delta = "-" if btc_d is None or btc_pct is None else f"{btc_d:+,.2f} ({btc_pct:+.2f}%)"
    eth_delta = "-" if eth_d is None or eth_pct is None else f"{eth_d:+,.2f} ({eth_pct:+.2f}%)"

    c1.metric("btc", btc_value, delta=btc_delta, delta_color="normal")
    c2.metric("eth", eth_value, delta=eth_delta, delta_color="normal")

    with c3:
        st.markdown(label("realized", font_px=15), unsafe_allow_html=True)
        st.markdown(colored_money(total_realized, font_px=22), unsafe_allow_html=True)

    with c4:
        st.markdown(label("unrealized", font_px=15), unsafe_allow_html=True)
        st.markdown(colored_money(total_unreal, font_px=22), unsafe_allow_html=True)

    with c5:
        st.markdown(label("total pnl", font_px=15), unsafe_allow_html=True)
        st.markdown(colored_money(total_pnl, font_px=22), unsafe_allow_html=True)

    with c6:
        st.markdown(label("last tick age", font_px=15), unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:22px; font-weight:850; line-height:1.05'>{format_seconds(age_s)}</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<div style='margin-top:6px; font-size:15px; color:{THEME.text_muted}'>asset focus: <b>{asset_focus}</b></div>",
        unsafe_allow_html=True,
    )


def render_price_panel(
    prices: pd.DataFrame,
    events_for_overlay: pd.DataFrame,
    asset_focus: str,
    last_n_ticks: int,
    show_trade_overlay: bool,
    chart_type: str,
    candle_interval: str,
) -> None:
    st.subheader("price chart")

    if prices.empty:
        st.info("no price ticks yet. start the engine (or run the trader) first.")
        return

    df = prices.copy()
    if last_n_ticks > 0 and "ts" in df.columns:
        uniq = df[["ts"]].drop_duplicates().sort_values("ts")
        df = df.merge(uniq.tail(last_n_ticks), on="ts", how="inner")

    df = apply_asset_focus(df, asset_focus)

    if chart_type == "candlestick":
        if asset_focus == "all":
            st.info("candlestick view requires an asset focus (BTC-USD or ETH-USD).")
            return

        candles = build_ohlc_from_ticks(prices=df, product_id=asset_focus, interval=candle_interval)
        if candles.empty:
            st.info("not enough ticks to build candles yet.")
            return

        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=candles["ts"],
                    open=candles["open"],
                    high=candles["high"],
                    low=candles["low"],
                    close=candles["close"],
                    name=asset_focus,
                )
            ]
        )
        fig.update_layout(height=420, legend_title_text="")
    else:
        fig = plotly_express.line(df, x="ts", y="price", color="product_id")
        fig.update_layout(height=420, legend_title_text="")

    if show_trade_overlay and not events_for_overlay.empty:
        if "ts" in df.columns and not df.empty and df["ts"].notna().any():
            t_min = df["ts"].min()
            t_max = df["ts"].max()

            ev = events_for_overlay.copy()
            if "ts" in ev.columns:
                ev = ev.dropna(subset=["ts"])
                ev = ev[(ev["ts"] >= t_min) & (ev["ts"] <= t_max)]
        else:
            ev = events_for_overlay

        markers = build_trade_event_markers(
            prices=df,
            events=ev,
            asset_focus=asset_focus,
            max_markers=500,
        )
        if not markers.empty:
            for event_type in sorted(markers["event_type"].unique().tolist()):
                m = markers[markers["event_type"] == event_type]
                color = EVENT_COLORS.get(event_type, THEME.slate)
                fig.add_trace(
                    go.Scatter(
                        x=m["ts"],
                        y=m["y"],
                        mode="markers",
                        name=f"{event_type}",
                        hovertemplate="<b>%{text}</b><br>time=%{x}<br>y=%{y}<extra></extra>",
                        text=m.apply(lambda r: f"{r['product_id']} • {r['event_type']} • {r['message']}", axis=1),
                        marker=dict(size=11, symbol="circle", color=color, line=dict(width=0)),
                    )
                )

    apply_dark_plotly_theme(fig)
    st.plotly_chart(fig, config=PLOTLY_CONFIG)


def render_equity_panel(equity: pd.DataFrame) -> None:
    st.subheader("equity curve")

    if equity.empty:
        st.info("equity curve will appear after ticks are recorded.")
        return

    fig_eq = plotly_express.line(equity, x="ts", y="equity")
    fig_eq.update_layout(height=260, yaxis_title="pnl ($)")
    apply_dark_plotly_theme(fig_eq)
    st.plotly_chart(fig_eq, config=PLOTLY_CONFIG)


def render_positions_panel(prices: pd.DataFrame, positions: pd.DataFrame, table_density: str, asset_focus: str) -> None:
    st.subheader("positions (with pnl)")

    if positions.empty:
        st.info("no positions found")
        return

    pos = compute_asset_pnl_rows(prices, positions)
    pos = apply_asset_focus(pos, asset_focus)

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

    from .formatters import money_col, qty_col

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


def render_overview(
    prices: pd.DataFrame,
    positions: pd.DataFrame,
    events_filtered: pd.DataFrame,
    asset_focus: str,
    last_n_ticks: int,
    show_trade_overlay: bool,
    chart_type: str,
    candle_interval: str,
    table_density: str,
) -> None:
    equity = load_equity_curve(prices, positions)

    left, right = st.columns([2, 1], gap="large")
    with left:
        with st.container(border=True):
            render_price_panel(
                prices=prices,
                events_for_overlay=events_filtered,
                asset_focus=asset_focus,
                last_n_ticks=last_n_ticks,
                show_trade_overlay=show_trade_overlay,
                chart_type=chart_type,
                candle_interval=candle_interval,
            )
        with st.container(border=True):
            render_equity_panel(equity=equity)

    with right:
        with st.container(border=True):
            render_positions_panel(prices=prices, positions=positions, table_density=table_density, asset_focus=asset_focus)