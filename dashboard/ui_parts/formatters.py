from __future__ import annotations

import datetime as dt
from typing import Optional

import pandas as pd
import streamlit as st

from ..metrics import format_usd
from ..theme import THEME


def money_col(label: str) -> st.column_config.NumberColumn:
    return st.column_config.NumberColumn(label=label, format="$%.2f")


def qty_col(label: str) -> st.column_config.NumberColumn:
    return st.column_config.NumberColumn(label=label, format="%.8f")


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def safe_dt(ts: Optional[pd.Timestamp]) -> Optional[dt.datetime]:
    if ts is None or pd.isna(ts):
        return None
    if ts.tzinfo is None:
        return ts.to_pydatetime().replace(tzinfo=dt.timezone.utc)
    return ts.to_pydatetime()


def format_seconds(s: Optional[float]) -> str:
    if s is None:
        return "-"
    if s < 60:
        return f"{s:.0f}s"
    if s < 3600:
        return f"{s / 60:.1f}m"
    return f"{s / 3600:.2f}h"


def parse_iso_utc(value: Optional[str]) -> Optional[dt.datetime]:
    if not value:
        return None
    try:
        x = dt.datetime.fromisoformat(value)
        if x.tzinfo is None:
            return x.replace(tzinfo=dt.timezone.utc)
        return x.astimezone(dt.timezone.utc)
    except Exception:
        return None


def pnl_color(value: float) -> str:
    if value > 0:
        return THEME.success
    if value < 0:
        return THEME.danger
    return "rgba(255,255,255,0.55)"


def colored_money(value: float, font_px: int = 20) -> str:
    color = pnl_color(value)
    sign = "" if value < 0 else "+"
    return (
        f"<span style='color:{color}; font-weight:850; font-size:{font_px}px; line-height:1.05'>"
        f"{sign}{format_usd(value)}</span>"
    )


def label(text: str, font_px: int = 14) -> str:
    return (
        f"<div style='font-size:{font_px}px; font-weight:750; color:{THEME.text_muted}; margin-bottom:4px'>"
        f"{text}</div>"
    )
