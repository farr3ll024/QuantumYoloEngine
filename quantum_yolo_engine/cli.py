# quantum_yolo_engine/cli.py
from __future__ import annotations

import argparse
import datetime as dt
import logging
import time
from logging.handlers import RotatingFileHandler
from typing import Optional

from rich.console import Console
from rich.live import Live

from .engine import PaperTrader
from .feeds import CsvMarketFeed, DemoMarketFeed
from .risk import RiskManager
from .store import StateStore
from .strategy import load_strategy_config
from .ui_rich import build_rich_dashboard, print_recent_events


def setup_logger(log_level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("paper_trader")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    file_handler = RotatingFileHandler("paper_trader.log", maxBytes=1_000_000, backupCount=3)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


def compute_replay_sleep(prev_ts: Optional[dt.datetime], ts: dt.datetime, speed: float) -> float:
    if prev_ts is None:
        return 0.0
    delta = (ts - prev_ts).total_seconds()
    return max(0.0, delta / max(1e-9, speed))


def main() -> None:
    parser = argparse.ArgumentParser(description="QuantumYoloEngine paper trader")
    parser.add_argument("--config", default="strategy.yaml", help="path to strategy yaml")
    parser.add_argument("--db", default="paper_trader.db", help="sqlite db path")

    # demo-only settings
    parser.add_argument("--ticks", type=int, default=70, help="number of demo ticks to run")
    parser.add_argument("--sleep", type=float, default=0.25, help="seconds between ticks (demo feed only)")
    parser.add_argument("--seed", type=int, default=7, help="random seed for demo feed")

    # feed selection
    parser.add_argument("--feed", choices=["demo", "csv"], default="demo", help="market feed type")
    parser.add_argument("--history-csv", default="history.csv", help="path to history csv when feed=csv")
    parser.add_argument("--replay", action="store_true", help="sleep between historical ticks (csv feed)")
    parser.add_argument("--speed", type=float, default=60.0, help="replay speed: 60 means 60x faster than real time (csv feed)")

    # csv looping
    parser.add_argument("--loop", action="store_true", help="loop the csv feed forever")
    parser.add_argument("--loop-gap", type=float, default=0.0, help="seconds to pause between csv loops")

    parser.add_argument("--no-breakeven-stop", action="store_true", help="do not move stop to breakeven after tp1")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--summary-every", type=int, default=10, help="console summary interval in console ui mode")
    parser.add_argument("--ui", choices=["console", "rich"], default="rich", help="display mode")
    parser.add_argument("--quiet", action="store_true", help="minimal console logging")
    args = parser.parse_args()

    logger = setup_logger(args.log_level)

    bankroll, strategies = load_strategy_config(args.config)
    risk = RiskManager(bankroll_usd=bankroll)
    risk.validate_strategy_allocations(strategies)
    for strat in strategies.values():
        if strat.enabled:
            risk.validate_entry_budget(strat)

    store = StateStore(args.db)
    trader = PaperTrader(
        store=store,
        strategies=strategies,
        logger=logger,
        move_stop_to_breakeven_after_tp1=not args.no_breakeven_stop,
    )
    trader.bootstrap()

    console = Console()

    logger.info("starting QuantumYoloEngine paper trader")
    logger.info("db=%s | feed=%s | ui=%s", args.db, args.feed, args.ui)

    try:
        if args.feed == "csv":
            tick_num = 0

            def new_csv_iter():
                return iter(CsvMarketFeed(args.history_csv))

            if args.ui == "rich":
                with Live(
                    build_rich_dashboard(store, {"BTC-USD": 0.0, "ETH-USD": 0.0}, 0),
                    refresh_per_second=8,
                    console=console,
                ) as live:
                    while True:
                        prev_ts: Optional[dt.datetime] = None
                        for ts, prices in new_csv_iter():
                            if args.replay:
                                sleep_s = compute_replay_sleep(prev_ts, ts, args.speed)
                                if sleep_s > 0:
                                    time.sleep(sleep_s)

                            tick_num += 1
                            trader.on_price_tick(ts, prices)
                            live.update(build_rich_dashboard(store, prices, tick_num))
                            prev_ts = ts

                        if not args.loop:
                            break
                        if args.loop_gap > 0:
                            time.sleep(args.loop_gap)
            else:
                while True:
                    prev_ts = None
                    for ts, prices in new_csv_iter():
                        if args.replay:
                            sleep_s = compute_replay_sleep(prev_ts, ts, args.speed)
                            if sleep_s > 0:
                                time.sleep(sleep_s)

                        tick_num += 1
                        trader.on_price_tick(ts, prices)

                        if not args.quiet and (tick_num % max(1, args.summary_every) == 0):
                            logger.info(
                                "tick=%s | BTC=%s | ETH=%s",
                                tick_num,
                                f"{prices.get('BTC-USD', 0):,.2f}",
                                f"{prices.get('ETH-USD', 0):,.2f}",
                            )

                        prev_ts = ts

                    if not args.loop:
                        break
                    if args.loop_gap > 0:
                        time.sleep(args.loop_gap)

        else:
            demo_feed = DemoMarketFeed(seed=args.seed)
            now = dt.datetime.now(dt.timezone.utc)

            if args.ui == "rich":
                with Live(
                    build_rich_dashboard(store, {"BTC-USD": 0.0, "ETH-USD": 0.0}, 0),
                    refresh_per_second=8,
                    console=console,
                ) as live:
                    for i in range(args.ticks):
                        prices = demo_feed.next_prices()
                        ts = now + dt.timedelta(seconds=i)
                        trader.on_price_tick(ts, prices)
                        live.update(build_rich_dashboard(store, prices, i + 1))
                        time.sleep(args.sleep)
            else:
                for i in range(args.ticks):
                    prices = demo_feed.next_prices()
                    ts = now + dt.timedelta(seconds=i)
                    trader.on_price_tick(ts, prices)

                    if not args.quiet and (i % max(1, args.summary_every) == 0):
                        logger.info(
                            "tick=%s | BTC=%s | ETH=%s",
                            i + 1,
                            f"{prices.get('BTC-USD', 0):,.2f}",
                            f"{prices.get('ETH-USD', 0):,.2f}",
                        )

                    time.sleep(args.sleep)

    except KeyboardInterrupt:
        logger.warning("stopped by user")

    print_recent_events(store, limit=20)
    store.print_summary()

    cur = store.conn.cursor()
    total_realized = cur.execute("select coalesce(sum(realized_pnl), 0) as v from positions").fetchone()["v"]
    print(f"\ncombined realized pnl: ${float(total_realized):.2f}")
    logger.info("combined realized pnl: $%.2f", float(total_realized))