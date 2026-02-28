#!/usr/bin/env python3
"""
make_history_6mo.py (resilient hourly history + clear console output)

Generates history.csv for PaperTrader:
ts,product_id,price
2025-08-27T13:00:00Z,BTC-USD,....
2025-08-27T13:00:00Z,ETH-USD,....

Providers:
- coingecko (chunked range fetch; can be rate-limited)
- binance  (klines endpoint; may be blocked in some regions/networks)

Improvements in this version:
- verbose progress output (what it's doing + chunk/page counters)
- better diagnostics when an HTTP call fails (status + body head)
- supports Binance mirror base URL (default: data-api.binance.vision)
  (often works when api.binance.com is blocked)
"""

from __future__ import annotations

import argparse
import datetime as dt
import random
import time
from typing import List, Optional, Tuple

import pandas as pd
import requests


COINGECKO_COINS = {
    "BTC-USD": "bitcoin",
    "ETH-USD": "ethereum",
}

BINANCE_SYMBOLS = {
    "BTC-USD": "BTCUSDT",
    "ETH-USD": "ETHUSDT",
}


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _clamp_utc(ts: dt.datetime) -> dt.datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=dt.timezone.utc)
    return ts.astimezone(dt.timezone.utc)


def _to_unix(ts: dt.datetime) -> int:
    return int(_clamp_utc(ts).timestamp())


def _to_ms(ts: dt.datetime) -> int:
    return int(_clamp_utc(ts).timestamp() * 1000)


def _sleep_with_jitter(base: float) -> None:
    time.sleep(max(0.0, base + random.uniform(0.0, base * 0.25)))


def _format_dt(ts: dt.datetime) -> str:
    ts = _clamp_utc(ts)
    return ts.isoformat().replace("+00:00", "Z")


def _request_with_backoff(
    url: str,
    params: dict,
    timeout: int,
    max_retries: int,
    min_sleep: float,
    verbose: bool = True,
) -> Optional[object]:
    """
    Returns decoded json on success; returns None if ultimately failed.

    Retries on:
      - 429 (rate limit)
      - 5xx
      - connection/timeouts
      - JSON decode errors (often caused by HTML blocks / WAF / geo)
    """
    sleep_s = min_sleep
    last_error: Optional[str] = None

    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, params=params, timeout=timeout)

            # rate limited
            if r.status_code == 429:
                retry_after = r.headers.get("Retry-After")
                if verbose:
                    print(f"[warn] 429 rate limited (attempt {attempt}/{max_retries}) retry_after={retry_after}")
                if retry_after:
                    try:
                        _sleep_with_jitter(float(retry_after))
                    except ValueError:
                        _sleep_with_jitter(sleep_s)
                else:
                    _sleep_with_jitter(sleep_s)
                sleep_s = min(60.0, sleep_s * 1.8)
                continue

            # transient server errors
            if 500 <= r.status_code < 600:
                if verbose:
                    print(f"[warn] {r.status_code} server error (attempt {attempt}/{max_retries})")
                _sleep_with_jitter(sleep_s)
                sleep_s = min(60.0, sleep_s * 1.8)
                continue

            r.raise_for_status()

            try:
                return r.json()
            except Exception:
                body_head = (r.text or "")[:220].replace("\n", " ")
                last_error = (
                    f"json decode failed (status={r.status_code}, "
                    f"content_type={r.headers.get('content-type')}, body_head='{body_head}')"
                )
                if verbose:
                    print(f"[warn] {last_error} (attempt {attempt}/{max_retries})")
                _sleep_with_jitter(sleep_s)
                sleep_s = min(60.0, sleep_s * 1.8)
                continue

        except Exception as ex:
            status = getattr(getattr(ex, "response", None), "status_code", None)
            text = getattr(getattr(ex, "response", None), "text", "")
            body_head = (text or "")[:220].replace("\n", " ")
            last_error = f"{type(ex).__name__}: {ex} (status={status}) body_head='{body_head}'"
            if verbose:
                print(f"[warn] request failed (attempt {attempt}/{max_retries}): {last_error}")
            _sleep_with_jitter(sleep_s)
            sleep_s = min(60.0, sleep_s * 1.8)

    if verbose:
        print(f"[error] giving up after {max_retries} retries: {url}")
        if last_error:
            print(f"[error] last error: {last_error}")
        print(f"[error] params: {params}")
    return None


