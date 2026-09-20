# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Umbrella context

QuantumYoloEngine is one product under the **Reints Labs LLC** portfolio.
The private ops dashboard correlating all Reints Labs repos, deploys, and
domains lives in the sibling `reints-labs-control-center` repo.

## What this is

A paper-trading sandbox for BTC/ETH — experimental and explicitly **not
financial advice**; it never connects to a real exchange. There are two
parallel implementations that must stay behaviorally consistent:

1. **`web/`** — the primary, hosted product: a Vite + React + TypeScript
   app that runs the whole simulation client-side in a Web Worker. No
   backend, no account.
2. **The Python reference engine** (repo root: `paper_trader.py`,
   `quantum_yolo_engine/`, Streamlit/Dash dashboards) — the original
   CLI/local implementation and the **source of truth** the TypeScript
   engine is tested against for behavioral parity.

`tests/parity/` holds the shared fixtures both engines are checked
against. **If you change trading logic in one engine (`engine.py`/
`metrics.py` on the Python side, or its TS equivalent in `web/`), update
the other and regenerate parity fixtures** — don't let them drift:

```bash
python tests/parity/generate_fixtures.py
```

## Commands

Python reference engine:
```bash
./scripts/setup.sh                # or requirements-dev.txt manually
pytest
pytest --cov=quantum_yolo_engine --cov-report=term-missing
python paper_trader.py --feed demo --ui rich
python -m streamlit run dashboard_streamlit.py   # legacy dashboard
```

Web simulator:
```bash
cd web
npm ci
npm run dev
```

## Legacy/beta code — don't treat as authoritative

- `dashboard/` and `dashboard_dash/` (Dash UI, `run_dashboard.py`) predate
  the `run_id`-scoped SQLite schema and are **not updated to filter by
  `run_id`** — they only work correctly against a single-run database.
- `dashboard_dash` is beta/WIP; always launch it via `run_dashboard.py`,
  never import the package directly (it stubs Streamlit's cache decorators
  to avoid a macOS startup segfault outside a Streamlit runtime).
- The Streamlit dashboard (`dashboard_streamlit.py`) is the one currently
  recommended for serious use of the Python engine; `web/` is the
  recommended product overall.

## Data model

SQLite (`runtime/db/paper_trader.db`, WAL mode) with `price_ticks`,
`orders`, `positions`, `events` tables, read live by dashboards while the
trader writes. Strategy/risk config lives in `strategy.yaml`; the engine
validates that allocations sum within bankroll and entry-ladder budgets sum
within each asset's allocation — preserve those validations if you touch
config loading.

## Non-goals

No real exchange connectivity, account management, or financial advice.
