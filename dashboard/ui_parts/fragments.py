from __future__ import annotations

from typing import Set

import datetime as dt
import streamlit as st

from ..db import load_events, load_orders, load_positions, load_price_ticks
from ..metrics import last_db_tick_ts
from .data import apply_asset_focus, apply_events_filters
from .render_overview import render_overview, render_status_rail
from .render_tables import render_events_panel, render_orders_panel


if not hasattr(st, "fragment"):
    raise RuntimeError(
        "st.fragment is not available. Please upgrade Streamlit: pip install 'streamlit>=1.35.0'"
    )


# ---------------------------------------------------------------------------
# Raw (un-decorated) fragment bodies — plain functions, no @st.fragment.
# We apply st.fragment exactly once in build_fragments() below, never here.
# Applying @st.fragment here AND wrapping again with run_every causes double-
# wrapping which triggers full page reruns and scroll resets.
# ---------------------------------------------------------------------------

def _status_body(db_path: str, asset_focus: str) -> None:
    prices = load_price_ticks(db_path)
    positions = load_positions(db_path)
    last_tick = last_db_tick_ts(prices)

    with st.container(border=True):
        if last_tick is None:
            st.warning("no ticks found in db yet")
        else:
            st.caption(f"last tick (utc): {last_tick}")
        render_status_rail(
            prices=prices,
            positions=positions,
            last_tick=last_tick,
            asset_focus=asset_focus,
        )


def _overview_body(
    db_path: str,
    asset_focus: str,
    last_n_ticks: int,
    show_trade_overlay: bool,
    chart_type: str,
    candle_interval: str,
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

    events_filtered = apply_events_filters(
        events=events,
        asset_focus=asset_focus,
        only_signals=show_only_signal_events,
        levels=levels_selected,
        event_types=event_types_selected,
        text_query=event_search,
    )

    render_overview(
        prices=prices,
        positions=positions,
        events_filtered=events_filtered,
        asset_focus=asset_focus,
        last_n_ticks=last_n_ticks,
        show_trade_overlay=show_trade_overlay,
        chart_type=chart_type,
        candle_interval=candle_interval,
        table_density=table_density,
    )


def _events_body(
    db_path: str,
    asset_focus: str,
    event_limit: int,
    show_only_signal_events: bool,
    levels_selected: Set[str],
    event_types_selected: Set[str],
    event_search: str,
) -> None:
    events = load_events(db_path, limit=event_limit)
    events_filtered = apply_events_filters(
        events=events,
        asset_focus=asset_focus,
        only_signals=show_only_signal_events,
        levels=levels_selected,
        event_types=event_types_selected,
        text_query=event_search,
    )
    with st.container(border=True):
        render_events_panel(events_filtered)


def _orders_body(db_path: str, asset_focus: str) -> None:
    orders = load_orders(db_path)
    orders = apply_asset_focus(orders, asset_focus)
    with st.container(border=True):
        render_orders_panel(orders)


def _diagnostics_body(db_path: str) -> None:
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


# ---------------------------------------------------------------------------
# Public API: build_fragments()
#
# Call this ONCE per session (cache in st.session_state) so that each body
# function is passed to st.fragment() exactly one time with a stable identity.
# Re-creating fragment-wrapped callables on every render confuses Streamlit's
# component diffing and causes full-page reruns.
# ---------------------------------------------------------------------------

class Fragments:
    """Holds the five live fragment callables, each wrapped exactly once."""

    def __init__(self, refresh_sec: int, enabled: bool):
        interval = dt.timedelta(seconds=refresh_sec) if (enabled and refresh_sec > 0) else None

        def _wrap(fn):
            return st.fragment(run_every=interval)(fn) if interval else fn

        self.status      = _wrap(_status_body)
        self.overview    = _wrap(_overview_body)
        self.events      = _wrap(_events_body)
        self.orders      = _wrap(_orders_body)
        self.diagnostics = _wrap(_diagnostics_body)


def build_fragments(refresh_sec: int, enabled: bool) -> Fragments:
    """
    Returns a Fragments instance cached in st.session_state so the fragment
    callables are created only once per session, not on every rerun.
    Recreates them only if the refresh settings actually change.
    """
    cache_key = "_fragments_cache"
    settings_key = "_fragments_settings"
    current_settings = (refresh_sec, enabled)

    if (
        cache_key not in st.session_state
        or st.session_state.get(settings_key) != current_settings
    ):
        st.session_state[cache_key] = Fragments(refresh_sec, enabled)
        st.session_state[settings_key] = current_settings

    return st.session_state[cache_key]