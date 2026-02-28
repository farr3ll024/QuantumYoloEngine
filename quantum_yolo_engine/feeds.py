# quantum_yolo_engine/feeds.py
from __future__ import annotations

import random
from typing import Dict, Iterator, List, Tuple

import pandas as pd

from .models import PriceSnapshot


class DemoMarketFeed:
    def __init__(self, seed: int = 7):
        self.random = random.Random(seed)
        self.prices = {"BTC-USD": 64200.0, "ETH-USD": 1856.0}
        self.step_count = 0

    def next_prices(self) -> PriceSnapshot:
        self.step_count += 1
        out: Dict[str, float] = {}

        for product_id, current in self.prices.items():
            if self.step_count < 20:
                drift = -0.004
            elif self.step_count < 45:
                drift = 0.006
            else:
                drift = self.random.uniform(-0.003, 0.003)

            noise = self.random.uniform(-0.004, 0.004)
            next_px = current * (1 + drift + noise)

            if product_id == "BTC-USD":
                next_px = max(45000.0, min(95000.0, next_px))
            if product_id == "ETH-USD":
                next_px = max(1200.0, min(4500.0, next_px))

            self.prices[product_id] = next_px
            out[product_id] = round(next_px, 2)

        return out


class CsvMarketFeed:
    """
    replays timestamped price data from a CSV of rows:
      ts, product_id, price

    yields (ts_datetime, {product_id: price, ...}) per unique timestamp.
    missing assets are forward-filled using last-known prices.
    """

    def __init__(self, csv_path: str):
        df = pd.read_csv(csv_path)

        if df.empty:
            raise ValueError(f"history csv is empty: {csv_path}")

        if not {"ts", "product_id", "price"}.issubset(set(df.columns)):
            raise ValueError("history csv must include columns: ts, product_id, price")

        df["ts"] = pd.to_datetime(df["ts"], utc=True)
        df["product_id"] = df["product_id"].astype(str)
        df["price"] = df["price"].astype(float)
        df = df.sort_values("ts")

        self._groups: List[Tuple[pd.Timestamp, pd.DataFrame]] = list(df.groupby("ts"))
        self._last: Dict[str, float] = {}

    def __iter__(self) -> Iterator[Tuple["dt.datetime", PriceSnapshot]]:
        import datetime as dt

        for ts, g in self._groups:
            for _, row in g.iterrows():
                self._last[str(row["product_id"])] = float(row["price"])
            yield ts.to_pydatetime(), dict(self._last)