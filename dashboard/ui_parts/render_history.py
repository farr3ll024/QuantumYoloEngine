from __future__ import annotations

from pathlib import Path

import streamlit as st

from ..history_manager import load_history_preview, load_history_summary, regenerate_history


def render_history_tab(history_csv_path: str) -> None:
    st.subheader("history file")

    summary = load_history_summary(history_csv_path)
    if not summary.exists:
        st.warning(f"history file not found: {history_csv_path}")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("rows", f"{summary.rows:,}")
        c2.metric("unique ticks", f"{summary.unique_ticks:,}")
        c3.metric("products", str(len(summary.products)))
        c4.metric("size (mb)", f"{summary.size_bytes / 1024 / 1024:.2f}")

        st.write(
            {
                "path": summary.path,
                "modified_utc": summary.modified_utc,
                "range_utc": f"{summary.start_utc} → {summary.end_utc}",
                "products": summary.products,
            }
        )

        head, tail = load_history_preview(history_csv_path, n=10)
        left, right = st.columns(2)
        with left:
            st.caption("head")
            st.dataframe(head, width="stretch", height=320)
        with right:
            st.caption("tail")
            st.dataframe(tail, width="stretch", height=320)

    st.divider()
    st.subheader("regenerate history")

    with st.form("regen_history_form", clear_on_submit=False):
        days = st.slider("days back", min_value=3, max_value=730, value=183, step=1)
        granularity = st.selectbox("granularity", ["hourly", "daily"], index=0)
        provider = st.selectbox("provider", ["binance", "coingecko"], index=0)

        out_path = st.text_input("output path", value=history_csv_path)
        out_path = str(Path(out_path).expanduser())

        binance_base_url = st.text_input(
            "binance base url (optional)",
            value="https://data-api.binance.vision",
            help="only used if provider=binance",
        )

        submitted = st.form_submit_button("generate", type="primary")

    if submitted:
        with st.spinner("generating history…"):
            ok, output = regenerate_history(
                days=days,
                granularity=granularity,
                provider=provider,
                out_path=out_path,
                binance_base_url=binance_base_url if provider == "binance" else None,
            )

        if ok:
            st.success("generated ✅")
            st.session_state.history_csv_path = out_path
            st.code(output[-6000:] if len(output) > 6000 else output)
            st.rerun()
        else:
            st.error("generation failed")
            st.code(output[-8000:] if len(output) > 8000 else output)