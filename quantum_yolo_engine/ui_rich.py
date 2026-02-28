# quantum_yolo_engine/ui_rich.py
from __future__ import annotations

from rich.console import Group
from rich.panel import Panel
from rich.table import Table

from .models import PRODUCT_IDS, PriceSnapshot
from .store import StateStore


def build_rich_dashboard(store: StateStore, prices: PriceSnapshot, tick_num: int) -> Panel:
    prices_table = Table(title=f"paper trader | tick {tick_num}", expand=True)
    prices_table.add_column("asset")
    prices_table.add_column("price", justify="right")
    for pid in PRODUCT_IDS:
        px = prices.get(pid)
        prices_table.add_row(pid, f"{px:,.2f}" if px is not None else "-")

    pos_table = Table(title="positions", expand=True)
    pos_table.add_column("asset")
    pos_table.add_column("state")
    pos_table.add_column("qty", justify="right")
    pos_table.add_column("avg", justify="right")
    pos_table.add_column("realized", justify="right")
    pos_table.add_column("unrealized", justify="right")

    for pid in PRODUCT_IDS:
        pos = store.get_position(pid)
        if not pos:
            continue
        px = prices.get(pid, 0.0)
        unreal = (px - pos.avg_entry) * pos.base_qty if pos.base_qty > 0 else 0.0

        realized_style = "green" if pos.realized_pnl >= 0 else "red"
        unreal_style = "green" if unreal >= 0 else "red"

        pos_table.add_row(
            pid,
            pos.state,
            f"{pos.base_qty:.8f}",
            f"{pos.avg_entry:.2f}",
            f"[{realized_style}]${pos.realized_pnl:.2f}[/{realized_style}]",
            f"[{unreal_style}]${unreal:.2f}[/{unreal_style}]",
        )

    cur = store.conn.cursor()
    rows = cur.execute(
        """
        select ts, product_id, event_type, message
        from events
        order by id desc
        limit 10
        """
    ).fetchall()

    events_table = Table(title="recent events", expand=True)
    events_table.add_column("time", width=8)
    events_table.add_column("asset", width=8)
    events_table.add_column("type", width=14)
    events_table.add_column("message")

    for row in reversed(rows):
        ts_str = str(row["ts"])
        events_table.add_row(
            ts_str[11:19] if len(ts_str) >= 19 else ts_str,
            row["product_id"] or "-",
            row["event_type"],
            row["message"],
        )

    group = Group(
        Panel(prices_table, border_style="cyan"),
        Panel(pos_table, border_style="green"),
        Panel(events_table, border_style="magenta"),
    )
    return Panel(group, title="live dashboard", border_style="white")


def print_recent_events(store: StateStore, limit: int = 12) -> None:
    cur = store.conn.cursor()
    rows = cur.execute(
        """
        select ts, level, product_id, event_type, message
        from events
        order by id desc
        limit ?
        """,
        (limit,),
    ).fetchall()

    print("\n=== recent events ===")
    for row in reversed(rows):
        ts_str = str(row["ts"])
        ts = ts_str[11:19] if len(ts_str) >= 19 else ts_str
        pid = row["product_id"] or "-"
        print(f"{ts} | {row['level']:<4} | {pid:<7} | {row['event_type']:<14} | {row['message']}")