# dashboard_dash/charts.py
"""
Plotly figure builders.
Pure data → figure.
"""

from __future__ import annotations

import re

import pandas as pd
import plotly.graph_objects as go

# ── palette (matches components.py exactly) ──────────────────────────────────

AMBER = "#e8a020"
GREEN = "#26a65b"
RED = "#e03e52"
BLUE = "#4a8fe8"
CYAN = "#18b8c4"

TEXT = "#b8c4cc"
MUTED = "#546270"
BG = "#0a0c10"
SURF = "#0f1318"
BORDER = "#1c2330"

COLORWAY = [AMBER, CYAN, GREEN, BLUE, RED, "#9d7fe8", "#e87c4a"]

PLOTLY_CONFIG = dict(
    displayModeBar="hover",
    scrollZoom=True,
    responsive=True,
    displaylogo=False,
    modeBarButtonsToRemove=["select2d", "lasso2d", "autoScale2d", "resetScale2d"],
)

_AXIS = dict(
    showgrid=True,
    gridcolor="rgba(255,255,255,0.04)",
    gridwidth=1,
    zeroline=False,
    tickfont=dict(color=MUTED, size=10, family="'IBM Plex Mono',monospace"),
    linecolor=BORDER,
    linewidth=1,
    showline=True,
)

BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor=BG,
    font=dict(color=TEXT, family="'IBM Plex Mono',monospace", size=11),
    legend=dict(
        bgcolor="rgba(15,19,24,0.9)",
        bordercolor=BORDER,
        borderwidth=1,
        font=dict(color=MUTED, size=10),
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
    ),
    margin=dict(l=56, r=12, t=8, b=44),
    hovermode="x unified",
    hoverlabel=dict(
        bgcolor="#151c24",
        bordercolor=BORDER,
        font=dict(color=TEXT, size=11, family="'IBM Plex Mono',monospace"),
        namelength=-1,
    ),
    colorway=COLORWAY,
    xaxis=_AXIS,
    yaxis=_AXIS,
)

EVENT_SYMBOLS = {
    "entry_filled": ("triangle-up", GREEN),
    "tp1_filled": ("diamond", BLUE),
    "tp2_filled": ("star", AMBER),
    "stop_filled": ("triangle-down", RED),
    "stop_moved": ("circle", CYAN),
}

RULE_MAP = {"1m": "1min", "5m": "5min", "15m": "15min", "1h": "1h", "4h": "4h", "1d": "1D"}


def _fig(h: int = 360) -> go.Figure:
    f = go.Figure()
    f.update_layout(height=h, **BASE)
    return f


def _empty(msg: str, h: int = 360) -> go.Figure:
    f = _fig(h)
    f.add_annotation(
        text=msg,
        showarrow=False,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        font=dict(color=MUTED, size=12, family="'IBM Plex Mono',monospace"),
    )
    return f


def _fill_price(msg: str | None) -> float | None:
    m = re.search(r"at\s+([0-9]+(?:\.[0-9]+)?)", msg or "")
    return float(m.group(1)) if m else None


def _nearest(px_df: pd.DataFrame, ts) -> float | None:
    if px_df.empty:
        return None
    i = px_df["ts"].searchsorted(ts, side="right") - 1
    if i < 0:
        return None
    v = px_df.iloc[int(i)]["price"]
    return float(v) if pd.notna(v) else None


def _get_fig_x_range(fig: go.Figure):
    xs = []
    for tr in getattr(fig, "data", []) or []:
        x = getattr(tr, "x", None)
        if x is None:
            continue
        for v in x:
            if v is not None:
                xs.append(v)
    if not xs:
        return None, None
    return min(xs), max(xs)


# ── public builders ─────────────────────────────────────────────────────────


