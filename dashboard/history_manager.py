# dashboard/history_manager.py
from __future__ import annotations

import datetime as dt
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class HistorySummary:
    path: str
    exists: bool
    size_bytes: int
    modified_utc: Optional[str]
    rows: int
    unique_ticks: int
    products: list[str]
    start_utc: Optional[str]
    end_utc: Optional[str]


def _safe_iso(ts: Optional[pd.Timestamp]) -> Optional[str]:
    if ts is None or pd.isna(ts):
        return None
    if ts.tzinfo is None:
        # interpret as utc if naive
        return ts.to_pydatetime().replace(tzinfo=dt.timezone.utc).isoformat()
    return ts.to_pydatetime().astimezone(dt.timezone.utc).isoformat()


def load_history_summary(csv_path: str) -> HistorySummary:
    p = Path(csv_path).expanduser()
    if not p.exists():
        return HistorySummary(
            path=str(p),
            exists=False,
            size_bytes=0,
            modified_utc=None,
            rows=0,
            unique_ticks=0,
            products=[],
            start_utc=None,
            end_utc=None,
        )

    stat = p.stat()
    modified = dt.datetime.fromtimestamp(stat.st_mtime, tz=dt.timezone.utc).isoformat()

    # read minimal columns (file is usually smallish; this stays fast)
    df = pd.read_csv(p, usecols=["ts", "product_id", "price"])
    if df.empty:
        return HistorySummary(
            path=str(p),
            exists=True,
            size_bytes=int(stat.st_size),
            modified_utc=modified,
            rows=0,
            unique_ticks=0,
            products=[],
            start_utc=None,
            end_utc=None,
        )

    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")

    rows = int(len(df))
    unique_ticks = int(df["ts"].dropna().nunique())
    products = sorted([str(x) for x in df["product_id"].dropna().unique().tolist()])

    start_ts = df["ts"].min()
    end_ts = df["ts"].max()

    return HistorySummary(
        path=str(p),
        exists=True,
        size_bytes=int(stat.st_size),
        modified_utc=modified,
        rows=rows,
        unique_ticks=unique_ticks,
        products=products,
        start_utc=_safe_iso(start_ts),
        end_utc=_safe_iso(end_ts),
    )


def load_history_preview(csv_path: str, n: int = 10) -> tuple[pd.DataFrame, pd.DataFrame]:
    p = Path(csv_path).expanduser()
    if not p.exists():
        return pd.DataFrame(), pd.DataFrame()

    df = pd.read_csv(p, usecols=["ts", "product_id", "price"])
    if df.empty:
        return df, df

    # keep as strings; preview only
    head = df.head(n)
    tail = df.tail(n)
    return head, tail


def regenerate_history(
        *,
        days: int,
        granularity: str,
        provider: str,
        out_path: str,
        binance_base_url: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Runs: python build_history.py --days N --granularity hourly|daily --provider binance|coingecko --out <out_path>
    Returns (ok, combined_output).
    """
    cmd = [
        "python",
        "build_history.py",
        "--days",
        str(int(days)),
        "--granularity",
        granularity,
        "--provider",
        provider,
        "--out",
        out_path,
    ]

    if provider == "binance" and binance_base_url:
        cmd += ["--binance-base-url", binance_base_url]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        ok = proc.returncode == 0
        return ok, out
    except Exception as ex:
        return False, f"failed to run generator: {ex}"
