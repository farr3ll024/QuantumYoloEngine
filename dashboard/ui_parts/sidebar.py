from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Set

import streamlit as st

from ..db import clear_all_data, load_events, load_orders, load_positions, load_price_ticks
from ..engine_control import get_status as get_engine_status
from ..engine_control import start_engine, stop_engine
from ..history_manager import load_history_summary
from .data import SIGNAL_EVENT_TYPES
from .formatters import format_seconds
from .paths import normalize_path

DEFAULT_DB_PATH = Path("runtime/db/paper_trader.db")
DEFAULT_HISTORY_CSV = Path("data/history.csv")
DEFAULT_STRATEGY_PATH = "strategy.yaml"


@dataclass(frozen=True)
class UiState:
    history_csv_path: str
    db_path: str
    strategy_config_path: str

    auto_refresh: bool
    refresh_sec: int

    event_limit: int
    asset_focus: str

    chart_type: str
    candle_interval: str
    last_n_ticks: int
    show_trade_overlay: bool

    show_only_signal_events: bool
    event_search: str
    levels_selected: Set[str]
    event_types_selected: Set[str]

    table_density: str
    show_orders: bool


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


def _estimate_csv_replay_runtime_seconds(history_csv_path: str, speed: float) -> float | None:
    if speed <= 0:
        return None

    summary = load_history_summary(history_csv_path)
    if not summary.exists or not summary.start_utc or not summary.end_utc:
        return None

    import datetime as dt

    try:
        start_dt = dt.datetime.fromisoformat(summary.start_utc)
        end_dt = dt.datetime.fromisoformat(summary.end_utc)
    except Exception:
        return None

    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=dt.timezone.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=dt.timezone.utc)

    sim_s = (end_dt - start_dt).total_seconds()
    if sim_s <= 0:
        return None

    return sim_s / float(speed)


def _render_engine_panel(*, history_csv_path: str, db_path: str) -> None:
    st.sidebar.subheader("engine")

    st.sidebar.caption(f"engine db: {db_path}")

    status = get_engine_status()
    if status.get("running"):
        st.sidebar.success(f"running (pid {status['pid']})")
        st.sidebar.caption(f"started: {status['started_at_utc']}")
        if st.sidebar.button("stop engine", type="primary", width="stretch"):
            res = stop_engine()
            if res.get("ok"):
                st.sidebar.success(res.get("message", "stopped"))
                st.rerun()
            else:
                st.sidebar.error(res.get("message", "failed to stop"))
    else:
        st.sidebar.warning("stopped")

        mode = st.sidebar.selectbox(
            "run mode",
            ["csv replay (rich)", "demo (rich)", "demo (console)"],
            index=0,
        )

        replay_speed = st.sidebar.select_slider(
            "replay speed",
            options=[1, 10, 60, 120, 300, 600, 1200, 3600, 7200, 14400],
            value=3600,
            format_func=lambda v: f"{v}x",
            disabled=(mode != "csv replay (rich)"),
            help="how many times faster than real time to replay history",
        )

        if mode == "csv replay (rich)":
            est_s = _estimate_csv_replay_runtime_seconds(history_csv_path, float(replay_speed))
            summary = load_history_summary(history_csv_path)

            if est_s is None:
                st.sidebar.caption("est. runtime: —")
            else:
                st.sidebar.markdown(
                    f"<div style='margin-top:-6px; margin-bottom:8px; "
                    f"padding:8px 10px; border-radius:12px; "
                    f"background:rgba(255,255,255,0.06); "
                    f"border:1px solid rgba(255,255,255,0.08)'>"
                    f"<div style='font-size:12px; font-weight:700; opacity:0.85'>est. runtime</div>"
                    f"<div style='font-size:18px; font-weight:900; line-height:1.15'>{format_seconds(est_s)}</div>"
                    f"<div style='font-size:12px; opacity:0.75; margin-top:2px'>"
                    f"{summary.unique_ticks:,} ticks • {len(summary.products)} assets"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        base = ["--db", str(db_path)]

        if mode == "demo (rich)":
            args = [*base, "--feed", "demo", "--ui", "rich"]
        elif mode == "demo (console)":
            args = [*base, "--feed", "demo", "--ui", "console"]
        else:
            args = [
                *base,
                "--feed",
                "csv",
                "--history-csv",
                history_csv_path,
                "--replay",
                "--speed",
                str(replay_speed),
                "--loop",
                "--ui",
                "rich",
            ]

        st.sidebar.code(" ".join(["python", "paper_trader.py", *args]), language="bash")

        if st.sidebar.button("start engine", type="primary", width="stretch"):
            res = start_engine(args)
            if res.get("ok"):
                st.sidebar.success(f"started (pid {res['pid']})")
                st.rerun()
            else:
                st.sidebar.error(res.get("message", "failed to start"))

    st.sidebar.divider()


def build_sidebar_state() -> UiState:
    if "history_csv_path" not in st.session_state:
        st.session_state.history_csv_path = str(DEFAULT_HISTORY_CSV)

    st.sidebar.subheader("history")
    history_csv_path = st.sidebar.text_input("history csv path", value=st.session_state.history_csv_path)
    history_csv_path = normalize_path(history_csv_path)
    st.session_state.history_csv_path = history_csv_path

    st.sidebar.subheader("controls")
    db_path = st.sidebar.text_input("sqlite db path", value=str(DEFAULT_DB_PATH))
    db_path = normalize_path(db_path)

    _render_engine_panel(history_csv_path=history_csv_path, db_path=db_path)

    strategy_config_path = st.sidebar.text_input(
        "strategy config path",
        value=DEFAULT_STRATEGY_PATH,
        help="path to the strategy YAML file",
    )

    auto_refresh = st.sidebar.checkbox("auto refresh", value=True)
    refresh_sec = st.sidebar.slider("refresh seconds", min_value=1, max_value=10, value=2)

    st.sidebar.divider()
    st.sidebar.subheader("data & focus")

    event_limit = st.sidebar.slider("events to load", min_value=50, max_value=5000, value=500, step=50)
    asset_focus = st.sidebar.selectbox("asset focus", options=["all", "BTC-USD", "ETH-USD"], index=0)

    chart_type = st.sidebar.selectbox(
        "chart type",
        options=["line", "candlestick"],
        index=0,
        help="candlestick aggregates tick prices into OHLC candles",
    )
    candle_interval = st.sidebar.selectbox(
        "candle interval",
        options=["1m", "5m", "15m", "1h", "4h", "1d"],
        index=1,
        disabled=(chart_type != "candlestick"),
    )

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

    return UiState(
        history_csv_path=history_csv_path,
        db_path=db_path,
        strategy_config_path=strategy_config_path,
        auto_refresh=auto_refresh,
        refresh_sec=int(refresh_sec),
        event_limit=int(event_limit),
        asset_focus=str(asset_focus),
        chart_type=str(chart_type),
        candle_interval=str(candle_interval),
        last_n_ticks=int(last_n_ticks),
        show_trade_overlay=bool(show_trade_overlay),
        show_only_signal_events=bool(show_only_signal_events),
        event_search=str(event_search or ""),
        levels_selected=levels_selected,
        event_types_selected=event_types_selected,
        table_density=str(table_density),
        show_orders=bool(show_orders),
    )