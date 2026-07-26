# Claude Implementation Guide: Finish QuantumYoloEngine and Launch It on a New Netlify Project

## Your role

You are the implementation agent responsible for turning the existing `QuantumYoloEngine` repository into a polished, publicly hosted educational paper-trading simulator.

Work directly in this repository. Inspect the existing code before changing it, preserve useful behavior, implement the requested product completely, test it in proportion to its risk, visually inspect the finished application, and deploy it to a **brand-new Netlify project**.

Do not stop at a plan, mockup, partial scaffold, or locally passing build. The assignment is complete only when:

1. The simulation engine has automated behavioral tests.
2. The hosted web application implements the required workflow.
3. The application builds from a clean checkout.
4. A new Netlify project has been created specifically for QuantumYoloEngine.
5. A preview deploy has been inspected.
6. A production deploy is live and verified.
7. The final handoff includes URLs, project identifiers, tests, known limitations, and rollback instructions.

---

## 1. Product mission

QuantumYoloEngine is an educational market-simulation laboratory for experimenting with BTC and ETH paper-trading strategies against deterministic demo data and historical CSV data.

It must help a user:

- configure a simulated bankroll;
- allocate that bankroll across BTC and ETH;
- build entry ladders;
- define stop-loss and two-stage take-profit rules;
- replay deterministic or historical price data;
- inspect positions, orders, fills, events, equity, drawdown, and performance;
- compare runs;
- export a self-contained report bundle;
- learn how a strategy behaves without risking money.

It must **never**:

- connect to an exchange for order execution;
- accept exchange API keys;
- place, prepare, sign, or route real orders;
- present results as investment advice;
- promise future returns;
- imply that backtesting predicts live performance;
- silently fetch or upload a user's private data;
- claim to be a production trading system.

The product voice can remain energetic and slightly playful, but warnings, calculations, and status labels must be unambiguous.

Use this exact persistent disclaimer wherever a run is configured or results are displayed:

> Experimental software for education and paper trading only. It does not place live trades and is not financial advice. Backtests and simulated results do not predict future performance.

---

## 2. Current repository audit

Treat this section as a starting snapshot. Revalidate it before implementation.

### Existing implementation

The repository currently contains:

- `quantum_yolo_engine/engine.py`: the Python paper-trading state machine;
- `quantum_yolo_engine/store.py`: SQLite persistence;
- `quantum_yolo_engine/feeds.py`: deterministic demo feed and CSV replay feed;
- `quantum_yolo_engine/strategy.py`: YAML strategy loading;
- `quantum_yolo_engine/risk.py`: basic bankroll/allocation validation;
- `quantum_yolo_engine/cli.py`: local CLI runner;
- `dashboard/`: Streamlit-oriented readers, charts, reports, and local process control;
- `dashboard_dash/`: a newer Dash interface marked beta/WIP;
- `run_dashboard.py`: local Dash server entry point;
- `strategy.yaml`: default BTC and ETH strategy;
- `build_history.py`: Binance/CoinGecko history generation;
- `README.md`: local setup and feature documentation.

### Behavior worth preserving

The current engine establishes important semantics:

- a buy-limit entry becomes eligible when market price is at or below its limit;
- the simulated entry fill uses `min(marketPrice, limitPrice)`;
- position average entry is quantity weighted;
- the stop cannot trigger on the exact same timestamp as a new entry;
- a sell stop triggers when market price is at or below the stop;
- the simulated stop fill uses `min(marketPrice, stopPrice)`;
- TP1 triggers when market price is at or above its threshold;
- TP1 sells its configured fraction of the current position;
- TP2 sells the remaining position;
- take-profit fills use `max(marketPrice, takeProfitPrice)`;
- the stop can move to average entry after TP1;
- every meaningful transition generates a structured event;
- a strategy snapshot and SHA-256 fingerprint are recorded at run start;
- reports contain strategy attribution and exportable data.

These rules must be covered by tests before or while they are ported.

### Known architectural blockers

The current hosted architecture is not Netlify compatible:

- Dash expects a persistent Python web server.
- `dashboard/engine_control.py` starts and kills local child processes.
- the dashboard and trader share a local SQLite database.
- runtime state, reports, logs, and history files are written to local disk.
- several callbacks accept arbitrary filesystem paths.
- the engine may replay indefinitely with `--loop`.

