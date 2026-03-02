from __future__ import annotations

import pandas as pd
import streamlit as st


def render_events_panel(events: pd.DataFrame) -> None:
    st.subheader("events")
    if events.empty:
        st.info("no events yet")
        return

    view = events.copy()
    if "ts" in view.columns and not view["ts"].empty:
        view["ts"] = view["ts"].dt.strftime("%Y-%m-%d %H:%M:%S")

    st.data_editor(view.head(500), width="stretch", hide_index=True, disabled=True, height=620)


def render_orders_panel(orders: pd.DataFrame) -> None:
    st.subheader("orders")
    if orders.empty:
        st.info("no orders found")
        return
    st.data_editor(orders, width="stretch", hide_index=True, disabled=True, height=620)