def price_line_fig(prices: pd.DataFrame, asset_focus: str, last_n: int) -> go.Figure:
    if prices.empty:
        return _empty("No price ticks yet — start the engine.")

    df = prices.copy()

    if last_n > 0 and "ts" in df.columns:
        uniq = df[["ts"]].drop_duplicates().sort_values("ts")
        df = df.merge(uniq.tail(last_n), on="ts", how="inner")

    if asset_focus != "all":
        df = df[df["product_id"] == asset_focus]

    if df.empty:
        return _empty(f"No data for {asset_focus}")

    fig = _fig()

    for i, (pid, grp) in enumerate(df.groupby("product_id")):
        grp = grp.sort_values("ts")
        fig.add_trace(
            go.Scatter(
                x=grp["ts"],
                y=grp["price"],
                name=str(pid),
                mode="lines",
                line=dict(color=COLORWAY[i % len(COLORWAY)], width=1.5),
                hovertemplate=f"{pid} $%{{y:,.2f}}",
            )
        )

    fig.update_layout(yaxis_tickprefix="$", yaxis_tickformat=",.0f")
    return fig


def price_candle_fig(prices: pd.DataFrame, asset_focus: str, last_n: int, interval: str) -> go.Figure:
    if asset_focus == "all" or prices.empty:
        return _empty("Select a single asset for candlestick view.")

    df = prices[prices["product_id"] == asset_focus].copy()

    if last_n > 0:
        uniq = df[["ts"]].drop_duplicates().sort_values("ts")
        df = df.merge(uniq.tail(last_n), on="ts", how="inner")

    df = df.dropna(subset=["ts", "price"]).sort_values("ts").set_index("ts")

    rule = RULE_MAP.get(interval, "5min")
    ohlc = (
        df["price"]
        .resample(rule)
        .agg(["first", "max", "min", "last"])
        .dropna()
        .rename(columns={"first": "open", "max": "high", "min": "low", "last": "close"})
        .reset_index()
    )

    if ohlc.empty:
        return _empty("Not enough ticks to build candles.")

    fig = _fig()
    fig.add_trace(
        go.Candlestick(
            x=ohlc["ts"],
            open=ohlc["open"],
            high=ohlc["high"],
            low=ohlc["low"],
            close=ohlc["close"],
            name=asset_focus,
            increasing=dict(line=dict(color=GREEN, width=1), fillcolor=GREEN),
            decreasing=dict(line=dict(color=RED, width=1), fillcolor=RED),
            whiskerwidth=0.5,
        )
    )

    fig.update_layout(xaxis_rangeslider_visible=False, yaxis_tickprefix="$", yaxis_tickformat=",.0f")
    return fig


def add_trade_overlays(fig: go.Figure, prices: pd.DataFrame, events: pd.DataFrame, asset_focus: str) -> go.Figure:
    TYPES = {"entry_filled", "tp1_filled", "tp2_filled", "stop_filled", "stop_moved"}

    if events.empty or "event_type" not in events.columns:
        return fig

    ev = events[events["event_type"].isin(TYPES)].copy()

    if asset_focus != "all":
        ev = ev[ev["product_id"] == asset_focus]

    if ev.empty:
        return fig

    px_df = prices.copy()

    if asset_focus != "all":
        px_df = px_df[px_df["product_id"] == asset_focus]

    px_df = px_df.sort_values("ts")

    # key fix: constrain overlay computation to plotted x-range
    x_min, x_max = _get_fig_x_range(fig)
    if x_min is not None and x_max is not None:
        ev = ev[(ev["ts"] >= x_min) & (ev["ts"] <= x_max)]
        px_df = px_df[(px_df["ts"] >= x_min) & (px_df["ts"] <= x_max)]

    if ev.empty or px_df.empty:
        return fig

    rows = []

    for _, r in ev.iterrows():
        ts = r.get("ts")
        if pd.isna(ts):
            continue

        msg = str(r.get("message", ""))
        pid = str(r.get("product_id") or "")

        sub = px_df if asset_focus != "all" else px_df[px_df["product_id"] == pid]
        if sub.empty:
            continue

        y = _fill_price(msg) or _nearest(sub[["ts", "price"]], ts)
        if y is None:
            continue

        rows.append({"ts": ts, "pid": pid, "et": str(r.get("event_type", "")), "msg": msg, "y": float(y)})

    if not rows:
        return fig

    m = pd.DataFrame(rows)

    for et in sorted(m["et"].unique()):
        sym, color = EVENT_SYMBOLS.get(et, ("circle", MUTED))
        sub = m[m["et"] == et]

        fig.add_trace(
            go.Scatter(
                x=sub["ts"],
                y=sub["y"],
                mode="markers",
                name=et,
                hovertemplate="<b>%{text}</b><br>$%{y:,.2f}<extra></extra>",
                text=sub.apply(lambda r: f"{r['pid']} · {r['msg']}", axis=1),
                marker=dict(size=8, symbol=sym, color=color, line=dict(color=BG, width=1)),
            )
        )

    return fig