def downsample(df: pd.DataFrame, granularity: str) -> pd.DataFrame:
    """
    Normalize to:
      - hourly: last price each hour
      - daily: last price each day
    """
    if df.empty:
        return df

    if granularity == "hourly":
        return df.set_index("ts").resample("1h").last().dropna().reset_index()

    if granularity == "daily":
        return df.set_index("ts").resample("1d").last().dropna().reset_index()

    raise ValueError("granularity must be hourly or daily")


def fetch_binance_klines(
    symbol: str,
    start: dt.datetime,
    end: dt.datetime,
    interval: str,
    base_url: str,
    limit: int = 1000,
    timeout: int = 30,
    max_retries: int = 12,
    min_sleep: float = 0.5,
    verbose: bool = True,
) -> pd.DataFrame:
    url = f"{base_url.rstrip('/')}/api/v3/klines"

    start_ms = _to_ms(start)
    end_ms = _to_ms(end)

    rows: List[Tuple[pd.Timestamp, float]] = []
    cursor = start_ms
    page = 0

    if verbose:
        print(f"[info] binance fetch start | symbol={symbol} interval={interval} base_url={base_url}")
        print(f"[info] window: {_format_dt(start)} -> {_format_dt(end)}")

    while cursor < end_ms:
        page += 1
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": cursor,
            "endTime": end_ms,
            "limit": limit,
        }

        if verbose:
            cur_dt = pd.to_datetime(cursor, unit="ms", utc=True).to_pydatetime()
            print(f"[info] binance page {page} | from={_format_dt(cur_dt)} | rows_so_far={len(rows):,}")

        data = _request_with_backoff(
            url,
            params,
            timeout=timeout,
            max_retries=max_retries,
            min_sleep=min_sleep,
            verbose=verbose,
        )

        if data is None:
            raise RuntimeError(f"binance request failed for {symbol} params={params}")

        if not isinstance(data, list):
            raise RuntimeError(f"binance unexpected response type for {symbol}: {type(data).__name__}")

        if not data:
            break

        for k in data:
            open_time_ms = int(k[0])
            close_price = float(k[4])
            ts = pd.to_datetime(open_time_ms, unit="ms", utc=True)
            rows.append((ts, close_price))

        last_open = int(data[-1][0])
        next_cursor = last_open + 1

        if next_cursor <= cursor:
            if verbose:
                print("[warn] cursor did not advance; stopping to avoid infinite loop")
            break

        cursor = next_cursor
        _sleep_with_jitter(min_sleep)

        if len(data) < limit:
            break

    if not rows:
        return pd.DataFrame(columns=["ts", "price"])

    df = pd.DataFrame(rows, columns=["ts", "price"]).drop_duplicates(subset=["ts"]).sort_values("ts")
    if verbose:
        print(f"[info] binance fetch done | symbol={symbol} rows={len(df):,}")
    return df


