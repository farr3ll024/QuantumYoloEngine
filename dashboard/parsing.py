# dashboard/parsing.py
from __future__ import annotations

import pandas as pd


def parse_ts_series(ts_series: pd.Series) -> pd.Series:
    """
    robust parsing for mixed ISO8601 timestamp strings:
      - supports ...Z
      - supports ...+00:00
      - supports optional fractional seconds (microseconds)

    uses format="mixed" when available; falls back to generic parsing if not.
    """
    try:
        return pd.to_datetime(ts_series, utc=True, format="mixed", errors="coerce")
    except TypeError:
        return pd.to_datetime(ts_series, utc=True, errors="coerce")