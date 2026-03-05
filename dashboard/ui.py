from __future__ import annotations

import streamlit as st

from dashboard.constants import APP_TITLE
from dashboard.ui_parts.css import inject_global_css
from dashboard.ui_parts.fragments import build_fragments
from dashboard.ui_parts.render_reports import render_reports_tab
from dashboard.ui_parts.sidebar import build_sidebar_state, render_dev_tools


def run_app() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    inject_global_css()

    with st.container():
        st.title(APP_TITLE)
        st.caption("A dashboard to experiment with losing money while trading. Enjoy!")
    st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)

    state = build_sidebar_state()
    render_dev_tools(state.db_path)

    # Build (or retrieve cached) fragment callables. These are created once per
    # session and reused on every rerun so Streamlit sees stable function
    # identities — the key requirement for in-place fragment updates that don't
    # reset scroll position.
    frags = build_fragments(state.refresh_sec, state.auto_refresh)

    # Status rail always sits above the tabs
    frags.status(db_path=state.db_path, asset_focus=state.asset_focus)

    st.divider()

    tab_names = ["overview", "events", "history", "strategy", "reports", "diagnostics"]
    if state.show_orders:
        tab_names.insert(1, "orders")

    tabs = st.tabs(tab_names)

    idx = 0
    overview_tab = tabs[idx]; idx += 1

    orders_tab = None
    if state.show_orders:
        orders_tab = tabs[idx]; idx += 1

    events_tab   = tabs[idx]; idx += 1
    history_tab  = tabs[idx]; idx += 1
    strategy_tab = tabs[idx]; idx += 1
    reports_tab  = tabs[idx]; idx += 1
    diag_tab     = tabs[idx]

    with overview_tab:
        frags.overview(
            db_path=state.db_path,
            asset_focus=state.asset_focus,
            last_n_ticks=state.last_n_ticks,
            show_trade_overlay=state.show_trade_overlay,
            chart_type=state.chart_type,
            candle_interval=state.candle_interval,
            table_density=state.table_density,
            event_limit=state.event_limit,
            show_only_signal_events=state.show_only_signal_events,
            levels_selected=state.levels_selected,
            event_types_selected=state.event_types_selected,
            event_search=state.event_search,
        )

    if orders_tab is not None:
        with orders_tab:
            frags.orders(db_path=state.db_path, asset_focus=state.asset_focus)

    with events_tab:
        frags.events(
            db_path=state.db_path,
            asset_focus=state.asset_focus,
            event_limit=state.event_limit,
            show_only_signal_events=state.show_only_signal_events,
            levels_selected=state.levels_selected,
            event_types_selected=state.event_types_selected,
            event_search=state.event_search,
        )

    from dashboard.ui_parts.render_history import render_history_tab
    from dashboard.ui_parts.render_strategy import render_strategy_tab

    with history_tab:
        render_history_tab(state.history_csv_path)

    with strategy_tab:
        render_strategy_tab(state.strategy_config_path)

    with reports_tab:
        render_reports_tab(db_path=state.db_path, strategy_config_path=state.strategy_config_path)

    with diag_tab:
        frags.diagnostics(db_path=state.db_path)