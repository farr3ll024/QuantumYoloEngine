# QuantumYoloEngine

A tiny **paper-trading sandbox** for BTC/ETH with:

- a **paper trader** that simulates entry ladders + stop + take-profits and records everything to SQLite
- a **Rich (terminal) dashboard** for live-ish feedback
- a **Streamlit dashboard** for charts, positions, orders, and event logs
- a helper script to generate **historical CSV price data** for replays

It’s intentionally experimental and a bit unhinged. Use it to learn, not to fund your retirement.

---

## What’s in here

- `paper_trader.py` — main entrypoint (CLI)
- `dashboard_streamlit.py` — Streamlit UI entrypoint
- `quantum_yolo_engine/` — core engine (strategies, store, feeds, CLI, rich UI)
- `dashboard/` — Streamlit dashboard code
- `strategy.yaml` — strategy + risk config (bankroll, allocations, ladder entries, stop/TP)
- `runtime/db/paper_trader.db` — default runtime SQLite database location (created locally; typically ignored by git)
- `scripts/` — convenience scripts

---

## Quickstart

### 1) Setup a virtualenv + install deps
```
bash
./scripts/setup.sh
source .venv/bin/activate
```
### 2) Run the trader (demo feed)

This runs a short demo price feed and writes ticks/events/orders/positions to SQLite.
```
bash
source .venv/bin/activate
python paper_trader.py --feed demo --ui rich
```
You can switch the terminal UI:
```
bash
python paper_trader.py --feed demo --ui console
```
### 3) Run the dashboard (Streamlit)

In a second terminal (same repo):
```
bash
source .venv/bin/activate
python -m streamlit run dashboard_streamlit.py
```
By default, the dashboard reads from `runtime/db/paper_trader.db`.

- You can change the DB path in the dashboard sidebar.
- The dashboard will also create the parent directory for the DB path if it doesn’t exist yet (so fresh checkouts work nicely with the default `runtime/db/...` path).

---

## Replay with historical data (CSV feed)

### 1) Generate `history.csv` (hourly, ~6 months)
```
bash
source .venv/bin/activate
python make_history_6mo.py --provider binance --granularity hourly --out history.csv
```
If Binance is blocked on your network, try the default mirror (already used by the script) or switch provider:
```
bash
python make_history_6mo.py --provider coingecko --granularity hourly --out history.csv
```
### 2) Run the trader against the CSV
```
bash
source .venv/bin/activate
python paper_trader.py \
  --feed csv \
  --history-csv history.csv \
  --replay \
  --speed 600 \
  --loop \
  --ui rich
```
Notes:

- `--replay` sleeps between ticks based on timestamp deltas.
- `--speed 600` means “600× faster than real time”.
- `--loop` replays forever; omit it to stop after one pass.

---

## Configuration (`strategy.yaml`)

The strategy file defines:

- `bankroll_usd` — total simulated bankroll
- per-asset:
  - `enabled`
  - `allocation_usd` (validated against bankroll)
  - `entries`: a ladder of limit buys (`price`, `quote_size_usd`)
  - `stop_price`
  - `take_profit`:
    - `tp1_price`, `tp1_fraction`
    - `tp2_price`, `tp2_fraction`

The engine validates:

- total enabled allocations ≤ bankroll
- each asset’s sum of entry budgets ≤ that asset’s allocation

---

## Database

Trading state is written to a local SQLite DB (default: `runtime/db/paper_trader.db`) with tables:

- `price_ticks` — time series prices
- `orders` — entry/stop/tp orders (open/filled/canceled)
- `positions` — per-asset position state + realized pnl
- `events` — structured event log (optionally with JSON payload)

The Streamlit dashboard is designed to read from the same DB while the trader is writing (SQLite WAL mode).

---

## Useful CLI options
```
bash
python paper_trader.py --help
```
Common ones:

- `--config strategy.yaml` — strategy config path
- `--db runtime/db/paper_trader.db` — SQLite db path
- `--feed demo|csv` — market feed
- `--ui rich|console` — terminal display mode
- `--no-breakeven-stop` — don’t move stop to breakeven after TP1
- `--quiet` — reduce console noise

---

## Troubleshooting

- **Dashboard shows “no ticks yet”**: run the trader first, and ensure the dashboard DB path matches the trader `--db`.
- **CSV feed errors**: confirm your `history.csv` has columns `ts,product_id,price` and UTC timestamps.
- **Streamlit refresh feels janky**: try lowering refresh seconds in the sidebar or disable auto refresh.

---

## Disclaimer

This is a learning/paper-trading project. It does not connect to an exchange, and it is **not** financial advice. If you trade real money based on a repo named “QuantumYoloEngine”, that’s between you and your future self.