def equity_fig(equity: pd.DataFrame) -> go.Figure:
    if equity.empty:
        return _empty("Equity curve appears after ticks are recorded.", h=170)

    fig = _fig(h=170)
    vals = equity["equity"].astype(float)

    # colour based on final value
    color = GREEN if vals.iloc[-1] >= 0 else RED

    fig.add_trace(
        go.Scatter(
            x=equity["ts"],
            y=vals,
            mode="lines",
            name="PnL",
            line=dict(color=color, width=1.5),
            hovertemplate="$%{y:,.2f}",
        )
    )

    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="rgba(255,255,255,0.12)")
    fig.update_layout(
        yaxis_tickprefix="$",
        yaxis_tickformat=",.2f",
        showlegend=False,
        margin=dict(l=56, r=12, t=4, b=36),
    )
    return fig


def event_bar_fig(events: pd.DataFrame) -> go.Figure:
    if events.empty or "event_type" not in events.columns:
        return _empty("No events.", 220)

    vc = events["event_type"].value_counts().head(10).reset_index()
    vc.columns = ["event_type", "count"]

    fig = _fig(220)
    fig.add_trace(
        go.Bar(
            x=vc["event_type"],
            y=vc["count"],
            marker=dict(color=AMBER, line=dict(width=0)),
            hovertemplate="%{x}: %{y}",
        )
    )

    fig.update_layout(showlegend=False, bargap=0.35, margin=dict(l=40, r=8, t=4, b=60), xaxis_tickangle=-30)
    return fig


def trades_bar_fig(trades: pd.DataFrame) -> go.Figure:
    if trades.empty or "exit_type" not in trades.columns:
        return _empty("No trades.", 220)

    vc = trades["exit_type"].value_counts().reset_index()
    vc.columns = ["exit_type", "count"]
    colors = [GREEN if "tp" in str(e) else RED for e in vc["exit_type"]]

    fig = _fig(220)
    fig.add_trace(
        go.Bar(
            x=vc["exit_type"],
            y=vc["count"],
            marker=dict(color=colors, line=dict(width=0)),
            hovertemplate="%{x}: %{y}",
        )
    )

    fig.update_layout(showlegend=False, bargap=0.4, margin=dict(l=40, r=8, t=4, b=40))
    return fig


def equity_compare_fig(base_eq: pd.DataFrame, cand_eq: pd.DataFrame) -> go.Figure:
    if base_eq.empty or cand_eq.empty:
        return _empty("Select two reports to compare.")

    fig = _fig(320)

    for df, name, color in [(base_eq, "Baseline", AMBER), (cand_eq, "Candidate", CYAN)]:
        if "ts" in df.columns and "equity" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["ts"],
                    y=df["equity"].astype(float),
                    name=name,
                    mode="lines",
                    line=dict(color=color, width=1.5),
                    hovertemplate=f"{name} $%{{y:,.2f}}",
                )
            )

    fig.update_layout(yaxis_tickprefix="$", yaxis_tickformat=",.2f")
    return fig