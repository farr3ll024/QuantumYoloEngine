# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Umbrella context

QuantumYoloEngine is one product under the **Reints Labs LLC** portfolio.
Portfolio-wide agent rules and known traps: `docs/agent-guide.md` in the
sibling `reints-labs-control-center` repo, which also holds the private ops
dashboard correlating all Reints Labs repos, deploys, and domains.

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

Both `tests/python/test_parity_fixtures.py` and `web/tests/unit/parity.test.ts`
check the committed fixtures. Regenerating rewrites the bootstrap timestamps
in every fixture even when nothing else changed: only regenerate after a
logic change, and don't commit timestamp-only churn
(`git checkout -- tests/parity/fixtures`).

`CLAUDE_IMPLEMENTATION_GUIDE.md` is the original build-out brief for the
hosted simulator (product mission, what it must never do, the required
disclaimer). Read it for product intent. Its Netlify project-creation and
deploy steps are not standing instructions: don't create or change a Netlify
project unless the owner asks.

## Verify a change

Run both engines' checks (about 30 seconds after install). There is no CI
workflow and Netlify only runs `npm ci && npm run build` in `web/`, so
nothing else runs the Python tests, lint or parity checks for you.

```bash
pip install -r requirements-dev.txt     # Python 3.11 verified
python -m pytest                        # tests/python, incl. parity fixtures
npm --prefix web ci
npm --prefix web run lint && npm --prefix web run typecheck \
  && npm --prefix web run test && npm --prefix web run build
npm --prefix web run test:e2e           # Playwright; serves web/dist, so build first
```

In a Claude Code cloud session, e2e needs the portfolio guide's Chromium
override (Playwright's own browser isn't installed), and a plain `pip install`
fails on the image's Debian-packaged PyYAML ("RECORD file not found"); the
session-start hook installs with `--ignore-installed` for that reason.

The root `.gitignore` anchors generated data to `/data/*`. An unanchored
`data/` once also matched `web/src/data/` and kept `csv.ts` out of git, which
broke clean checkouts: anchor root-only ignore rules, and check
`git status --ignored` when a new file doesn't show up.

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

## Claude Code setup

- `.claude/settings.json` allows `pytest`/`python -m pytest`, the fixture
  generator, and the web `lint`, `typecheck`, `test*` and `build` scripts
  (`npm --prefix web run ...` or `npm run ...` inside `web/`) without a
  prompt. It denies reading `.env`, `.env.local`, `.env.*.local`,
  `.streamlit/secrets.toml` and key files (`*.pem`, `*.key`).
- `.claude/hooks/session-start.sh` runs in cloud sessions: `pip install -r
  requirements-dev.txt` when the requirements files changed since the last
  install (hash in the git-ignored `.cache/`) or the test dependencies are
  missing, and `npm ci` in `web/` when `node_modules` is missing or older
  than the lockfile.
- Skills: `/verify` runs both engines' checks and explains failures.

## Non-goals

No real exchange connectivity, account management, or financial advice.