Netlify production deploys do not provide a permanent Python process or durable shared local disk. Do not attempt to hide this incompatibility with shell scripts, a long-running function, or an ephemeral SQLite file.

### Correctness and maintainability gaps to address

At minimum, revalidate and fix these issues:

1. There is no committed automated test suite.
2. Dependencies are loosely specified and there is no reproducible lockfile for the Python application.
3. `--replay` uses `store_true` while defaulting to `True`, so the CLI exposes no effective way to disable replay sleeping.
4. Strategy validation does not fully enforce:
   - positive bankroll and allocations;
   - positive prices and entry sizes;
   - unique entry IDs;
   - supported product IDs;
   - `0 < tp1_fraction <= 1`;
   - `0 < tp2_fraction <= 1`;
   - a valid total exit fraction;
   - sensible stop/entry/take-profit ordering;
   - finite numeric values.
5. Rows are not scoped by a first-class `run_id`, so reused databases can mix separate runs.
6. Stable order IDs can collide when a database is reused.
7. The runtime mutates `strat.stop_price`, which can make state attribution harder.
8. The current equity curve applies the final position state backward across historical ticks. It is not a faithful event-by-event equity reconstruction.
9. Trade reconstruction treats every `entry_filled` as a replacement for the prior open timestamp instead of explicitly modeling multiple ladder fills.
10. Report attribution can still read a strategy file from disk after a run instead of relying exclusively on the immutable run snapshot.
11. The Dash layer depends on Streamlit stubs and duplicates presentation/report logic.
12. There are no browser, accessibility, responsive-layout, or clean-install tests.

Do not preserve a known incorrect metric merely because the current dashboard displays it.

---

## 3. Required architecture

### Decision

Build the hosted product as a browser-first TypeScript application under `web/`.

Use:

- Vite;
- React;
- TypeScript with strict mode;
- Vitest;
- Playwright;
- a Web Worker for simulation;
- IndexedDB for browser-local runs and imported datasets;
- a charting library with accessible tabular fallbacks;
- YAML parsing for strategy import/export;
- a ZIP library for report bundles.

Keep the existing Python engine as:

- the local research CLI;
- the reference implementation during migration;
- the producer of cross-language parity fixtures;
- a tool for offline history generation.

Do not host the Dash or Streamlit process on Netlify.

### Why this architecture

A deterministic replay does not require a trusted server. Running it in a Web Worker:

- avoids server timeout limits;
- avoids persistent process requirements;
- keeps user-uploaded CSV data in the browser;
- prevents public compute abuse;
- makes replay responsive and pauseable;
- makes Netlify deployment a conventional static application;
- allows offline-friendly behavior after initial load;
- avoids pretending ephemeral function storage is durable.

### Cloud persistence boundary

Version 1 must work without accounts and without cloud persistence.

Persist locally:

- strategies;
- imported dataset metadata;
- completed run summaries;
- event ledgers;
- comparison selections;
- user display preferences.

Use IndexedDB rather than localStorage for run/event data. localStorage may be used only for small preferences.

Do **not** add anonymous public writes to Netlify Blobs. If cloud sharing is added later, place it behind Netlify Functions with:

- explicit authentication or signed ownership;
- request validation;
- rate limiting;
- object-size limits;
- strong consistency for immediate read-after-write;
- non-guessable IDs;
- deletion controls;
- no secrets in client bundles.

Cloud sharing is a later feature unless the user explicitly expands scope.

---

## 4. Target repository structure

Create this structure without deleting the existing Python implementation:

