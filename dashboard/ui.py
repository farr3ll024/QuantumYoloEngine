from __future__ import annotations

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from .constants import APP_TITLE
from .ui_parts.css import inject_global_css
from .ui_parts.fragments import with_run_every
from .ui_parts.fragments import frag_diagnostics, frag_events, frag_orders, frag_overview, frag_status
from .ui_parts.render_reports import render_reports_tab
from .ui_parts.sidebar import build_sidebar_state, render_dev_tools


def run_app() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    inject_global_css()

    with st.container():
        st.title(APP_TITLE)
        st.caption("A dashboard to experiment with losing money while trading. Enjoy!")
    st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)

    state = build_sidebar_state()

    render_dev_tools(state.db_path)

    if state.auto_refresh and not state.has_fragments:
        st_autorefresh(interval=state.refresh_sec * 1000, key="paper_trader_refresh")

    status_live = with_run_every(frag_status, state.refresh_sec, enabled=state.auto_refresh,
                                 has_fragments=state.has_fragments)
    overview_live = with_run_every(
        frag_overview, state.refresh_sec, enabled=state.auto_refresh, has_fragments=state.has_fragments
    )
    events_live = with_run_every(frag_events, state.refresh_sec, enabled=state.auto_refresh,
                                 has_fragments=state.has_fragments)
    orders_live = with_run_every(frag_orders, state.refresh_sec, enabled=state.auto_refresh,
                                 has_fragments=state.has_fragments)
    diagnostics_live = with_run_every(
        frag_diagnostics, state.refresh_sec, enabled=state.auto_refresh, has_fragments=state.has_fragments
    )

    status_live(db_path=state.db_path, asset_focus=state.asset_focus)

    st.divider()

    tab_names = ["overview", "events", "history", "strategy", "reports", "diagnostics"]
    if state.show_orders:
        tab_names.insert(1, "orders")

    tabs = st.tabs(tab_names)

    idx = 0
    overview_tab = tabs[idx]
    idx += 1

    orders_tab = None
    if state.show_orders:
        orders_tab = tabs[idx]
        idx += 1

    events_tab = tabs[idx]
    idx += 1

    history_tab = tabs[idx]
    idx += 1

    strategy_tab = tabs[idx]
    idx += 1

    reports_tab = tabs[idx]
    idx += 1

    diag_tab = tabs[idx]

    with overview_tab:
        overview_live(
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
            orders_live(db_path=state.db_path, asset_focus=state.asset_focus)

    with events_tab:
        events_live(
            db_path=state.db_path,
            asset_focus=state.asset_focus,
            event_limit=state.event_limit,
            show_only_signal_events=state.show_only_signal_events,
            levels_selected=state.levels_selected,
            event_types_selected=state.event_types_selected,
            event_search=state.event_search,
        )

    from .ui_parts.render_history import render_history_tab
    from .ui_parts.render_strategy import render_strategy_tab

    with history_tab:
        render_history_tab(state.history_csv_path)

    with strategy_tab:
        render_strategy_tab(state.strategy_config_path)

    with reports_tab:
        render_reports_tab(db_path=state.db_path, strategy_config_path=state.strategy_config_path)

    with diag_tab:
        diagnostics_live(db_path=state.db_path)
