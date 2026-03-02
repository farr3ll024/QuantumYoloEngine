from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st
import yaml

from ..strategy_manager import DEFAULT_STRATEGY_PATH, load_strategy_yaml, save_strategy_yaml, validate_strategy_dict
from ..theme import THEME


def _render_strategy_asset_summary(product_id: str, asset: Dict[str, Any]) -> None:
    enabled = asset.get("enabled", True)
    status_color = THEME.success if enabled else THEME.text_muted
    status_label = "enabled" if enabled else "disabled"

    st.markdown(
        f"<div style='display:flex; align-items:center; gap:10px; margin-bottom:6px'>"
        f"<span style='font-size:18px; font-weight:800; color:{THEME.primary}'>{product_id}</span>"
        f"<span style='font-size:12px; font-weight:700; color:{status_color}; "
        f"background:rgba(255,255,255,0.07); border-radius:6px; padding:2px 8px'>{status_label}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    tp = asset.get("take_profit", {})
    entries = asset.get("entries", [])

    col1, col2, col3 = st.columns(3)
    col1.metric("allocation", f"${float(asset.get('allocation_usd', 0)):,.2f}")
    col2.metric("stop price", f"${float(asset.get('stop_price', 0)):,.2f}")
    col3.metric("entries", str(len(entries)))

    col4, col5, col6 = st.columns(3)
    col4.metric(
        "tp1 price",
        f"${float(tp.get('tp1_price', 0)):,.2f}",
        help=f"sell {float(tp.get('tp1_fraction', 0)) * 100:.0f}% of position",
    )
    col5.metric(
        "tp2 price",
        f"${float(tp.get('tp2_price', 0)):,.2f}",
        help=f"sell {float(tp.get('tp2_fraction', 0)) * 100:.0f}% of position",
    )
    col6.metric("total entry budget", f"${sum(float(e.get('quote_size_usd', 0)) for e in entries):,.2f}")

    if entries:
        entry_df = pd.DataFrame(entries)[["id", "price", "quote_size_usd"]]
        entry_df.columns = ["id", "entry price", "size (usd)"]
        st.dataframe(entry_df, hide_index=True, width="stretch")


def render_strategy_tab(strategy_config_path: str) -> None:
    st.subheader("current strategy")

    ok, data, err = load_strategy_yaml(strategy_config_path)

    if not ok or data is None:
        st.error(f"could not load strategy: {err}")
        st.info(f"expected path: `{strategy_config_path}`")
    else:
        bankroll = float(data.get("bankroll_usd", 0))
        assets = data.get("assets", {})
        enabled_assets = [pid for pid, a in assets.items() if a.get("enabled", True)]
        total_alloc = sum(float(a.get("allocation_usd", 0)) for a in assets.values() if a.get("enabled", True))

        m1, m2, m3 = st.columns(3)
        m1.metric("bankroll", f"${bankroll:,.2f}")
        m2.metric("enabled assets", str(len(enabled_assets)))
        m3.metric("total allocated", f"${total_alloc:,.2f}", delta=f"${bankroll - total_alloc:,.2f} unallocated")

        st.divider()

        for product_id, asset in assets.items():
            with st.container(border=True):
                _render_strategy_asset_summary(product_id, asset)

        with st.expander("view raw YAML", expanded=False):
            raw_text = yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
            st.code(raw_text, language="yaml")

    st.divider()
    st.subheader("edit / create strategy")
    st.caption(
        "paste a full strategy YAML below and save it to disk. the engine must be restarted for changes to take effect.")

    if ok and data is not None:
        default_yaml = yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    else:
        default_yaml = """bankroll_usd: 500.0
quote_currency: USD

assets:
  BTC-USD:
    enabled: true
    allocation_usd: 325.0
    stop_price: 101500.0
    take_profit:
      tp1_price: 116000.0
      tp1_fraction: 0.50
      tp2_price: 119500.0
      tp2_fraction: 0.50
    entries:
      - id: btc_e1
        price: 112500.0
        quote_size_usd: 75.0

  ETH-USD:
    enabled: true
    allocation_usd: 175.0
    stop_price: 4050.0
    take_profit:
      tp1_price: 4640.0
      tp1_fraction: 0.50
      tp2_price: 4775.0
      tp2_fraction: 0.50
    entries:
      - id: eth_e1
        price: 4500.0
        quote_size_usd: 40.0
"""

    new_yaml = st.text_area(
        "strategy YAML",
        value=default_yaml,
        height=480,
        key="strategy_editor",
        label_visibility="collapsed",
    )

    save_path = st.text_input(
        "save to path",
        value=str(strategy_config_path or DEFAULT_STRATEGY_PATH),
        help="you can save to a new file to create an alternate strategy without overwriting the current one",
    )

    col_save, col_validate = st.columns([1, 1])

    with col_validate:
        if st.button("validate only", width="stretch"):
            try:
                parsed = yaml.safe_load(new_yaml)
                v_ok, v_err = validate_strategy_dict(parsed)
                if v_ok:
                    st.success("validation passed ✅")
                else:
                    st.error(f"validation failed: {v_err}")
            except yaml.YAMLError as ex:
                st.error(f"YAML parse error: {ex}")

    with col_save:
        if st.button("save strategy", type="primary", width="stretch"):
            try:
                parsed = yaml.safe_load(new_yaml)
            except yaml.YAMLError as ex:
                st.error(f"YAML parse error: {ex}")
                return

            v_ok, v_err = validate_strategy_dict(parsed)
            if not v_ok:
                st.error(f"validation failed: {v_err}")
                return

            s_ok, s_err = save_strategy_yaml(save_path, parsed)
            if s_ok:
                st.success(f"saved to `{save_path}` ✅  —  restart the engine to apply changes.")
                st.rerun()
            else:
                st.error(f"save failed: {s_err}")