```text
QuantumYoloEngine/
├─ quantum_yolo_engine/           # existing Python reference engine
├─ dashboard/                     # existing local dashboard; legacy/local only
├─ dashboard_dash/                # existing beta dashboard; legacy/local only
├─ tests/
│  ├─ python/
│  └─ parity/
│     ├─ fixtures/
│     └─ generate_fixtures.py
├─ web/
│  ├─ index.html
│  ├─ package.json
│  ├─ package-lock.json
│  ├─ tsconfig.json
│  ├─ vite.config.ts
│  ├─ playwright.config.ts
│  ├─ netlify/
│  │  └─ functions/               # only if a bounded server endpoint is justified
│  ├─ public/
│  │  ├─ datasets/
│  │  │  ├─ manifest.json
│  │  │  └─ sample-btc-eth.csv
│  │  ├─ favicon.svg
│  │  ├─ robots.txt
│  │  └─ _headers or generated equivalents if needed
│  ├─ src/
│  │  ├─ app/
│  │  ├─ components/
│  │  ├─ engine/
│  │  │  ├─ model.ts
│  │  │  ├─ strategy.ts
│  │  │  ├─ validate.ts
│  │  │  ├─ simulate.ts
│  │  │  ├─ metrics.ts
│  │  │  ├─ reports.ts
│  │  │  └─ parity.ts
│  │  ├─ worker/
│  │  │  └─ simulation.worker.ts
│  │  ├─ data/
│  │  ├─ storage/
│  │  ├─ routes/
│  │  ├─ styles/
│  │  ├─ test/
│  │  └─ main.tsx
│  └─ tests/
│     ├─ unit/
│     └─ e2e/
├─ netlify.toml
├─ strategy.yaml
├─ requirements.txt
├─ requirements-dev.txt
├─ README.md
└─ CLAUDE_IMPLEMENTATION_GUIDE.md
```

If a materially better structure is justified, document the reason before deviating.

---

## 5. Domain model

Do not use untyped dictionaries for core state.

### Required primary entities

#### Strategy

- `schemaVersion`
- `name`
- `bankrollUsd`
- `quoteCurrency`
- `assets[]`
- `moveStopToBreakevenAfterTp1`
- `createdAt`
- `updatedAt`

#### AssetStrategy

- `productId`
- `enabled`
- `allocationUsd`
- `entries[]`
- `stopPrice`
- `takeProfit`

#### EntryRule

- `id`
- `price`
- `quoteSizeUsd`

#### TakeProfitRule

- `tp1Price`
- `tp1Fraction`
- `tp2Price`
- `tp2Fraction`

#### Dataset

- `datasetId`
- `name`
- `source`
- `createdAt`
- `startTs`
- `endTs`
- `products`
- `rowCount`
- `sha256`
- `schemaVersion`

#### Run

- `runId`
- `status`: `created | running | paused | completed | canceled | failed`
- `strategySnapshot`
- `strategyHash`
- `datasetSnapshot`
- `datasetHash`
- `engineVersion`
- `startedAt`
- `completedAt`
- `cursor`
- `eventSequence`
- `summary`

#### Tick

- `ts`
- `productId`
- `price`

#### Order

- `runId`
- `orderId`
- `ruleId`
- `productId`
- `orderType`
- `side`
- `status`
- `limitOrTriggerPrice`
- `quoteSizeUsd`
- `baseSize`
- `createdAt`
- `filledAt`
- `fillPrice`

#### Position

- `runId`
- `productId`
- `baseQty`
- `avgEntry`
- `investedQuote`
- `realizedPnl`
- `state`
- `tp1Done`
- `tp2Done`
- `stopDone`
- `activeStopPrice`

#### Event

- `runId`
- `sequence`
- `ts`
- `level`
- `eventType`
- `productId`
- `message`
- `payload`

Use integer sequence numbers for deterministic ordering when timestamps are equal.

---

## 6. Implementation phases

Complete phases in order. Do not deploy before the quality gate in Phase 9.

### Phase 1: Establish a clean baseline

1. Record:
   - current branch;
   - current commit;
   - current `git status`;
   - available Python and Node versions.
2. Preserve unrelated user changes.
3. Create a feature branch such as:

   ```bash
   git switch -c feat/netlify-web-simulator
   ```

4. Add reproducible development dependencies:
   - `pytest`;
   - `pytest-cov`;
   - optionally `hypothesis`;
   - formatter/linter/type checker if adopted.
5. Pin compatible dependency ranges or produce a lock/constraints file.
6. Update setup instructions for Windows, macOS, and Linux.
7. Confirm all Python modules compile.
8. Confirm the current CLI can execute a short deterministic demo run in a temporary directory.

Do not commit generated runtime databases, logs, reports, or downloaded history.

### Phase 2: Test and harden the Python reference engine

Create focused tests for:

