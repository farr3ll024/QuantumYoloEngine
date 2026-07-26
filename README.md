# QuantumYoloEngine

A tiny **paper-trading sandbox** for BTC/ETH with:

- a **paper trader** that simulates entry ladders + stop + take-profits and records everything to SQLite
- a **Rich (terminal) dashboard** for live-ish feedback
- a **Streamlit dashboard** for charts, positions, orders, events, equity, and reports
- helper scripts to generate **historical CSV price data** for replays

It's intentionally experimental and a bit unhinged. Use it to learn, not to fund your retirement.

---

## Hosted web simulator (start here if you just want to use it)

The primary way to use QuantumYoloEngine is now the browser-based simulator under [`web/`](web/) —
a Vite + React + TypeScript app that runs the entire simulation in a Web Worker, client-side. No
account, no backend, no exchange connection. See [`web/README.md`](web/README.md) if present, or
just:

```bash
cd web
npm ci
npm run dev
```

Everything below this point documents the **Python reference engine** — the original CLI/local
dashboards, and the source of truth the web app's TypeScript engine is behaviorally tested against
(see `tests/parity/`).

---

## What's in here

- `paper_trader.py` — main entrypoint (CLI) for the Python reference engine
- `dashboard_streamlit.py` — Streamlit UI entrypoint *(local/legacy — see note below)*
- `run_dashboard.py` — Dash UI entrypoint *(local/legacy, beta — see below)*
- `quantum_yolo_engine/` — core reference engine (strategies, store, feeds, CLI, rich UI, validation, metrics)
- `dashboard/` — shared dashboard code (db readers, charts, history helpers, strategy + report tooling) *(local/legacy)*
- `dashboard_dash/` — Dash UI layer *(local/legacy, beta)*
- `web/` — the hosted browser simulator (Vite + React + TypeScript); see above
- `tests/python/` — pytest suite for the Python reference engine
- `tests/parity/` — behavioral parity fixtures shared between the Python and TypeScript engines
- `strategy.yaml` — strategy + risk config (bankroll, allocations, ladder entries, stop/TP)
- `runtime/db/paper_trader.db` — default runtime SQLite database location (created locally; typically ignored by git)
- `runtime/reports/` — exported run reports (created locally; typically ignored by git)
- `scripts/` — convenience scripts (`setup`, `run_trader`, `run_dashboard`, `make_history`)
- `.streamlit/config.toml` — Streamlit theme config (safe to commit)

> **Known limitation:** `dashboard/` and `dashboard_dash/` predate the `run_id`-scoped SQLite schema
> (see "Database" below) and have not been updated to filter by `run_id`. They still work for a
> database written by a single run, but were not re-verified against multi-run databases as part of
> the web migration. The Python CLI (`paper_trader.py`) and `quantum_yolo_engine/` itself are fully
> updated and tested.

---

## Quickstart (Python reference engine)

### 1) Setup a virtualenv + install deps

**macOS / Linux:**
```bash
./scripts/setup.sh
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Any platform, manually:
```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows:     .venv\Scripts\activate
pip install -r requirements-dev.txt   # or requirements.txt for a non-dev install
```

### Run the Python test suite
```bash
pytest
# with coverage:
pytest --cov=quantum_yolo_engine --cov-report=term-missing
```

### Regenerate behavioral parity fixtures (after changing engine.py or metrics.py)
```bash
python tests/parity/generate_fixtures.py
```

### 2) Run the trader

CSV replay is supported via the `csv` feed + `data/history.csv`.

Example (explicit CSV replay):
```bash
./scripts/run_trader.sh \
  --feed csv \
  --history-csv data/history.csv \
  --replay \
  --speed 3600 \
  --loop \
  --ui rich
