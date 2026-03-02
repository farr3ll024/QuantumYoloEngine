# QuantumYoloEngine

A tiny **paper-trading sandbox** for BTC/ETH with:

- a **paper trader** that simulates entry ladders + stop + take-profits and records everything to SQLite
- a **Rich (terminal) dashboard** for live-ish feedback
- a **Streamlit dashboard** for charts, positions, orders, events, and equity
- helper scripts to generate **historical CSV price data** for replays

It’s intentionally experimental and a bit unhinged. Use it to learn, not to fund your retirement.

---

## What’s in here

- `paper_trader.py` — main entrypoint (CLI)
- `dashboard_streamlit.py` — Streamlit UI entrypoint
- `quantum_yolo_engine/` — core engine (strategies, store, feeds, CLI, rich UI)
- `dashboard/` — Streamlit dashboard code (db readers, charts, history helpers, strategy manager)
- `strategy.yaml` — strategy + risk config (bankroll, allocations, ladder entries, stop/TP)
- `runtime/db/paper_trader.db` — default runtime SQLite database location (created locally; typically ignored by git)
- `scripts/` — convenience scripts (`setup`, `run_trader`, `run_dashboard`, `make_history`)
- `.streamlit/config.toml` — Streamlit theme config (safe to commit)

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
python paper_trader.py --feed demo --ui rich
```
You can switch the terminal UI:
```
bash
python paper_trader.py --feed demo --ui console
```
Or use the wrapper script:
```
bash
./scripts/run_trader.sh --feed demo --ui rich
```
### 3) Run the dashboard (Streamlit)

In a second terminal (same repo):
```
bash
python -m streamlit run dashboard_streamlit.py
```
Or use the wrapper script:
```
bash
./scripts/run_dashboard.sh
```
By default, the dashboard reads from `runtime/db/paper_trader.db`.

- You can change the DB path in the dashboard sidebar.
- The dashboard will create the parent directory for the chosen DB path if it doesn’t exist yet (handy on fresh checkouts).

---

## Replay with historical data (CSV feed)

### 1) Generate history CSV (default output: `data/history.csv`)
```
bash
./scripts/make_history.sh
```
You can override parameters (and optionally write to a different output path):
```
bash
./scripts/make_history.sh --days 30 --provider coingecko --granularity hourly --out data/history_30d.csv
```
### 2) Run the trader against the CSV
```
bash
./scripts/run_trader.sh \
  --feed csv \
  --history-csv data/history.csv \
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

## Streamlit dashboard features

The dashboard is designed to be useful while the trader is running:

- **Overview**: price chart (line or candlesticks), trade overlays, positions, equity curve
- **Events / Orders / Diagnostics**: inspect what the engine is doing
- **History**: work with CSV history settings used for replay
- **Strategy**: view the current `strategy.yaml`, validate edits, and save a new strategy file (restart the trader to apply changes)

---

## Configuration (`strategy.yaml`)

The strategy file defines:

- `bankroll_usd` — total simulated bankroll
- per-asset:
  - `enabled`
  - `allocation_usd` (validated against bankroll)
  - `entries`: a ladder of limit buys (`id`, `price`, `quote_size_usd`)
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
- **CSV feed errors**: confirm your history CSV has columns `ts,product_id,price` and UTC timestamps.
- **Streamlit refresh feels janky**: try lowering refresh seconds in the sidebar or disable auto refresh.

---

## Disclaimer

This is a learning/paper-trading project. It does not connect to an exchange, and it is **not** financial advice. If you trade real money based on a repo named “QuantumYoloEngine”, that’s between you and your future self.