- strategy parsing;
- allocation limits;
- entry-budget limits;
- positive and finite values;
- duplicate entry IDs;
- take-profit fractions;
- unsupported assets;
- deterministic demo feed output for a fixed seed;
- weighted average entry;
- multiple ladder fills;
- no same-tick entry and stop;
- stop fills;
- TP1 partial exit;
- break-even stop movement;
- TP2 final exit;
- order cancellation;
- realized P&L;
- stable strategy hashing;
- clean separation between two `run_id` values;
- event sequence ordering;
- idempotent initialization;
- faithful event-by-event equity calculation;
- maximum drawdown;
- report export contents.

Fix the CLI replay flag. Prefer a mutually exclusive pair:

```text
--replay / --no-replay
```

or a boolean optional action supported by the targeted Python version.

Introduce `run_id` and immutable strategy snapshots into the Python data model. A new run must not inherit prior orders, positions, or event state unless an explicit resume flow is implemented and tested.

Do not make schema changes without migration or new-database behavior that is documented and tested.

### Phase 3: Generate behavioral parity fixtures

Create small, human-reviewable fixtures that execute these scenarios in Python:

1. No fills.
2. One entry fill.
3. Three ladder fills and weighted average.
4. Entry followed by stop on a later tick.
5. Entry and stop threshold crossed on the same tick.
6. TP1 then break-even stop.
7. TP1 then TP2.
8. BTC and ETH interleaved at identical timestamps.
9. Price gap through stop.
10. Price gap through take profit.

Each fixture must include:

- strategy input;
- ordered ticks;
- expected orders;
- expected positions;
- expected events;
- expected equity samples;
- expected summary;
- strategy and dataset hashes.

Normalize floating-point output before serialization. Define the rounding policy once and test it.

The TypeScript engine must pass the same fixture suite.

### Phase 4: Scaffold the hosted web application

Under `web/`, create a Vite React TypeScript application.

