from __future__ import annotations

from typing import Any, Callable, Optional, Set

import datetime as dt
import streamlit as st

from ..db import load_events, load_orders, load_positions, load_price_ticks
from ..metrics import last_db_tick_ts
from .data import apply_asset_focus, apply_events_filters
from .render_overview import render_overview, render_status_rail
from .render_tables import render_events_panel, render_orders_panel


HAS_FRAGMENTS = hasattr(st, "fragment")
if HAS_FRAGMENTS:
    fragment = st.fragment  # type: ignore[attr-defined]
else:

    def fragment(*_args: Any, **_kwargs: Any):  # type: ignore[no-redef]
        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            return fn

        return deco


def run_every(refresh_sec: int) -> Optional[dt.timedelta]:
    if refresh_sec <= 0:
        return None
    return dt.timedelta(seconds=int(refresh_sec))


def with_run_every(
    fn: Callable[..., Any],
    refresh_sec: int,
    *,
    enabled: bool,
    has_fragments: bool,
) -> Callable[..., Any]:
    if not enabled or not has_fragments:
        return fn
    base = getattr(fn, "__wrapped__", fn)
    return fragment(run_every=run_every(refresh_sec))(base)  # type: ignore[misc]


@fragment
def frag_status(db_path: str, asset_focus: str) -> None:
    prices = load_price_ticks(db_path)
    positions = load_positions(db_path)
    last_tick = last_db_tick_ts(prices)

    with st.container(border=True):
        if last_tick is None:
            st.warning("no ticks found in db yet")
        else:
            st.caption(f"last tick (utc): {last_tick}")
        render_status_rail(prices=prices, positions=positions, last_tick=last_tick, asset_focus=asset_focus)


@fragment
def frag_overview(
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


@fragment
def frag_events(
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


@fragment
def frag_orders(db_path: str, asset_focus: str) -> None:
    orders = load_orders(db_path)
    orders = apply_asset_focus(orders, asset_focus)
    with st.container(border=True):
        render_orders_panel(orders)


@fragment
def frag_diagnostics(db_path: str) -> None:
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