def fetch_coingecko_range_chunked(
    coin_id: str,
    vs: str,
    start: dt.datetime,
    end: dt.datetime,
    chunk_days: int,
    timeout: int,
    max_retries: int,
    min_sleep: float,
    verbose: bool = True,
) -> pd.DataFrame:
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"

    start = _clamp_utc(start)
    end = _clamp_utc(end)

    frames: List[pd.DataFrame] = []
    cursor = start
    failures = 0
    chunk_num = 0

    if verbose:
        print(f"[info] coingecko fetch start | coin={coin_id} vs={vs} chunk_days={chunk_days}")
        print(f"[info] window: {_format_dt(start)} -> {_format_dt(end)}")

    while cursor < end:
        chunk_num += 1
        chunk_end = min(end, cursor + dt.timedelta(days=chunk_days))
        params = {"vs_currency": vs, "from": _to_unix(cursor), "to": _to_unix(chunk_end)}

        if verbose:
            print(f"[info] coingecko chunk {chunk_num} | {cursor.date()} -> {chunk_end.date()}")

        payload = _request_with_backoff(
            url,
            params,
            timeout=timeout,
            max_retries=max_retries,
            min_sleep=min_sleep,
            verbose=verbose,
        )

        if payload is None:
            failures += 1
            print(f"[warn] coingecko chunk failed (skipping): {coin_id} {cursor.isoformat()} -> {chunk_end.isoformat()}")
            cursor = chunk_end
            continue

        if not isinstance(payload, dict):
            failures += 1
            print(f"[warn] coingecko unexpected payload type (skipping): {type(payload).__name__}")
            cursor = chunk_end
            continue

        prices = payload.get("prices", [])
        if prices:
            df = pd.DataFrame(prices, columns=["ts_ms", "price"])
            df["ts"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
            df["price"] = df["price"].astype(float)
            frames.append(df[["ts", "price"]])

        _sleep_with_jitter(min_sleep)
        cursor = chunk_end

    if not frames:
        raise RuntimeError(f"coingecko returned no data for {coin_id} (failures={failures})")

    out = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["ts"]).sort_values("ts")
    if verbose:
        print(f"[info] coingecko fetch done | coin={coin_id} points={len(out):,} failures={failures}")
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=183, help="how many days back from now (approx 6 months)")
    p.add_argument("--granularity", choices=["hourly", "daily"], default="hourly")
    p.add_argument("--out", default="history.csv")

    p.add_argument("--provider", choices=["binance", "coingecko"], default="binance")

    p.add_argument(
        "--binance-base-url",
        default="https://data-api.binance.vision",
        help="binance base url (api.binance.com may be blocked; this mirror often works)",
    )

    p.add_argument("--vs", default="usd")
    p.add_argument("--chunk-days", type=int, default=30)

    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--max-retries", type=int, default=12)
    p.add_argument("--min-sleep", type=float, default=0.8)

    p.add_argument("--quiet", action="store_true", help="reduce console output")

    args = p.parse_args()
    verbose = not args.quiet

    end = _utc_now()
    start = end - dt.timedelta(days=args.days)

    if verbose:
        print("===============================================")
        print("[info] make_history_6mo starting")
        print(f"[info] provider={args.provider} granularity={args.granularity} days={args.days}")
        print(f"[info] out={args.out}")
        if args.provider == "binance":
            print(f"[info] binance_base_url={args.binance_base_url}")
        else:
            print(f"[info] coingecko vs={args.vs} chunk_days={args.chunk_days}")
        print(f"[info] window: {_format_dt(start)} -> {_format_dt(end)}")
        print("===============================================")

    frames: List[pd.DataFrame] = []

    if args.provider == "binance":
        interval = "1h" if args.granularity == "hourly" else "1d"

        for product_id, symbol in BINANCE_SYMBOLS.items():
            df = fetch_binance_klines(
                symbol=symbol,
                start=start,
                end=end,
                interval=interval,
                base_url=args.binance_base_url,
                timeout=args.timeout,
                max_retries=args.max_retries,
                min_sleep=args.min_sleep,
                verbose=verbose,
            )
            df = downsample(df, args.granularity)
            df["product_id"] = product_id
            frames.append(df)

    else:
        for product_id, coin_id in COINGECKO_COINS.items():
            df = fetch_coingecko_range_chunked(
                coin_id=coin_id,
                vs=args.vs,
                start=start,
                end=end,
                chunk_days=max(1, int(args.chunk_days)),
                timeout=args.timeout,
                max_retries=args.max_retries,
                min_sleep=args.min_sleep,
                verbose=verbose,
            )
            df = downsample(df, args.granularity)
            df["product_id"] = product_id
            frames.append(df)

    all_df = pd.concat(frames, ignore_index=True)
    if all_df.empty:
        raise RuntimeError("no data returned from provider")

    if verbose:
        print(f"[info] combining assets | raw_rows={len(all_df):,}")

    pivot = (
        all_df.pivot_table(index="ts", columns="product_id", values="price", aggfunc="last")
        .sort_index()
        .ffill()
        .dropna(how="all")
    )

    out_rows = pivot.reset_index().melt(id_vars=["ts"], var_name="product_id", value_name="price")
    out_rows["ts"] = out_rows["ts"].dt.tz_convert("UTC").dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out_rows = out_rows.sort_values(["ts", "product_id"])

    out_rows.to_csv(args.out, index=False, columns=["ts", "product_id", "price"])

    unique_ticks = out_rows["ts"].nunique()
    print(f"[ok] wrote {args.out} ({len(out_rows):,} rows, {unique_ticks:,} unique ticks) using provider={args.provider}")

    if unique_ticks > 1:
        ts_vals = pd.to_datetime(out_rows["ts"].drop_duplicates().sort_values(), utc=True)
        delta_s = (ts_vals.iloc[1] - ts_vals.iloc[0]).total_seconds()
        print(f"[ok] first tick delta: {delta_s:.0f}s (expected ~3600 for hourly, ~86400 for daily)")


if __name__ == "__main__":
    main()