Required package scripts:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test",
    "lint": "eslint .",
    "typecheck": "tsc -b --pretty false"
  }
}
```

Use:

- strict TypeScript;
- no `any` in engine and persistence code;
- runtime schema validation at file/import boundaries;
- error boundaries;
- route-level lazy loading where useful;
- semantic HTML;
- keyboard-operable controls;
- reduced-motion support;
- accessible chart summaries and data tables.

Do not copy the 40,000-line-equivalent Dash callback architecture into React. Separate pure engine logic from UI state.

### Phase 5: Port the deterministic engine

Implement the engine as pure functions or a small explicit state machine.

Inputs:

- immutable run state;
- one timestamp group of ticks;
- immutable strategy;
- engine options.

Outputs:

- next run state;
- emitted events;
- changed orders/positions;
- equity sample.

The worker must:

- process ticks in stable timestamp/product order;
- support start, pause, resume, step, cancel, and reset;
- report progress without flooding the main thread;
- batch UI updates;
- honor a speed control without changing deterministic results;
- stop cleanly when the component unmounts or a run is canceled;
- never use wall-clock time as a trading input;
- never mutate the strategy snapshot.

Run IDs, event sequences, and hashes must be deterministic for a given fixture unless the ID is explicitly generated outside the engine.

### Phase 6: Implement the product experience

#### Route: `/`

Provide:

- product explanation;
- paper-trading disclaimer;
- sample screenshots or a live preview;
- “Open simulator” CTA;
- link to methodology;
- clear experimental status.

#### Route: `/simulator`

Provide a guided workspace with:

1. **Dataset**
   - bundled sample dataset;
   - CSV upload;
   - validation summary;
   - detected products;
   - start/end date;
   - row count;
   - duplicate/invalid row warnings.
2. **Strategy**
   - approachable form editor;
   - advanced YAML editor;
   - validation errors attached to fields;
   - allocation visualization;
   - reset-to-default;
   - import/export.
3. **Run controls**
   - start;
   - pause/resume;
   - step one timestamp;
   - cancel;
   - reset;
   - speed;
   - progress;
   - current timestamp;
   - explicit status.
4. **Overview**
   - bankroll;
   - current equity;
   - total P&L;
   - realized/unrealized P&L;
   - maximum drawdown;
   - filled entries;
   - TP1/TP2 hits;
   - stop count.
5. **Charts**
   - price series;
   - entry/TP/stop markers;
   - equity curve;
   - drawdown;
   - asset selector;
   - time-window controls.
6. **Tables**
   - positions;
   - orders;
   - events;
   - trades;
   - sortable and filterable;
   - useful empty states.
7. **Run completion**
   - summary;
   - warnings;
   - save locally;
   - export report;
   - compare another strategy.

#### Route: `/runs`

Provide locally saved runs:

- newest first;
- search/filter;
- strategy hash;
- dataset hash;
- key metrics;
- open;
- compare;
- export;
- delete with confirmation.

#### Route: `/compare`

Allow two to four completed runs to be compared across:

- total P&L;
- realized P&L;
- max drawdown;
- stop rate;
- TP completion rate;
- duration;
- exposure;
- number of entries;
- strategy differences;
- equity overlays.

Never use color alone to communicate better/worse results.

#### Route: `/methodology`

Explain:

- fill assumptions;
- slippage limitation;
- fees limitation;
- data limitations;
- no order-book simulation;
- no liquidity model;
- no live execution;
- how P&L and drawdown are calculated;
- why simulated performance differs from live trading.

#### Route: `/privacy`

State clearly:

- imported CSV data stays in the browser in version 1;
- saved runs remain in browser storage;
- deleting browser data removes local runs;
- no exchange credentials are requested;
- standard Netlify access logs may exist.

### Phase 7: Data import and reports

CSV schema:

```csv
ts,product_id,price
2026-01-01T00:00:00Z,BTC-USD,92000.00
2026-01-01T00:00:00Z,ETH-USD,3300.00
```

Validation must reject or explicitly handle:

- missing required columns;
- empty files;
- invalid timestamps;
- invalid prices;
- non-positive prices;
- unsupported product IDs;
- excessive file size;
- excessive row count;
- unordered rows;
- duplicate `(ts, product_id)` rows;
- missing asset values.

Forward filling must be explicit and must never invent a value before the first observation for an asset.

Report ZIP must include:

```text
README.md
manifest.json
summary.json
summary.csv
equity_curve.csv
drawdown.csv
events.csv
orders.csv
positions.csv
trades.csv
strategy_snapshot.yaml
dataset_manifest.json
```

`manifest.json` must include:

- schema version;
- application version/commit;
- engine version;
- run ID;
- created time;
- strategy hash;
- dataset hash;
- calculation assumptions;
- disclaimer.

Report metrics must be derived from the immutable event ledger, not from the final position snapshot projected backward.

### Phase 8: Design and usability

The product should feel like a serious Reints Labs experiment, not an admin template.

Direction:

- dark analytical workspace;
- high-contrast data surfaces;
- restrained electric accents;
- clear hierarchy;
- compact but readable tables;
- monospaced treatment for hashes, timestamps, and prices;
- energetic product personality without casino imagery;
- no fake urgency, flashing profit indicators, confetti, or “winning” language.

Responsive requirements:

- no horizontal page overflow at 320 CSS pixels;
- tables use controlled horizontal scrolling inside their region;
- sidebar becomes a drawer or top workflow on narrow screens;
- primary controls remain reachable;
- charts remain legible;
- touch targets are at least 44×44 CSS pixels where practical.

Accessibility requirements:

- logical heading hierarchy;
- visible focus;
- keyboard-complete workflow;
- labeled inputs;
- form errors connected with `aria-describedby`;
- status updates exposed through appropriate live regions;
- reduced motion;
- WCAG AA contrast;
- chart data available in tables or summaries.

### Phase 9: Quality gate before Netlify creation

Do not create the Netlify project until all of these pass locally:

```bash
# Python reference
python -m pytest