```
To run the demo feed instead:
```bash
python paper_trader.py --feed demo --ui rich
```
You can switch the terminal UI:
```bash
python paper_trader.py --feed demo --ui console
```

### 3) Run the dashboard (Streamlit)

In a second terminal (same repo):
```bash
python -m streamlit run dashboard_streamlit.py
```
Or use the wrapper script:
```bash
./scripts/run_dashboard.sh
```
By default, the dashboard reads from `runtime/db/paper_trader.db`.

- You can change the DB path in the dashboard sidebar.
- The dashboard will create the parent directory for the chosen DB path if it doesn't exist yet (handy on fresh checkouts).
- When running CSV replay from the dashboard, it shows an **estimated runtime** based on the history file's time range and replay speed.
- Trade markers are filtered to the **visible chart time window** so overlays stay aligned with the plotted price series.

---

## Replay with historical data (CSV feed)

### 1) Generate history CSV (default output: `data/history.csv`)
```bash
./scripts/make_history.sh
```
You can override parameters (and optionally write to a different output path):
```bash
./scripts/make_history.sh --days 30 --provider coingecko --granularity hourly --out data/history_30d.csv
```

### 2) Run the trader against the CSV
```bash
./scripts/run_trader.sh \
  --feed csv \
  --history-csv data/history.csv \
  --replay \
  --speed 3600 \
  --loop \
  --ui rich
```
Notes:

- `--replay` sleeps between ticks based on timestamp deltas.
- `--speed 3600` means "3600× faster than real time".
- Supported speeds in the dashboard UI include up to **14400×**.
- `--loop` replays forever; omit it to stop after one pass.

---

## Reports (strategy optimization workflow)

The dashboard includes a **Reports** tab that can build exportable, strategy-aware run summaries from your SQLite runtime DB.

Reports include:

- KPI summary (realized/unrealized/total PnL, drawdown, event counts)
- equity curve export
- raw tables export (events, orders, positions, price ticks)
- reconstructed trade rounds (entry → exit) when possible, with duration + MFE/MAE
- a strategy snapshot + strategy hash for attribution

Exports can be downloaded as a **ZIP bundle** containing CSV/JSON/YAML files for offline analysis and strategy tuning.

---

## Streamlit dashboard features

The dashboard is designed to be useful while the trader is running:

- **Overview**: price chart (line or candlesticks), trade overlays, positions, equity curve
- **Events / Orders / Diagnostics**: inspect what the engine is doing
- **History**: work with CSV history settings used for replay
- **Strategy**: view the current `strategy.yaml`, validate edits, and save a new strategy file (restart the trader to apply changes)
- **Reports**: build and export run summaries to help optimize `strategy.yaml`

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
- each asset's sum of entry budgets ≤ that asset's allocation

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
```bash
python paper_trader.py --help
```
Common ones:

- `--config strategy.yaml` — strategy config path
- `--db runtime/db/paper_trader.db` — SQLite db path
- `--feed demo|csv` — market feed
- `--ui rich|console` — terminal display mode
- `--no-breakeven-stop` — don't move stop to breakeven after TP1
- `--quiet` — reduce console noise

---

## Troubleshooting

- **Dashboard shows "no ticks yet"**: run the trader first, and ensure the dashboard DB path matches the trader `--db`.
- **CSV feed errors**: confirm your history CSV has columns `ts,product_id,price` and UTC timestamps.
- **Streamlit refresh feels janky**: try lowering refresh seconds in the sidebar or disable auto refresh.

---

## Dash dashboard *(beta — not recommended for daily use)*

A second dashboard built on [Dash](https://dash.plotly.com/) lives in `dashboard_dash/` and is launched via `run_dashboard.py`. Its main motivation is solving Streamlit's scroll-reset-on-refresh behaviour (a known upstream issue) — Dash patches only changed DOM nodes via websocket so the page never reloads.

It is currently **work in progress**. Styling, engine controls, and a few callbacks are still being refined. Use the Streamlit dashboard for anything serious.

If you want to try it anyway:
```bash
pip install dash
python run_dashboard.py          # opens http://127.0.0.1:8050
python run_dashboard.py --port 8051 --debug --host 0.0.0.0   # optional flags
```

Known rough edges:

- Visual theme is still being iterated on
- Engine start/stop may behave differently from the Streamlit version
- Startup segfault on macOS: always launch via `run_dashboard.py`, never import `dashboard_dash` directly (the entrypoint stubs out Streamlit's cache decorators which otherwise crash outside a Streamlit runtime)

---

## Disclaimer

This is a learning/paper-trading project. It does not connect to an exchange, and it is **not** financial advice. If you trade real money based on a repo named "QuantumYoloEngine", that's between you and your future self.