# Hosted app
cd web
npm ci
npm run lint
npm run typecheck
npm test
npm run build
npm run test:e2e
```

Required automated coverage:

- Python reference-engine tests;
- TypeScript engine unit tests;
- cross-language parity fixtures;
- strategy validation;
- CSV validation;
- IndexedDB persistence;
- report exports;
- route smoke tests;
- simulator happy path;
- pause/resume/reset;
- narrow viewport;
- keyboard workflow;
- error states.

Required manual/visual inspection:

- desktop simulator;
- mobile simulator;
- strategy validation;
- dataset import;
- completed run;
- report ZIP;
- run comparison;
- privacy and methodology;
- no overflow;
- no clipped menus/tooltips;
- no unreadable chart labels;
- no console errors.

Do not treat a successful build as sufficient visual validation.

---

## 7. Netlify requirements

### Mandatory isolation

Create a **new Netlify project**. Do not link or deploy this repository to any existing project, including:

- `reints-labs`;
- `weddware-platform`;
- `thereints2027`;
- Baker and Son's Construction;
- any Color Forge project.

Do not reuse an existing site ID.

Preferred project name:

```text
quantum-yolo-engine
```

If that name is unavailable, use:

```text
quantum-yolo-engine-reints-labs
```

Report the final name and immutable project ID.

### Root `netlify.toml`

Create and validate a root configuration equivalent to:

```toml
[build]
  base = "web"
  command = "npm ci && npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "22"

[[redirects]]
  from = "/api/*"
  to = "/.netlify/functions/:splat"
  status = 200

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[[headers]]
  for = "/*"
  [headers.values]
    X-Content-Type-Options = "nosniff"
    X-Frame-Options = "DENY"
    Referrer-Policy = "strict-origin-when-cross-origin"
    Permissions-Policy = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"

[[headers]]
  for = "/assets/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"
```

Only include the `/api/*` redirect if actual Netlify Functions exist. Specific redirects must precede the SPA fallback.

Add a Content Security Policy after inventorying the application's actual scripts, styles, workers, fonts, images, network calls, and blob URLs. Do not paste a CSP that breaks Vite chunks, Web Workers, downloads, or charts. Avoid `'unsafe-eval'`. Minimize `'unsafe-inline'`.

### New project creation procedure

Use the authenticated Netlify account.

1. Verify identity:

   ```bash
   npx netlify status
   ```

2. Confirm the repository is not linked:

   ```bash
   if [ -f .netlify/state.json ]; then
     cat .netlify/state.json
   fi
   ```

   On Windows, use the PowerShell equivalent.

3. List or inspect existing projects to avoid collisions.
4. Create exactly one new project:

   ```bash
   npx netlify sites:create --name quantum-yolo-engine
   ```

   If the CLI version uses a different current command, consult `npx netlify sites --help` rather than guessing.

5. Confirm `.netlify/state.json` contains the new project ID.
6. Confirm:

   ```bash
   npx netlify status
   ```

   shows only the new QuantumYoloEngine project for this working directory.
7. Do not commit `.netlify/state.json`.

### Deployment sequence

1. Run the full local quality gate.
2. Create a preview deploy:

   ```bash
   npx netlify deploy
   ```

3. Inspect the preview at desktop and mobile sizes.
4. Run smoke tests against the preview URL.
5. Confirm headers, SPA routes, assets, CSV import, worker execution, exports, and refresh behavior.
6. Only after preview acceptance, deploy production:

   ```bash
   npx netlify deploy --prod
   ```

7. Verify the production URL independently.
8. Record:
   - production URL;
   - unique deploy URL;
   - deploy ID;
   - project ID;
   - build-log URL;
   - deployed commit SHA.

### Custom domain

A custom domain is not required for the first launch. Do not change DNS for `reintslabs.com`, `weddware.com`, or `sarahandblaise.com` as part of this task.

If the user later approves a branded domain, prefer a subdomain such as:

```text
quantum.reintslabs.com
```

That must be a separate, explicit DNS task.

---

## 8. Security and abuse prevention

### Mandatory

- No secrets in source, examples, fixtures, logs, screenshots, or client bundles.
- No exchange credential inputs.
- No arbitrary server filesystem paths.
- No child-process controls in the hosted app.
- No user-controlled shell commands.
- No `eval`, dynamic code generation, or unsafe YAML loaders.
- Validate all imported data at runtime.
- Cap CSV size and rows before parsing the full file.
- Parse large files off the main thread.
- Escape user-provided labels in exports and UI.
- Mitigate spreadsheet-formula injection in exported CSV values beginning with `=`, `+`, `-`, or `@`.
- Use cryptographic hashes only for attribution/integrity, not as authentication.
- Never expose Netlify tokens.
- Keep source maps private or intentionally reviewed.
- Add dependency auditing to the release checklist.

### Functions, if introduced

Use modern Netlify function syntax:

```ts
import type { Config, Context } from "@netlify/functions";

export default async (req: Request, context: Context) => {
  return Response.json({ ok: true, requestId: context.requestId });
};

export const config: Config = {
  path: "/api/health",
  method: ["GET"],
};
```

Use `Netlify.env.get()` for server-only environment variables. Do not use a function for a long-running replay. Synchronous functions have bounded execution time; background functions still require external persistence and are inappropriate for indefinite loops.

---

## 9. Definition of done

### Engine

- [ ] Python reference tests pass.
- [ ] TypeScript engine tests pass.
- [ ] Parity fixtures pass.
- [ ] Every run has a `run_id`.
- [ ] Strategy and dataset snapshots are immutable.
- [ ] Equity and drawdown are reconstructed correctly.
- [ ] Floating-point policy is documented.
- [ ] No live-trading code exists.

### Product

- [ ] Sample run works without setup.
- [ ] CSV import validates errors clearly.
- [ ] Strategy form and YAML import/export work.
- [ ] Start, pause, resume, step, cancel, and reset work.
- [ ] Positions, orders, events, charts, and metrics agree.
- [ ] Runs persist locally.
- [ ] Run comparison works.
- [ ] Report ZIP is complete and re-importable.
- [ ] Disclaimer is persistent and visible.
- [ ] Privacy and methodology pages are accurate.

### Quality

- [ ] Clean install succeeds.
- [ ] Lint passes.
- [ ] Type checking passes.
- [ ] Unit tests pass.
- [ ] E2E tests pass.
- [ ] No console errors.
- [ ] Mobile layout is visually inspected.
- [ ] Keyboard workflow is verified.
- [ ] Accessibility checks pass.
- [ ] Dependency audit is reviewed.

### Netlify

- [ ] A brand-new project was created.
- [ ] No existing Reints Labs/Weddware/wedding project was reused.
- [ ] Preview deploy was inspected.
- [ ] Production deploy is live.
- [ ] Direct navigation and refresh on SPA routes work.
- [ ] Security headers are present.
- [ ] Production URL and project ID are recorded.
- [ ] Rollback procedure is documented.

---

## 10. Required final handoff

Your final response must include:

1. concise outcome;
2. production URL;
3. unique deploy URL;
4. Netlify project name and ID;
5. deployed branch and commit SHA;
6. major implementation decisions;
7. test commands and results;
8. screenshots or visual-review notes for desktop and mobile;
9. security/privacy notes;
10. known limitations;
11. exact rollback target and procedure;
12. any work intentionally deferred.

Do not claim:

- “fully tested” without listing tests;
- “secure” without naming controls;
- “deployed” without a production URL and deploy ID;
- “matches Python” without parity fixture results;
- “mobile ready” without inspecting a narrow viewport.

---

## 11. Suggested execution checklist

Use this as the working sequence:

```text
[ ] inspect repo and git state
[ ] create feature branch
[ ] establish Python environment
[ ] add Python tests
[ ] correct reference-engine issues
[ ] add run IDs and immutable snapshots
[ ] generate parity fixtures
[ ] scaffold web app
[ ] implement typed model and validation
[ ] port engine
[ ] run parity suite
[ ] implement worker controls
[ ] implement dataset import
[ ] implement strategy editor
[ ] implement overview/charts/tables
[ ] implement local persistence
[ ] implement report export/import
[ ] implement run comparison
[ ] add methodology/privacy/disclaimer
[ ] add responsive/accessibility polish
[ ] add Netlify configuration
[ ] pass full local quality gate
[ ] create new Netlify project
[ ] preview deploy
[ ] visual and E2E preview QA
[ ] production deploy
[ ] production verification
[ ] documentation and final handoff
```

---

## 12. Guardrails for judgment calls

When deciding between speed and correctness:

- prefer correctness in simulation math;
- prefer deterministic behavior;
- prefer explicit limitations;
- prefer local/private data handling;
- prefer a smaller complete workflow over a wide incomplete one;
- preserve existing Python functionality unless a tested replacement exists;
- avoid cloud services that are unnecessary for version 1;
- do not introduce real trading “for later”;
- do not repurpose an existing Netlify project;
- do not modify Reints Labs, Weddware, or personal wedding DNS/deployments.

If an architectural decision changes these product boundaries, stop and obtain user direction before proceeding.

